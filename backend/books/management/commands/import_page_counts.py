import gzip
import json

from django.core.management.base import BaseCommand

from books.metadata import parse_page_count
from books.models import Book


class Command(BaseCommand):
    help = "Fill missing page counts from matching Goodreads editions without changing other book data"

    def add_arguments(self, parser):
        parser.add_argument("books_path", help="Path to goodreads_books.json.gz")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        pending = dict(Book.objects.filter(page_count__isnull=True, ucsd_id__isnull=False).exclude(ucsd_id="").values_list("ucsd_id", "id"))
        total = len(pending)
        if not total:
            self.stdout.write("No Goodreads books have missing page counts.")
            return
        batch = []
        matched = 0
        valid = 0
        updated = 0

        def flush():
            nonlocal updated
            if batch and not options["dry_run"]:
                updated += Book.objects.filter(page_count__isnull=True).bulk_update(batch, ["page_count"], batch_size=1000)
            batch.clear()

        with gzip.open(options["books_path"], "rt", encoding="utf-8") as records:
            for scanned, line in enumerate(records, 1):
                record = json.loads(line)
                book_id = pending.pop(str(record.get("book_id")), None)
                if book_id is not None:
                    matched += 1
                    count = parse_page_count(record.get("num_pages"))
                    if count is not None:
                        valid += 1
                        batch.append(Book(id=book_id, page_count=count))
                        if len(batch) >= 1000:
                            flush()
                if scanned % 200000 == 0:
                    self.stdout.write(f"Scanned {scanned:,} records; found {valid:,} valid page counts.")
                if not pending:
                    break
        flush()
        self.stdout.write(self.style.SUCCESS(
            f"Matched {matched:,}/{total:,} editions; valid counts: {valid:,}; updated: {updated:,}; "
            f"missing or invalid counts: {matched - valid:,}; unmatched IDs: {len(pending):,}."
        ))
