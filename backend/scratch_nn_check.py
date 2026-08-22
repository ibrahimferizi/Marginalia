import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")  # adjust to your actual settings module path
django.setup()

from pgvector.django import CosineDistance
from books.models import Book

SEARCH_TITLE = "Brave New World"  # change this to test different books
TOP_N = 10

target = Book.objects.filter(
    title__icontains=SEARCH_TITLE,
    canonical_book__isnull=True,
    embedding__isnull=False,
).first()

if not target:
    print(f"No embedded canonical book found matching '{SEARCH_TITLE}'")
else:
    print(f"Target: {target.title} by {target.author}")
    print(f"Genres: {list(target.genres.keys())}")
    print("-" * 60)

    neighbors = (
        Book.objects.filter(canonical_book__isnull=True, embedding__isnull=False)
        .exclude(id=target.id)
        .annotate(distance=CosineDistance("embedding", target.embedding))
        .order_by("distance")[:TOP_N]
    )

    for book in neighbors:
        print(f"  {book.distance:.4f}  {book.title} — {book.author}  {list(book.genres.keys())}")