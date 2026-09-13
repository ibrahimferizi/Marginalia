from django.db.models import Avg, Count
from django.utils import timezone


def reading_stats(user):
    statuses = {"want_to_read": 0, "reading": 0, "finished": 0, "dropped": 0}
    for row in user.reading_list_entries.values("status").annotate(total=Count("id")):
        statuses[row["status"]] = row["total"]
    ratings = {str(value): 0 for value in range(1, 6)}
    for row in user.reviews.values("rating").annotate(total=Count("id")):
        ratings[str(row["rating"])] = row["total"]
    average = user.reviews.aggregate(value=Avg("rating"))["value"]
    year = timezone.localdate().year
    finished = user.reading_list_entries.filter(status="finished")
    return {
        "reading_list": statuses,
        "rated_books": sum(ratings.values()),
        "average_rating": round(average, 2) if average is not None else None,
        "rating_distribution": ratings,
        "year": year,
        "finished_this_year": finished.filter(finished_at__year=year).count(),
        "finished_without_date": finished.filter(finished_at__isnull=True).count(),
    }
