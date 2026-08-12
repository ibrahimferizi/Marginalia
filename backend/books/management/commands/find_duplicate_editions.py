import re
from collections import defaultdict
from django.core.management.base import BaseCommand
from books.models import Book

PLACEHOLDER_AUTHORS = {'unknown', 'anonymous', 'various', ''}

def normalize_title(title):
    title = (title or '').split(':')[0]
    title = re.sub(r'[^\w\s]', '', title, flags=re.UNICODE)
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title

def normalize_author(author):
    return re.sub(r'[^\w]', '', (author or ''), flags=re.UNICODE).lower()

class Command(BaseCommand):
    help = "Detect duplicate editions of the same book and link them via canonical_book"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        groups = defaultdict(list)

        qs = Book.objects.filter(canonical_book__isnull=True).only(
            'id', 'title', 'author', 'ratings_count'
        ).iterator(chunk_size=2000)

        for book in qs:
            norm_title = normalize_title(book.title)
            norm_author = normalize_author(book.author)
            if not norm_title or norm_author in PLACEHOLDER_AUTHORS:
                continue
            key = (norm_title, norm_author)
            groups[key].append(book)

        to_update = []
        merges = 0
        for key, books in groups.items():
            if len(books) < 2:
                continue
            canonical = max(books, key=lambda b: (b.ratings_count, -b.id))
            for b in books:
                if b.id != canonical.id:
                    b.canonical_book_id = canonical.id
                    to_update.append(b)
            merges += 1

        self.stdout.write(f"{merges} duplicate groups found, {len(to_update)} rows to relink")

        if not dry_run:
            Book.objects.bulk_update(to_update, ['canonical_book'], batch_size=1000)
            self.stdout.write(self.style.SUCCESS("Done"))
        else:
            self.stdout.write("Dry run — nothing written")