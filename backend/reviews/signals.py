from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Review

def _recalculate_book_rating(book):
    stats = book.reviews.aggregate(avg=Avg("rating"), count=Count("id"))
    book.avg_rating = stats["avg"] or 0
    book.ratings_count = stats["count"] or 0
    book.save(update_fields=["avg_rating", "ratings_count"])

@receiver(post_save, sender=Review)
def update_book_rating_on_save(sender, instance, **kwargs):
    _recalculate_book_rating(instance.book)

@receiver(post_delete, sender=Review)
def update_book_rating_on_delete(sender, instance, **kwargs):
    _recalculate_book_rating(instance.book)