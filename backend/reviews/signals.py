from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Review
from django.core.cache import cache

def _recalculate_book_rating(book):
    stats = book.reviews.aggregate(avg=Avg("rating"), count=Count("id"))
    real_avg = stats["avg"] or 0
    real_count = stats["count"] or 0

    seed_sum = float(book.seed_avg_rating) * book.seed_ratings_count
    real_sum = float(real_avg) * real_count
    total_count = book.seed_ratings_count + real_count

    if total_count > 0:
        book.avg_rating = round((seed_sum + real_sum) / total_count, 2)
    else:
        book.avg_rating = 0

    book.ratings_count = total_count
    book.save(update_fields=["avg_rating", "ratings_count"])

def _recalculate_taste_vector(user):
    reviews = Review.objects.filter(user=user).select_related("book")
    taste = {}
    for review in reviews:
        book_genres = review.book.genres or {}
        genre_total = sum(book_genres.values())
        if not genre_total:
            continue
        rating_weight = review.rating
        for genre, count in book_genres.items():
            normalized = count / genre_total
            taste[genre] = taste.get(genre, 0) + normalized * rating_weight
    user.taste_vector = taste
    user.save(update_fields=["taste_vector"])
    cache.delete(f"recommendations:hybrid:{user.id}")

@receiver(post_save, sender=Review)
def update_book_rating_on_save(sender, instance, **kwargs):
    _recalculate_book_rating(instance.book)

@receiver(post_delete, sender=Review)
def update_book_rating_on_delete(sender, instance, **kwargs):
    _recalculate_book_rating(instance.book)

@receiver(post_save, sender=Review)
def update_taste_vector_on_save(sender, instance, **kwargs):
    _recalculate_taste_vector(instance.user)

@receiver(post_delete, sender=Review)
def update_taste_vector_on_delete(sender, instance, **kwargs):
    _recalculate_taste_vector(instance.user)