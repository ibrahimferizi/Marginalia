from django.core.management.base import BaseCommand

from books.models import Book

MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 64


class Command(BaseCommand):
    help = "Generate and store embeddings for canonical books using sentence-transformers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-generate embeddings even for books that already have one.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Only process this many books (for testing).",
        )

    def build_input_text(self, book):
        genre_names = ", ".join(book.genres.keys()) if book.genres else ""
        parts = [book.title, genre_names, book.description]
        return ". ".join(p.strip() for p in parts if p and p.strip())

    def handle(self, *args, **options):
        force = options["force"]
        limit = options["limit"]

        from sentence_transformers import SentenceTransformer

        queryset = Book.objects.filter(canonical_book__isnull=True)
        if not force:
            queryset = queryset.filter(embedding__isnull=True)

        if limit:
            queryset = queryset[:limit]

        books = list(queryset)
        total = len(books)

        if total == 0:
            self.stdout.write(self.style.WARNING("No books to embed."))
            return

        self.stdout.write(f"Loading model '{MODEL_NAME}'...")
        model = SentenceTransformer(MODEL_NAME)

        self.stdout.write(f"Embedding {total} canonical books...")

        embedded_count = 0
        skipped_count = 0

        for start in range(0, total, BATCH_SIZE):
            batch = books[start:start + BATCH_SIZE]

            texts = []
            valid_books = []
            for book in batch:
                text = self.build_input_text(book)
                if not text:
                    skipped_count += 1
                    continue
                texts.append(text)
                valid_books.append(book)

            if not texts:
                continue

            vectors = model.encode(texts, show_progress_bar=False)

            for book, vector in zip(valid_books, vectors):
                book.embedding = vector

            Book.objects.bulk_update(valid_books, ["embedding"], batch_size=BATCH_SIZE)
            embedded_count += len(valid_books)

            self.stdout.write(f"  {min(start + BATCH_SIZE, total)}/{total} processed")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Embedded {embedded_count} books, skipped {skipped_count} (no title/description/genres)."
        ))