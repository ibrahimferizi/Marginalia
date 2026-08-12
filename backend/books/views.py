from django.shortcuts import render
from rest_framework import filters, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .enrichment import enrich_book
from .models import Book
from .recommendations import hybrid_recommendations
from .serializers import BookSerializer

# Create your views here.

class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "author"]

    def get_queryset(self):
        if self.action == "list":
            return Book.objects.filter(canonical_book__isnull=True)
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