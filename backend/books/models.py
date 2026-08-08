from django.db import models

# Create your models here.

class Book(models.Model):
    ucsd_id = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    google_books_id = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)

    title = models.CharField(max_length=512)
    author = models.CharField(max_length=512, blank=True)
    description = models.TextField(blank=True)
    cover_url = models.URLField(blank=True)
    genres = models.JSONField(default=dict, blank=True)
    published_year = models.PositiveIntegerField(null=True, blank=True)
    isbn = models.CharField(max_length=32, blank=True, db_index=True)

    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    ratings_count = models.PositiveIntegerField(default=0)

    seed_avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    seed_ratings_count = models.PositiveIntegerField(default=0)

    enriched_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title