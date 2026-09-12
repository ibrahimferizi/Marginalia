import math
from django.core.cache import cache
from django.db.models import F, Q, Value
from .models import Book
import numpy as np
from pgvector.django import CosineDistance

CACHE_TIMEOUT = None

STUDY_AID_PATTERN = r'\m(monarch\s+notes|cliffs?\s*notes|spark\s*notes)\M|\msummary\s*(&\s*)?study\s+guide\M|\mby\M.+\mstudy\s+guide\M'


def multi_volume_candidates():
    return (
        Q(title__iregex=r'\m(box(ed)?[ -]*sets?|omnib(us|uses)|bundles?)\M')
        | Q(title__iregex=r'\([^)]*#\s*[0-9]+\s*[-â€“]\s*[0-9]+[^)]*\)')
        | (Q(title__iregex=r'\mtrilog(y|ies)\M') & Q(description__iregex=r'\m(this|one|single) volume (includes|contains|collects)\M'))
    )

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

def build_collab_candidates(user, candidates):
    reviews = user.reviews.select_related("book", "book__canonical_book").filter(rating__gte=3).order_by("book_id")
    seeds = {}
    weights = {3: 0.2, 4: 0.8, 5: 1.0}
    for review in reviews:
        book = review.book.canonical_book or review.book
        key = ("work", book.work_id) if book.work_id else ("book", book.id)
        if key not in seeds or review.rating > seeds[key][1]:
            seeds[key] = (book, review.rating)
    neighbor_ids = {n["book_id"] for book, _ in seeds.values() for n in book.similar_books or [] if n["score"] > 0}
    eligible = set(candidates.filter(id__in=neighbor_ids).values_list("id", flat=True))
    support = {}
    top_source = {}
    books_with_collab_data = 0
    confidence = 0.0
    for book, rating in seeds.values():
        neighbors = [n for n in book.similar_books or [] if n["book_id"] in eligible and n["score"] > 0]
        if neighbors and rating >= 4:
            books_with_collab_data += 1
        if neighbors:
            confidence = max(confidence, weights[rating])
        for neighbor in neighbors:
            book_id = neighbor["book_id"]
            score = weights[rating] * neighbor["score"]
            support[book_id] = support.get(book_id, 0.0) + score
            if book_id not in top_source or score > top_source[book_id][1]:
                top_source[book_id] = (book, score)
    peak = max(support.values(), default=0.0)
    predictions = {bid: confidence * value / peak for bid, value in support.items()} if peak else {}
    return predictions, books_with_collab_data, top_source

def compute_alpha(books_with_collab_data):
    return max(0.5, 1 - 0.15 * books_with_collab_data)

def shared_genres(vec_a: dict, vec_b: dict, top_n=2):
    shared = set(vec_a) & set(vec_b)
    ranked = sorted(shared, key=lambda k: vec_a[k] * vec_b[k], reverse=True)
    return ranked[:top_n]

def exact_content_candidates(queryset, embedding, limit=500):
    return (
        queryset.filter(embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", embedding))
        .order_by((Value(1.0) - F("distance")).desc(), "id")[:limit]
    )


def recommendation_candidates(reviewed_ids, include_study_aids=False):
    reviewed_ids = set(reviewed_ids)
    reviewed = list(Book.objects.filter(id__in=reviewed_ids).values_list("canonical_book_id", "work_id"))
    canonical_ids = {canonical_id for canonical_id, _ in reviewed if canonical_id is not None}
    work_ids = {work_id for _, work_id in reviewed if work_id}
    work_ids.update(
        Book.objects.filter(id__in=canonical_ids).exclude(work_id="").values_list("work_id", flat=True)
    )
    candidates = (
        Book.objects.filter(canonical_book__isnull=True)
        .exclude(id__in=reviewed_ids | canonical_ids)
        .exclude(work_id__in=work_ids)
    )
    if not include_study_aids:
        candidates = candidates.exclude(title__iregex=STUDY_AID_PATTERN)
    return candidates


def unique_work_books(books, limit):
    result = []
    seen = set()
    for book in books:
        if len(result) >= limit:
            break
        key = ("work", book.work_id) if book.work_id else ("book", book.id)
        if key not in seen:
            seen.add(key)
            result.append(book)
    return result


def hybrid_recommendations(user, limit=20, content_pool_size=500):
    cache_key = f"recommendations:hybrid:v8:{user.id}"
    use_cache = limit == 20 and content_pool_size == 500
    cached = cache.get(cache_key) if use_cache else None
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

    already_reviewed = set(user.reviews.values_list("book_id", flat=True))
    base_qs = recommendation_candidates(already_reviewed)
    collab_predictions, books_with_collab_data, top_source = build_collab_candidates(user, base_qs)
    alpha = (0.85 if books_with_collab_data < 2 else 0.7) if collab_predictions else 1.0
    if user.taste_embedding is None:
        alpha = 0.0
    fields = ("id", "title", "author", "genres", "avg_rating", "ratings_count", "work_id")

    candidates_by_id = {}
    taste_embedding = user.taste_embedding

    if taste_embedding is not None:
        content_qs = exact_content_candidates(base_qs.only(*fields), taste_embedding, content_pool_size)
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
        raw_collab = collab_predictions.get(book.id, 0)
        weighted_content = alpha * content_score
        weighted_collab = (1 - alpha) * raw_collab
        final_score = weighted_content + weighted_collab

        if final_score > 0:
            if weighted_collab > 0 and book.id in top_source:
                source_book, _ = top_source[book.id]
                book.recommendation_reason = {
                    "type": "hybrid" if weighted_content > 0 else "collaborative",
                    "source_book": {"id": source_book.id, "title": source_book.title},
                }
            else:
                book.recommendation_reason = {
                    "type": "content",
                    "method": "embedding",
                }
            scored.append((final_score, book))

    scored.sort(key=lambda pair: (pair[0], pair[1].ratings_count, -pair[1].id), reverse=True)
    top_books = unique_work_books((book for _, book in scored), limit)

    cache_payload = [
        {"id": b.id, "reason": b.recommendation_reason} for b in top_books
    ]
    if use_cache:
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
