from django.shortcuts import render
from rest_framework import filters, viewsets
from .models import Book
from .serializers import BookSerializer

# Create your views here.

class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "author"]