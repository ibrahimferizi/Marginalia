from django.core.management.base import BaseCommand
from accounts.models import User
from reviews.signals import _recalculate_taste_vector


class Command(BaseCommand):
    help = "Recalculate genre preferences and taste embeddings for existing users with reviews."

    def handle(self, *args, **options):
        users = User.objects.filter(reviews__isnull=False).distinct()
        total = users.count()
        self.stdout.write(f"Backfilling taste_embedding for {total} users with reviews...")

        for i, user in enumerate(users, 1):
            _recalculate_taste_vector(user)
            if i % 50 == 0 or i == total:
                self.stdout.write(f"  {i}/{total} done")

        self.stdout.write(self.style.SUCCESS("Backfill complete."))
