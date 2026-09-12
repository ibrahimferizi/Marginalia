from django.core.cache import cache
from django.db import transaction

from books.models import Book

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def build_input_text(book):
    genre_names = ", ".join(book.genres.keys()) if book.genres else ""
    parts = [book.title, genre_names, book.description]
    return ". ".join(p.strip() for p in parts if p and p.strip())


def save_book_embeddings(books):
    from accounts.models import User
    from reviews.signals import _recalculate_taste_vector

    with transaction.atomic():
        Book.objects.bulk_update(books, ["embedding"], batch_size=64)
        users = User.objects.filter(reviews__book_id__in=[book.id for book in books]).distinct()
        for user in users:
            _recalculate_taste_vector(user)
        transaction.on_commit(cache.clear)
