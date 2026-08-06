from django.contrib import admin
from .models import ReadingList

# Register your models here.

@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "status", "updated_at"]
    list_filter = ["status"]
    search_fields = ["user__username", "book__title"]