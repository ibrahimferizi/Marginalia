import random
from rest_framework import filters, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .enrichment import enrich_book
from .models import Book
from .recommendations import hybrid_recommendations, similar_books_for, recommendation_candidates, preferred_editions, unique_work_books
from .serializers import BookSerializer

from django.db.models import Case, When, Value, IntegerField
from rest_framework.exceptions import ValidationError

from .embeddings import get_embedding_model
from .search import search_books

class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "author"]

    def get_queryset(self):
        if self.action == "list":
            sort = self.request.query_params.get("sort", "popular")
            if sort not in {"popular", "relevance"}:
                raise ValidationError({"sort": "Choose popular or relevance."})
            qs = Book.objects.filter(canonical_book__isnull=True)
            query = self.request.query_params.get("search", "").strip()
            if sort == "relevance" and query:
                qs = qs.annotate(match_priority=Case(
                    When(title__iexact=query, then=Value(0)),
                    When(title__istartswith=query, then=Value(1)),
                    When(author__iexact=query, then=Value(2)),
                    default=Value(3), output_field=IntegerField(),
                ))
                return qs.order_by("match_priority", "-ratings_count", "id")
            return qs.order_by("-ratings_count", "id")
        return Book.objects.all()

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def popular(self, request):
        excluded = set()
        if request.user.is_authenticated:
            excluded.update(request.user.reviews.values_list("book_id", flat=True))
            excluded.update(request.user.reading_list_entries.exclude(status="want_to_read").values_list("book_id", flat=True))
        candidates = recommendation_candidates(excluded).order_by("-ratings_count", "id")[:500]
        pool = preferred_editions(unique_work_books(candidates, 200))
        selected = random.SystemRandom().sample(pool, min(20, len(pool)))
        return Response(self.get_serializer(selected, many=True).data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def explore(self, request):
        mode = request.query_params.get("mode", "hybrid")
        if mode not in {"hybrid", "content", "collaborative"}:
            raise ValidationError({"mode": "Choose hybrid, content or collaborative."})
        source = request.query_params.get("source")
        if source is not None:
            try:
                source = int(source)
                if source <= 0:
                    raise ValueError
            except ValueError:
                raise ValidationError({"source": "Choose a valid source book."})
        books = hybrid_recommendations(request.user, limit=None, mode=mode)
        sources = {item["id"]: {"id": item["id"], "title": item["title"]} for book in books for item in book.recommendation_sources}
        if source is not None:
            books = [book for book in books if any(item["id"] == source for item in book.recommendation_sources)]
        page = self.paginate_queryset(books)
        response = self.get_paginated_response(self.get_serializer(page, many=True).data)
        response.data["sources"] = sorted(sources.values(), key=lambda item: (item["title"], item["id"]))
        return response

    def retrieve(self, request, *args, **kwargs):
        book = self.get_object()
        book = enrich_book(book)
        serializer = self.get_serializer(book)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def recommended(self, request):
        books = hybrid_recommendations(request.user)
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny])
    def similar(self, request, pk=None):
        book = self.get_object()
        books = similar_books_for(book)
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def semantic_search(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=400)
        if len(query) > 500:
            return Response({"detail": "Search queries must be at most 500 characters."}, status=400)

        sort = request.query_params.get("sort", "relevance")
        if sort not in {"popular", "relevance"}:
            raise ValidationError({"sort": "Choose popular or relevance."})
        model = get_embedding_model()
        query_embedding = model.encode(query)
        books = search_books(query, query_embedding, limit=None, sort=sort)
        page = self.paginate_queryset(books)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
