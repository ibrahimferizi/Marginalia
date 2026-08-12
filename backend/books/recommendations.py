import math
from django.core.cache import cache
from .models import Book

CACHE_TIMEOUT = None

def cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    shared_keys = set(vec_a) & set(vec_b)
    dot = sum(vec_a[k] * vec_b[k] for k in shared_keys)
    norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def build_collab_candidates(user, min_rating=4):
    reviews = user.reviews.select_related("book").filter(rating__gte=min_rating)
    weighted_sums = {}
    weight_totals = {}
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

    predictions = {
        book_id: weighted_sums[book_id] / weight_totals[book_id]
        for book_id in weighted_sums
        if weight_totals[book_id] > 0
    }
    return predictions, books_with_collab_data

def compute_alpha(books_with_collab_data):
    return max(0.5, 1 - 0.15 * books_with_collab_data)

def hybrid_recommendations(user, limit=20):
    cache_key = f"recommendations:hybrid:{user.id}"
    cached_ids = cache.get(cache_key)
    if cached_ids is not None:
        books = Book.objects.filter(id__in=cached_ids)
        books_by_id = {b.id: b for b in books}
        return [books_by_id[i] for i in cached_ids if i in books_by_id]

    if not user.taste_vector:
        return []

    already_reviewed = set(user.reviews.values_list("book_id", flat=True))
    collab_predictions, books_with_collab_data = build_collab_candidates(user)
    alpha = compute_alpha(books_with_collab_data)

    candidates = Book.objects.filter(canonical_book__isnull=True).exclude(
        id__in=already_reviewed
    ).only("id", "title", "author", "genres", "avg_rating", "ratings_count")

    scored = []
    for book in candidates.iterator(chunk_size=2000):
        content_score = cosine_similarity(user.taste_vector, book.genres or {})
        collab_score = collab_predictions.get(book.id, 0) / 5.0
        final_score = alpha * content_score + (1 - alpha) * collab_score
        if final_score > 0:
            scored.append((final_score, book))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top_books = [book for _, book in scored[:limit]]

    cache.set(cache_key, [b.id for b in top_books], timeout=CACHE_TIMEOUT)
    return top_books