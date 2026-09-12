from django.db.models import Q
from pgvector.django import CosineDistance

from .models import Book
from .recommendations import exact_content_candidates, unique_work_books


def search_books(query, embedding, limit=20):
    base = Book.objects.filter(canonical_book__isnull=True)
    candidates = {b.id: b for b in exact_content_candidates(base, embedding, 200)}
    for book in base.filter(Q(title__iexact=query) | Q(title__istartswith=query + " (")).annotate(distance=CosineDistance("embedding", embedding)):
        candidates[book.id] = book
    ranked = []
    for book in candidates.values():
        title = book.title.casefold()
        exact_title = title == query.casefold() or title.startswith(query.casefold() + " (")
        score = 1.0 - book.distance if book.distance is not None else 0.0
        ranked.append((exact_title, score, book))
    ranked.sort(key=lambda row: (row[0], row[1], row[2].ratings_count, -row[2].id), reverse=True)
    return unique_work_books((row[2] for row in ranked), limit)
