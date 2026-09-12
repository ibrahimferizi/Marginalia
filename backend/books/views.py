from django.shortcuts import render
from rest_framework import filters, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .enrichment import enrich_book
from .models import Book
from .recommendations import hybrid_recommendations, similar_books_for
from .serializers import BookSerializer

from django.db.models import F, FloatField, ExpressionWrapper
from django.db.models.functions import Cast

from .embeddings import get_embedding_model
from .search import search_books

# Create your views here.

class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "author"]

    def get_queryset(self):
        if self.action == "list":
            is_search = bool(self.request.query_params.get("search"))

            qs = Book.objects.filter(canonical_book__isnull=True)

            BOXSET_PATTERN = r'(box\s*.?set|boxed\s*set|omnibus|collection|bundle|trilogy|the complete|books? \d+.?\d*\b)'
            if not is_search:
                qs = qs.exclude(title__iregex=BOXSET_PATTERN).exclude(cover_url="")

            M = 1000
            C = 3.5
            v = Cast(F("ratings_count"), FloatField())
            r = Cast(F("avg_rating"), FloatField())
            weighted_rating = ExpressionWrapper(
                (v / (v + M)) * r + (M / (v + M)) * C,
                output_field=FloatField(),
            )

            return qs.annotate(weighted_rating=weighted_rating).order_by("-weighted_rating", "id")
        return Book.objects.all()

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

        model = get_embedding_model()
        query_embedding = model.encode(query)

        books = search_books(query, query_embedding)

        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)
