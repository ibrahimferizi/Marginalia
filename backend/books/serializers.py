from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            "id",
            "ucsd_id",
            "google_books_id",
            "title",
            "author",
            "description",
            "cover_url",
            "genres",
            "published_year",
            "isbn",
            "avg_rating",
            "ratings_count",
        ]
        read_only_fields = ["avg_rating", "ratings_count"]