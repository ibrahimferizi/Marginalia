import csv
import random

import numpy as np
from scipy import sparse

from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Book


class Command(BaseCommand):
    help = "Compute item-item collaborative filtering similarity from Goodreads interaction data"

    def add_arguments(self, parser):
        parser.add_argument("interactions_path", type=str, help="Path to the interactions .json.gz file")
        parser.add_argument("--sample-size", type=int, default=5_000_000,
                             help="Number of matching interactions to reservoir-sample")
        parser.add_argument("--min-ratings", type=int, default=5,
                             help="Minimum ratings a book needs to be included")
        parser.add_argument("--top-k", type=int, default=15,
                             help="Number of similar books to store per book")
        parser.add_argument("--min-co-raters", type=int, default=5,
                             help="Minimum shared raters required between two books to count as similar")
        parser.add_argument("--min-score", type=float, default=0.25,
                             help="Minimum cosine similarity required to count as a real neighbor")

    def load_valid_books(self):
        self.stdout.write("Loading canonical book set...")
        book_map = {}
        qs = Book.objects.filter(canonical_book__isnull=True).only("id", "ucsd_id").iterator(chunk_size=5000)
        for book in qs:
            if book.ucsd_id:
                book_map[book.ucsd_id] = book.id
        self.stdout.write(f"Loaded {len(book_map):,} canonical books")
        return book_map

    def sample_interactions(self, interactions_path, sample_size, valid_book_ids):
        self.stdout.write(f"Reservoir-sampling up to {sample_size:,} matching interactions...")
        reservoir = []
        seen = 0

        with open(interactions_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for record in reader:
                book_id = record.get("book_id")
                try:
                    rating = int(record.get("rating", 0))
                except (TypeError, ValueError):
                    continue

                if book_id not in valid_book_ids or rating == 0:
                    continue

                seen += 1
                parsed = {"user_id": record["user_id"], "book_id": book_id, "rating": rating}
                if len(reservoir) < sample_size:
                    reservoir.append(parsed)
                else:
                    j = random.randint(0, seen - 1)
                    if j < sample_size:
                        reservoir[j] = parsed

                if seen % 500_000 == 0:
                    self.stdout.write(f"  matched {seen:,} interactions so far...")

        self.stdout.write(f"Sampled {len(reservoir):,} interactions")
        return reservoir

    def build_matrix(self, interactions):
        self.stdout.write("Building rating matrix...")
        user_index, book_index = {}, {}
        rows, cols, data = [], [], []

        for record in interactions:
            user_id, book_id, rating = record["user_id"], record["book_id"], record["rating"]
            if user_id not in user_index:
                user_index[user_id] = len(user_index)
            if book_id not in book_index:
                book_index[book_id] = len(book_index)
            rows.append(user_index[user_id])
            cols.append(book_index[book_id])
            data.append(float(rating))

        n_users, n_books = len(user_index), len(book_index)
        self.stdout.write(f"Matrix: {n_users:,} users x {n_books:,} books, {len(data):,} ratings")
        matrix = sparse.csr_matrix((data, (rows, cols)), shape=(n_users, n_books))
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

    def compute_similarity(self, matrix):
        self.stdout.write("Computing item-item cosine similarity...")
        col_norms = np.asarray(np.sqrt(matrix.multiply(matrix).sum(axis=0))).flatten()
        col_norms[col_norms == 0] = 1
        inv_norms = sparse.diags(1.0 / col_norms)
        normalized = matrix @ inv_norms
        similarity = (normalized.T @ normalized).tocsr()

        self.stdout.write("Computing co-rater overlap counts...")
        binary = (matrix != 0).astype(np.float64)
        co_occurrence = (binary.T @ binary).tocsr()

        self.stdout.write(f"Similarity matrix: {similarity.shape[0]:,} x {similarity.shape[1]:,}, "
                           f"{similarity.nnz:,} nonzero entries")
        return similarity, co_occurrence

    def extract_top_k(self, similarity, co_occurrence, index_to_id, top_k, min_co_raters, min_score):
        self.stdout.write(
            f"Extracting top {top_k} neighbors per book "
            f"(min {min_co_raters} shared raters, min score {min_score})..."
        )
        results = {}
        n_books = similarity.shape[0]

        for i in range(n_books):
            row = similarity.getrow(i)
            co_row = co_occurrence.getrow(i)
            neighbor_indices, neighbor_scores = row.indices, row.data

            co_lookup = dict(zip(co_row.indices, co_row.data))

            mask = np.array([
                idx != i and co_lookup.get(idx, 0) >= min_co_raters and score >= min_score
                for idx, score in zip(neighbor_indices, neighbor_scores)
            ])
            neighbor_indices, neighbor_scores = neighbor_indices[mask], neighbor_scores[mask]
            if len(neighbor_indices) == 0:
                continue

            order = np.argsort(neighbor_scores)[::-1][:top_k]
            results[index_to_id[i]] = [
                {"ucsd_id": index_to_id[neighbor_indices[j]], "score": round(float(neighbor_scores[j]), 4)}
                for j in order
            ]
            if i % 5000 == 0 and i > 0:
                self.stdout.write(f"  processed {i:,} / {n_books:,} books...")

        return results

    def save_results(self, results, book_map):
        self.stdout.write("Saving similar_books to database...")
        books_to_update = []
        for ucsd_id, neighbors in results.items():
            book_pk = book_map.get(ucsd_id)
            if book_pk is None:
                continue
            resolved = [
                {"book_id": book_map[n["ucsd_id"]], "score": n["score"]}
                for n in neighbors if n["ucsd_id"] in book_map
            ]
            if resolved:
                books_to_update.append(Book(id=book_pk, similar_books=resolved))

        self.stdout.write(f"Updating {len(books_to_update):,} books...")
        batch_size = 2000
        for start in range(0, len(books_to_update), batch_size):
            batch = books_to_update[start:start + batch_size]
            with transaction.atomic():
                Book.objects.bulk_update(batch, ["similar_books"], batch_size=batch_size)
            self.stdout.write(f"  updated {min(start + batch_size, len(books_to_update)):,}")

        self.stdout.write(self.style.SUCCESS("Done."))

    def handle(self, *args, **options):
        book_map = self.load_valid_books()
        interactions = self.sample_interactions(
            options["interactions_path"], options["sample_size"], set(book_map.keys())
        )
        matrix, book_index = self.build_matrix(interactions)
        filtered_matrix, index_to_id = self.filter_sparse_books(matrix, book_index, options["min_ratings"])
        similarity, co_occurrence = self.compute_similarity(filtered_matrix)
        results = self.extract_top_k(
            similarity, co_occurrence, index_to_id,
            options["top_k"], options["min_co_raters"], options["min_score"],
        )
        self.save_results(results, book_map)