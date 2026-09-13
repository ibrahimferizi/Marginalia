from django.db import models
from pgvector.django import HnswIndex, VectorField

# Create your models here.

class Book(models.Model):
    ucsd_id = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    work_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    language_code = models.CharField(max_length=32, blank=True, default="")
    source_format = models.CharField(max_length=255, blank=True, default="")
    google_books_id = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)

    title = models.CharField(max_length=512)
    author = models.CharField(max_length=512, blank=True)
    description = models.TextField(blank=True)
    cover_url = models.URLField(blank=True)
    genres = models.JSONField(default=dict, blank=True)
    published_year = models.PositiveIntegerField(null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    isbn = models.CharField(max_length=32, blank=True, db_index=True)

    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    ratings_count = models.PositiveIntegerField(default=0)

    seed_avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    seed_ratings_count = models.PositiveIntegerField(default=0)

    enriched_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    canonical_book = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='duplicate_editions',
    )

    similar_books = models.JSONField(default=list, blank=True)

    embedding = VectorField(dimensions=384, null=True, blank=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            HnswIndex(
                name="book_embedding_hnsw_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return self.title
