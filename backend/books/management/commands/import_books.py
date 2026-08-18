import gzip
import heapq
import json
import math
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Book


class Command(BaseCommand):
    help = "Import a weighted-random sample of books from the Goodreads/UCSD dataset, favoring higher-rated books"

    def add_arguments(self, parser):
        parser.add_argument("books_path", type=str, help="Path to goodreads_books.json.gz")
        parser.add_argument("authors_path", type=str, help="Path to goodreads_book_authors.json.gz")
        parser.add_argument("genres_path", type=str, help="Path to goodreads_book_genres_initial.json.gz")
        parser.add_argument("--sample-size", type=int, default=200_000, help="Number of books to import")

    def load_authors(self, authors_path):
        self.stdout.write("Loading authors lookup...")
        authors = {}
        with gzip.open(authors_path, "rt", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                authors[record["author_id"]] = record["name"]
        self.stdout.write(f"Loaded {len(authors):,} authors")
        return authors

    def load_genres(self, genres_path):
        self.stdout.write("Loading genres lookup...")
        genres = {}
        with gzip.open(genres_path, "rt", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                genres[record["book_id"]] = record["genres"]
        self.stdout.write(f"Loaded genres for {len(genres):,} books")
        return genres

    def build_book_record(self, raw_line, authors, genres_lookup):
        data = json.loads(raw_line)

        title = (data.get("title_without_series") or data.get("title") or "").strip()
        if not title:
            return None

        author_id = None
        if data.get("authors"):
            author_id = data["authors"][0].get("author_id")
        author = authors.get(author_id, "")

        isbn = data.get("isbn13") or data.get("isbn") or ""

        cover_url = data.get("image_url", "")
        if "nophoto" in cover_url:
            cover_url = ""

        published_year = None
        year_str = data.get("publication_year", "")
        if year_str.isdigit():
            published_year = int(year_str)

        try:
            seed_avg_rating = round(float(data.get("average_rating") or 0), 2)
            seed_ratings_count = int(data.get("ratings_count") or 0)
        except ValueError:
            seed_avg_rating, seed_ratings_count = 0, 0

        if seed_ratings_count == 0:
            seed_avg_rating = 0

        book_genres = genres_lookup.get(data.get("book_id"), {})

        if not book_genres and not data.get("description", "").strip():
            return None

        return Book(
            ucsd_id=data.get("book_id"),
            title=title,
            author=author,
            description=data.get("description", ""),
            cover_url=cover_url,
            genres=book_genres,
            published_year=published_year,
            isbn=isbn,
            avg_rating=seed_avg_rating,
            ratings_count=seed_ratings_count,
            seed_avg_rating=seed_avg_rating,
            seed_ratings_count=seed_ratings_count,
        )

    def handle(self, *args, **options):
        books_path = options["books_path"]
        authors_path = options["authors_path"]
        genres_path = options["genres_path"]
        sample_size = options["sample_size"]

        authors = self.load_authors(authors_path)
        genres_lookup = self.load_genres(genres_path)

        self.stdout.write(f"Weighted-sampling {sample_size:,} books from {books_path} "
                           f"(favoring higher ratings_count)...")

        heap = []
        with gzip.open(books_path, "rt", encoding="utf-8") as f:
            for i, line in enumerate(f):
                try:
                    peek = json.loads(line)
                    weight = int(peek.get("ratings_count") or 0) + 1
                except (json.JSONDecodeError, ValueError):
                    weight = 1

                u = random.random()
                key = u ** (1.0 / weight)

                if len(heap) < sample_size:
                    heapq.heappush(heap, (key, i, line))
                elif key > heap[0][0]:
                    heapq.heapreplace(heap, (key, i, line))

                if i % 200_000 == 0 and i > 0:
                    self.stdout.write(f"  scanned {i:,} lines...")

        reservoir = [entry[2] for entry in heap]
        self.stdout.write(f"Sampled {len(reservoir):,} raw lines, parsing...")

        books_to_create = []
        skipped = 0
        for line in reservoir:
            book = self.build_book_record(line, authors, genres_lookup)
            if book is None:
                skipped += 1
                continue
            books_to_create.append(book)

        self.stdout.write(f"Parsed {len(books_to_create):,} books ({skipped} skipped)")

        self.stdout.write("Inserting into database in batches...")
        batch_size = 5000
        total = len(books_to_create)
        for start in range(0, total, batch_size):
            batch = books_to_create[start:start + batch_size]
            with transaction.atomic():
                Book.objects.bulk_create(batch, ignore_conflicts=True)
            self.stdout.write(f"  inserted {min(start + batch_size, total):,} / {total:,}")

        self.stdout.write(self.style.SUCCESS("Import complete."))