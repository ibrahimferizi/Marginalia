from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    recommendation_reason = serializers.SerializerMethodField()
    recommendation_sources = serializers.SerializerMethodField()
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
            "similar_books",
            "recommendation_reason",
            "recommendation_sources",
        ]
        read_only_fields = ["avg_rating", "ratings_count"]

    def get_recommendation_reason(self, obj):
        return getattr(obj, "recommendation_reason", None)

    def get_recommendation_sources(self, obj):
        return getattr(obj, "recommendation_sources", [])
