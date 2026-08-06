from django.db import models
from django.conf import settings

# Create your models here.

class ReadingList(models.Model):
    class Status(models.TextChoices):
        WANT_TO_READ = "want_to_read", "Want to Read"
        READING = "reading", "Reading"
        FINISHED = "finished", "Finished"
        DROPPED = "dropped", "Dropped"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_list_entries"
    )
    book = models.ForeignKey(
        "books.Book", on_delete=models.CASCADE, related_name="reading_list_entries"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WANT_TO_READ)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "book")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} [{self.status}]"