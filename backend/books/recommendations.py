import math
from django.core.cache import cache
from .models import Book
import numpy as np
from pgvector.django import CosineDistance

CACHE_TIMEOUT = None

def cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    shared_keys = set(vec_a) & set(vec_b)
    dot = sum(vec_a[k] * vec_b[k] for k in shared_keys)
    norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def cosine_similarity_vectors(vec_a, vec_b):
    if vec_a is None or vec_b is None:
        return 0.0
    a = np.asarray(vec_a, dtype=float)
    b = np.asarray(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def build_collab_candidates(user, min_rating=4):
    reviews = user.reviews.select_related("book").filter(rating__gte=min_rating)
    weighted_sums = {}
    weight_totals = {}
    top_source = {}
    books_with_collab_data = 0

    for review in reviews:
        neighbors = review.book.similar_books or []
        if neighbors:
            books_with_collab_data += 1
        for neighbor in neighbors:
            book_id = neighbor["book_id"]
            score = neighbor["score"]
            weighted_sums[book_id] = weighted_sums.get(book_id, 0) + score * review.rating
            weight_totals[book_id] = weight_totals.get(book_id, 0) + score

            if book_id not in top_source or score > top_source[book_id][1]:
                top_source[book_id] = (review.book, score)

    predictions = {
        book_id: weighted_sums[book_id] / weight_totals[book_id]
        for book_id in weighted_sums
        if weight_totals[book_id] > 0
    }
    return predictions, books_with_collab_data, top_source

def compute_alpha(books_with_collab_data):
    return max(0.5, 1 - 0.15 * books_with_collab_data)

def shared_genres(vec_a: dict, vec_b: dict, top_n=2):
    shared = set(vec_a) & set(vec_b)
    ranked = sorted(shared, key=lambda k: vec_a[k] * vec_b[k], reverse=True)
    return ranked[:top_n]

def hybrid_recommendations(user, limit=20, content_pool_size=500):
    cache_key = f"recommendations:hybrid:v4:{user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        book_ids = [entry["id"] for entry in cached]
        books = Book.objects.filter(id__in=book_ids)
        books_by_id = {b.id: b for b in books}
        result = []
        for entry in cached:
            book = books_by_id.get(entry["id"])
            if book:
                book.recommendation_reason = entry["reason"]
                result.append(book)
        return result

    if not user.taste_vector:
        return []

    already_reviewed = set(user.reviews.values_list("book_id", flat=True))
    collab_predictions, books_with_collab_data, top_source = build_collab_candidates(user)
    alpha = compute_alpha(books_with_collab_data)

    base_qs = Book.objects.filter(canonical_book__isnull=True).exclude(id__in=already_reviewed)
    fields = ("id", "title", "author", "genres", "avg_rating", "ratings_count")

    candidates_by_id = {}
    taste_embedding = user.taste_embedding

    if taste_embedding is not None:
        content_qs = (
            base_qs.filter(embedding__isnull=False)
            .annotate(distance=CosineDistance("embedding", taste_embedding))
            .order_by("distance")
            .only(*fields)[:content_pool_size]
        )
        for book in content_qs:
            candidates_by_id[book.id] = (book, 1.0 - book.distance)

    collab_ids = set(collab_predictions.keys()) - set(candidates_by_id.keys())
    if collab_ids:
        if taste_embedding is not None:
            collab_content_qs = (
                base_qs.filter(id__in=collab_ids, embedding__isnull=False)
                .annotate(distance=CosineDistance("embedding", taste_embedding))
                .only(*fields)
            )
            for book in collab_content_qs:
                candidates_by_id[book.id] = (book, 1.0 - book.distance)

        still_missing = collab_ids - set(candidates_by_id.keys())
        if still_missing:
            no_embedding_qs = base_qs.filter(id__in=still_missing).only(*fields)
            for book in no_embedding_qs:
                candidates_by_id[book.id] = (book, 0.0)

    scored = []
    for book, content_score in candidates_by_id.values():
        raw_collab = collab_predictions.get(book.id, 0) / 5.0
        weighted_content = alpha * content_score
        weighted_collab = (1 - alpha) * raw_collab
        final_score = weighted_content + weighted_collab

        if final_score > 0:
            content_share = content_score
            collab_share = raw_collab

            if collab_share > content_share and book.id in top_source:
                source_book, _ = top_source[book.id]
                book.recommendation_reason = {
                    "type": "collaborative",
                    "source_book": {"id": source_book.id, "title": source_book.title},
                }
            else:
                book.recommendation_reason = {
                    "type": "content",
                    "shared_genres": shared_genres(user.taste_vector, book.genres or {}),
                }
            scored.append((final_score, book))

    scored.sort(key=lambda pair: (pair[0], pair[1].ratings_count), reverse=True)
    top_books = [book for _, book in scored[:limit]]

    cache_payload = [
        {"id": b.id, "reason": b.recommendation_reason} for b in top_books
    ]
    cache.set(cache_key, cache_payload, timeout=CACHE_TIMEOUT)
    return top_books

def content_similar_books(book, limit=15):
    cache_key = f"similar_books:content:v2:{book.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        book_ids = [entry["id"] for entry in cached]
        books = Book.objects.filter(id__in=book_ids)
        books_by_id = {b.id: b for b in books}
        result = []
        for entry in cached:
            candidate = books_by_id.get(entry["id"])
            if candidate:
                candidate.recommendation_reason = entry["reason"]
                result.append(candidate)
        return result

    if not book.genres:
        return []

    candidates = Book.objects.filter(canonical_book__isnull=True).exclude(
        id=book.id
    ).only("id", "title", "author", "genres", "avg_rating", "ratings_count")

    scored = []
    for candidate in candidates.iterator(chunk_size=2000):
        score = cosine_similarity(book.genres, candidate.genres or {})
        if score > 0:
            candidate.recommendation_reason = {
                "type": "content",
                "shared_genres": shared_genres(book.genres, candidate.genres or {}),
            }
            scored.append((score, candidate))

    scored.sort(key=lambda pair: (pair[0], pair[1].ratings_count), reverse=True)
    top_books = [b for _, b in scored[:limit]]

    cache_payload = [
        {"id": b.id, "reason": b.recommendation_reason} for b in top_books
    ]
    cache.set(cache_key, cache_payload, timeout=None)
    return top_books


def similar_books_for(book, limit=15):
    neighbors = book.similar_books or []
    if neighbors:
        neighbor_ids = [n["book_id"] for n in neighbors[:limit]]
        books = Book.objects.filter(id__in=neighbor_ids)
        books_by_id = {b.id: b for b in books}
        result = []
        for n in neighbors[:limit]:
            candidate = books_by_id.get(n["book_id"])
            if candidate:
                candidate.recommendation_reason = {"type": "collaborative"}
                result.append(candidate)
        return result

    return content_similar_books(book, limit=limit)