import csv
import random
import hashlib
import json
from array import array
from pathlib import Path

import numpy as np
from scipy import sparse

from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from django.db import transaction

from books.models import Book


class Command(BaseCommand):
    help = "Compute item-item collaborative filtering similarity from Goodreads interaction data"

    def add_arguments(self, parser):
        parser.add_argument("interactions_path", type=str, help="Path to goodreads_interactions.csv")
        parser.add_argument("--book-id-map", type=str, help="Path to book_id_map.csv; defaults to the CSV's directory")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--matrix-cache", type=str, help="Optional .npz cache for the validated rating matrix")
        parser.add_argument("--sample-size", type=int, default=0,
                             help="Number of matching interactions to reservoir-sample; 0 uses all ratings")
        parser.add_argument("--min-ratings", type=int, default=5,
                             help="Minimum ratings a book needs to be included")
        parser.add_argument("--top-k", type=int, default=15,
                             help="Number of similar books to store per book")
        parser.add_argument("--min-co-raters", type=int, default=5,
                            help="Minimum shared raters required between two books to count as similar")
        parser.add_argument("--relative-threshold", type=float, default=0.6,
                            help="Keep neighbors scoring at least this fraction of the book's own best score")
        parser.add_argument("--absolute-floor", type=float, default=0.05,
                            help="Hard minimum similarity score regardless of relative threshold")
        parser.add_argument("--n-factors", type=int, default=30,
                            help="Number of latent factors for ALS")
        parser.add_argument("--als-iterations", type=int, default=8,
                            help="Number of ALS alternating iterations")
        parser.add_argument("--regularization", type=float, default=0.1,
                            help="L2 regularization strength for ALS")
        parser.add_argument("--bias-regularization", type=float, default=0.01,
                            help="L2 regularization for ALS bias terms, kept lighter than factor "
                                 "regularization so bias can absorb popularity signal cleanly")
        parser.add_argument("--block-size", type=int, default=256,
                            help="Number of books per similarity computation block")

    def load_valid_books(self):
        self.stdout.write("Loading edition-to-canonical mapping...")
        edition_to_canonical = {}
        qs = Book.objects.only("id", "ucsd_id", "canonical_book_id").iterator(chunk_size=5000)
        canonical_count = 0
        for book in qs:
            if not book.ucsd_id:
                continue
            canonical_pk = book.canonical_book_id or book.id
            edition_to_canonical[book.ucsd_id] = canonical_pk
            if book.canonical_book_id is None:
                canonical_count += 1
        self.stdout.write(f"Mapped {len(edition_to_canonical):,} editions onto {canonical_count:,} canonical books")
        return edition_to_canonical

    def load_csv_mapping(self, mapping_path, edition_to_canonical):
        mapping = {}
        try:
            with open(mapping_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                if not {"book_id_csv", "book_id"}.issubset(reader.fieldnames or []):
                    raise CommandError("Book mapping must contain book_id_csv and book_id columns")
                for record in reader:
                    canonical_pk = edition_to_canonical.get(record["book_id"])
                    if canonical_pk is not None:
                        mapping[record["book_id_csv"]] = canonical_pk
        except OSError as exc:
            raise CommandError(f"Cannot read book ID mapping: {exc}") from exc
        if not mapping:
            raise CommandError("Book ID mapping has no matches in the catalog")
        self.stdout.write(f"Mapped {len(mapping):,} CSV book IDs to the catalog")
        return mapping

    def iter_interactions(self, interactions_path, csv_to_canonical):
        seen = 0
        with open(interactions_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            if not {"user_id", "book_id", "rating"}.issubset(header):
                raise CommandError("Interactions must contain user_id, book_id and rating columns")
            user_column, book_column, rating_column = (header.index(name) for name in ("user_id", "book_id", "rating"))
            for record in reader:
                try:
                    book_id = record[book_column]
                    rating = int(record[rating_column])
                    user_id = record[user_column]
                except (IndexError, ValueError):
                    continue

                canonical_pk = csv_to_canonical.get(book_id)
                if canonical_pk is None or not 1 <= rating <= 5:
                    continue

                seen += 1
                yield {"user_id": user_id, "canonical_pk": canonical_pk, "rating": rating}
                if seen % 5_000_000 == 0:
                    self.stdout.write(f"  matched {seen:,} interactions so far...")
        self.stdout.write(f"Matched {seen:,} rated interactions in the complete CSV")

    def sample_interactions(self, interactions_path, sample_size, csv_to_canonical, seed=42):
        records = self.iter_interactions(interactions_path, csv_to_canonical)
        if sample_size == 0:
            return records
        self.stdout.write(f"Reservoir-sampling up to {sample_size:,} matching interactions...")
        reservoir = []
        rng = random.Random(seed)
        for seen, parsed in enumerate(records, start=1):
            if len(reservoir) < sample_size:
                reservoir.append(parsed)
            else:
                j = rng.randint(0, seen - 1)
                if j < sample_size:
                    reservoir[j] = parsed

        self.stdout.write(f"Sampled {len(reservoir):,} interactions")
        return reservoir

    def build_matrix(self, interactions):
        self.stdout.write("Building rating matrix...")
        user_index, book_index = {}, {}
        rows, cols, data = array("i"), array("i"), array("f")

        for record in interactions:
            user_id, canonical_pk, rating = record["user_id"], record["canonical_pk"], record["rating"]
            if user_id not in user_index:
                user_index[user_id] = len(user_index)
            if canonical_pk not in book_index:
                book_index[canonical_pk] = len(book_index)
            rows.append(user_index[user_id])
            cols.append(book_index[canonical_pk])
            data.append(float(rating))

        n_users, n_books = len(user_index), len(book_index)
        self.stdout.write(f"Matrix: {n_users:,} users x {n_books:,} canonical books, {len(data):,} ratings")
        if not data:
            raise CommandError("No rated interactions matched; existing neighbors were preserved")
        rows = np.frombuffer(rows, dtype=np.int32)
        cols = np.frombuffer(cols, dtype=np.int32)
        data = np.frombuffer(data, dtype=np.float32)
        matrix = sparse.csr_matrix((data, (rows, cols)), shape=(n_users, n_books))
        counts = sparse.csr_matrix((np.ones(len(data), dtype=np.float32), (rows, cols)), shape=matrix.shape)
        matrix.data /= counts.data
        return matrix, book_index

    def filter_sparse_books(self, matrix, book_index, min_ratings):
        self.stdout.write(f"Dropping books with fewer than {min_ratings} ratings...")
        ratings_per_book = np.asarray((matrix != 0).sum(axis=0)).flatten()
        kept_columns = np.where(ratings_per_book >= min_ratings)[0]
        self.stdout.write(f"Keeping {len(kept_columns):,} of {matrix.shape[1]:,} books")

        filtered = matrix[:, kept_columns]
        old_col_to_id = {v: k for k, v in book_index.items()}
        new_index_to_id = {new_i: old_col_to_id[old_i] for new_i, old_i in enumerate(kept_columns)}
        return filtered, new_index_to_id

    def train_als(self, matrix, n_factors, n_iterations, regularization, bias_regularization=None):
        if bias_regularization is None:
            bias_regularization = regularization
        self.stdout.write(
            f"Training ALS with bias terms ({n_factors} factors, {n_iterations} iterations, "
            f"factor_reg={regularization}, bias_reg={bias_regularization})..."
        )
        n_users, n_items = matrix.shape
        rng = np.random.default_rng(42)
        P = rng.normal(scale=0.1, size=(n_users, n_factors))
        Q = rng.normal(scale=0.1, size=(n_items, n_factors))
        b_u = np.zeros(n_users)
        b_i = np.zeros(n_items)
        mu = float(matrix.data.mean())

        user_rows = matrix.tocsr()
        item_cols = matrix.tocsc()
        reg_diag = np.full(n_factors + 1, regularization)
        reg_diag[0] = bias_regularization
        reg_eye = np.diag(reg_diag)

        def rmse():
            coo = user_rows.tocoo()
            preds = mu + b_u[coo.row] + b_i[coo.col] + np.einsum('ij,ij->i', P[coo.row], Q[coo.col])
            errors = coo.data - preds
            return np.sqrt(np.mean(errors ** 2))

        for iteration in range(n_iterations):
            for u in range(n_users):
                start, end = user_rows.indptr[u], user_rows.indptr[u + 1]
                if start == end:
                    continue
                item_idx = user_rows.indices[start:end]
                ratings = user_rows.data[start:end]
                residual = ratings - mu - b_i[item_idx]

                Q_aug = np.hstack([np.ones((len(item_idx), 1)), Q[item_idx]])
                A = Q_aug.T @ Q_aug + reg_eye
                b = Q_aug.T @ residual
                solution = np.linalg.solve(A, b)
                b_u[u] = solution[0]
                P[u] = solution[1:]

            for i in range(n_items):
                start, end = item_cols.indptr[i], item_cols.indptr[i + 1]
                if start == end:
                    continue
                user_idx = item_cols.indices[start:end]
                ratings = item_cols.data[start:end]
                residual = ratings - mu - b_u[user_idx]

                P_aug = np.hstack([np.ones((len(user_idx), 1)), P[user_idx]])
                A = P_aug.T @ P_aug + reg_eye
                b = P_aug.T @ residual
                solution = np.linalg.solve(A, b)
                b_i[i] = solution[0]
                Q[i] = solution[1:]

            self.stdout.write(f"  completed iteration {iteration + 1}/{n_iterations}, train RMSE: {rmse():.4f}")

        return Q

    def compute_co_occurrence(self, matrix):
        self.stdout.write("Computing co-rater overlap counts...")
        binary = (matrix != 0).astype(np.float64)
        return (binary.T @ binary).tocsr()

    def compute_similarity(self, matrix):
        self.stdout.write("Computing item-item cosine similarity...")
        col_norms = np.asarray(np.sqrt(matrix.multiply(matrix).sum(axis=0))).flatten()
        col_norms[col_norms == 0] = 1
        inv_norms = sparse.diags(1.0 / col_norms)
        normalized = matrix @ inv_norms
        similarity = (normalized.T @ normalized).tocsr()
        co_occurrence = self.compute_co_occurrence(matrix)
        self.stdout.write(f"Similarity matrix: {similarity.shape[0]:,} x {similarity.shape[1]:,}, "
                          f"{similarity.nnz:,} nonzero entries")
        return similarity, co_occurrence

    def compute_als_similarity_blocked(self, Q, co_occurrence, index_to_id, top_k, min_co_raters,
                                       relative_threshold, absolute_floor, block_size=2000):
        self.stdout.write(f"Computing ALS-factor similarity in blocks of {block_size}...")
        n_items = Q.shape[0]
        norms = np.linalg.norm(Q, axis=1)
        norms[norms == 0] = 1
        Q_norm = Q / norms[:, None]

        results = {}
        for start in range(0, n_items, block_size):
            end = min(start + block_size, n_items)
            block_sim = Q_norm[start:end] @ Q_norm.T

            for local_i, i in enumerate(range(start, end)):
                co_row = co_occurrence.getrow(i)
                co_lookup = dict(zip(co_row.indices, co_row.data))

                candidate_indices = np.array([idx for idx in co_lookup if idx != i])
                if len(candidate_indices) == 0:
                    continue
                candidate_scores = block_sim[local_i, candidate_indices]

                valid_mask = np.array([co_lookup[idx] >= min_co_raters for idx in candidate_indices])
                candidate_indices, candidate_scores = candidate_indices[valid_mask], candidate_scores[valid_mask]
                if len(candidate_scores) == 0:
                    continue

                book_max = candidate_scores.max()
                cutoff = max(absolute_floor, book_max * relative_threshold)
                keep_mask = candidate_scores >= cutoff
                candidate_indices, candidate_scores = candidate_indices[keep_mask], candidate_scores[keep_mask]
                if len(candidate_indices) == 0:
                    continue

                order = np.argsort(candidate_scores)[::-1][:top_k]
                results[index_to_id[i]] = [
                    {"book_id": index_to_id[candidate_indices[j]], "score": round(float(candidate_scores[j]), 4)}
                    for j in order
                ]

            del block_sim
            self.stdout.write(f"  processed {end:,} / {n_items:,} books...")

        return results

    def extract_top_k(self, similarity, co_occurrence, index_to_id, top_k, min_co_raters,
                      relative_threshold, absolute_floor, row_offset=0):
        self.stdout.write(
            f"Extracting top {top_k} neighbors per book "
            f"(min {min_co_raters} shared raters, relative={relative_threshold}, floor={absolute_floor})..."
        )
        results = {}
        n_books = similarity.shape[0]
        similarity = similarity.multiply(co_occurrence >= min_co_raters).tocsr()
        similarity.eliminate_zeros()

        for i in range(n_books):
            row = similarity.getrow(i)
            neighbor_indices, neighbor_scores = row.indices, row.data
            valid_mask = neighbor_indices != i + row_offset
            neighbor_indices, neighbor_scores = neighbor_indices[valid_mask], neighbor_scores[valid_mask]
            if len(neighbor_scores) == 0:
                continue

            book_max = neighbor_scores.max()
            cutoff = max(absolute_floor, book_max * relative_threshold)
            keep_mask = neighbor_scores >= cutoff
            neighbor_indices, neighbor_scores = neighbor_indices[keep_mask], neighbor_scores[keep_mask]
            if len(neighbor_indices) == 0:
                continue

            order = np.argsort(neighbor_scores)[::-1][:top_k]
            results[index_to_id[i + row_offset]] = [
                {"book_id": index_to_id[neighbor_indices[j]], "score": round(float(neighbor_scores[j]), 4)}
                for j in order
            ]
            if i % 5000 == 0 and i > 0:
                self.stdout.write(f"  processed {i:,} / {n_books:,} books...")

        return results

    def save_results(self, results):
        self.stdout.write("Saving similar_books to database...")
        books_to_update = [
            Book(id=canonical_pk, similar_books=neighbors)
            for canonical_pk, neighbors in results.items()
        ]

        self.stdout.write(f"Updating {len(books_to_update):,} books...")
        batch_size = 2000
        with transaction.atomic():
            Book.objects.exclude(similar_books=[]).update(similar_books=[])
            for start in range(0, len(books_to_update), batch_size):
                batch = books_to_update[start:start + batch_size]
                Book.objects.bulk_update(batch, ["similar_books"], batch_size=batch_size)
                self.stdout.write(f"  updated {min(start + batch_size, len(books_to_update)):,}")
            transaction.on_commit(cache.clear)

        self.stdout.write(self.style.SUCCESS("Done."))

    def handle(self, *args, **options):
        if options["sample_size"] < 0 or options["block_size"] < 1:
            raise CommandError("Sample size must be nonnegative and block size must be positive")
        edition_to_canonical = self.load_valid_books()
        mapping_path = options["book_id_map"] or Path(options["interactions_path"]).with_name("book_id_map.csv")
        csv_to_canonical = self.load_csv_mapping(
            mapping_path,
            edition_to_canonical,
        )
        fingerprint_data = {
            "version": 1,
            "catalog": sorted(csv_to_canonical.items()),
            "sample_size": options["sample_size"], "seed": options["seed"], "min_ratings": options["min_ratings"],
            "files": [(str(Path(p).resolve()), Path(p).stat().st_size, Path(p).stat().st_mtime_ns)
                      for p in (options["interactions_path"], mapping_path)],
        }
        fingerprint = hashlib.sha256(json.dumps(fingerprint_data).encode()).hexdigest()
        cache_path = Path(options["matrix_cache"]) if options["matrix_cache"] else None
        filtered_matrix = None
        if cache_path and cache_path.exists():
            with np.load(cache_path, allow_pickle=False) as saved:
                if saved["fingerprint"].item() == fingerprint:
                    filtered_matrix = sparse.csr_matrix((saved["data"], saved["indices"], saved["indptr"]), shape=tuple(saved["shape"]))
                    index_to_id = dict(enumerate(saved["book_ids"].tolist()))
                    self.stdout.write("Loaded validated rating matrix from cache")
        if filtered_matrix is None:
            interactions = self.sample_interactions(
                options["interactions_path"], options["sample_size"], csv_to_canonical, options["seed"]
            )
            matrix, book_index = self.build_matrix(interactions)
            del interactions
            filtered_matrix, index_to_id = self.filter_sparse_books(matrix, book_index, options["min_ratings"])
            del matrix
            if cache_path:
                temporary = cache_path.with_suffix(".tmp")
                with temporary.open("wb") as f:
                    np.savez(f, data=filtered_matrix.data, indices=filtered_matrix.indices, indptr=filtered_matrix.indptr,
                             shape=filtered_matrix.shape, book_ids=list(index_to_id.values()), fingerprint=fingerprint)
                temporary.replace(cache_path)
                self.stdout.write(f"Saved rating matrix to {cache_path}")
        norms = np.sqrt(np.asarray(filtered_matrix.multiply(filtered_matrix).sum(axis=0)).ravel())
        normalized = (filtered_matrix @ sparse.diags(1 / norms)).tocsc()
        binary = (filtered_matrix != 0).astype(np.int32).tocsc()
        del filtered_matrix
        normalized_rows = normalized.tocsr()
        binary_rows = binary.tocsr()
        results = {}
        for start in range(0, normalized.shape[1], options["block_size"]):
            end = start + options["block_size"]
            similarity = (normalized[:, start:end].T @ normalized_rows).tocsr()
            co_occurrence = (binary[:, start:end].T @ binary_rows).tocsr()
            results.update(self.extract_top_k(
                similarity, co_occurrence, index_to_id, options["top_k"], options["min_co_raters"],
                options["relative_threshold"], options["absolute_floor"], row_offset=start,
            ))
            self.stdout.write(f"Processed {min(end, normalized.shape[1]):,} / {normalized.shape[1]:,} books")
        self.save_results(results)
