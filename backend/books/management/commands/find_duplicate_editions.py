import re
from collections import defaultdict
from django.core.management.base import BaseCommand
from books.models import Book

PLACEHOLDER_AUTHORS = {'unknown', 'anonymous', 'various', ''}

SERIES_SUFFIX_RE = re.compile(r'\s*\([^()]*#\s*[\d.]+[^()]*\)\s*$')


def strip_series_suffix(title):
    title = title or ''
    prev = None
    while prev != title:
        prev = title
        title = SERIES_SUFFIX_RE.sub('', title)
    return title


def normalize_title(title):
    title = strip_series_suffix(title)
    title = (title or '').split(':')[0]
    title = re.sub(r'[^\w\s]', '', title, flags=re.UNICODE)
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title


def normalize_author(author):
    return re.sub(r'[^\w]', '', (author or ''), flags=re.UNICODE).lower()


def normalize_isbn(isbn):
    return re.sub(r'[^0-9Xx]', '', isbn or '').upper()


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


class Command(BaseCommand):
    help = "Detect duplicate editions of the same book and link them via canonical_book"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        books = list(
            Book.objects.filter(canonical_book__isnull=True).only(
                'id', 'title', 'author', 'isbn', 'ratings_count'
            ).iterator(chunk_size=2000)
        )

        uf = UnionFind()
        for book in books:
            uf.find(book.id)

        title_author_groups = defaultdict(list)
        for book in books:
            norm_title = normalize_title(book.title)
            norm_author = normalize_author(book.author)
            if not norm_title or norm_author in PLACEHOLDER_AUTHORS:
                continue
            title_author_groups[(norm_title, norm_author)].append(book.id)

        for key, ids in title_author_groups.items():
            if len(ids) < 2:
                continue
            for other_id in ids[1:]:
                uf.union(ids[0], other_id)

        isbn_groups = defaultdict(list)
        for book in books:
            norm_isbn = normalize_isbn(book.isbn)
            if not norm_isbn:
                continue
            isbn_groups[norm_isbn].append(book.id)

        for key, ids in isbn_groups.items():
            if len(ids) < 2:
                continue
            for other_id in ids[1:]:
                uf.union(ids[0], other_id)

        components = defaultdict(list)
        books_by_id = {b.id: b for b in books}
        for book in books:
            root = uf.find(book.id)
            components[root].append(book)

        to_update = []
        merges = 0
        for root, group in components.items():
            if len(group) < 2:
                continue
            canonical = max(group, key=lambda b: (b.ratings_count, -b.id))
            for b in group:
                if b.id != canonical.id:
                    b.canonical_book_id = canonical.id
                    to_update.append(b)
            merges += 1

        self.stdout.write(
            f"{merges} duplicate groups found "
            f"(title+author pass: {sum(1 for v in title_author_groups.values() if len(v) > 1)}, "
            f"isbn pass: {sum(1 for v in isbn_groups.values() if len(v) > 1)}), "
            f"{len(to_update)} rows to relink"
        )

        if not dry_run:
            Book.objects.bulk_update(to_update, ['canonical_book'], batch_size=1000)
            self.stdout.write(self.style.SUCCESS("Done"))
        else:
            self.stdout.write("Dry run — nothing written")