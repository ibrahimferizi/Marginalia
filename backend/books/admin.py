from django.contrib import admin
from .models import Book

# Register your models here.

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "avg_rating", "ratings_count", "published_year"]
    search_fields = ["title", "author", "isbn"]