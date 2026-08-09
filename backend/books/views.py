from django.shortcuts import render
from rest_framework import filters, viewsets
from rest_framework.response import Response

from .enrichment import enrich_book
from .models import Book
from .serializers import BookSerializer

# Create your views here.

class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "author"]

    def retrieve(self, request, *args, **kwargs):
        book = self.get_object()
        book = enrich_book(book)
        serializer = self.get_serializer(book)
        return Response(serializer.data)