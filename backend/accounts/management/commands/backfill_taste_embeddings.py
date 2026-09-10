from django.core.management.base import BaseCommand
from accounts.models import User
from reviews.signals import _recalculate_taste_vector


class Command(BaseCommand):
    help = (
        "Backfill taste_embedding for existing users with reviews. "
        "Needed one-time after Phase 3.5's #10 content-score upgrade, since "
        "taste_embedding is only computed inside _recalculate_taste_vector, "
        "which only fires on Review post_save/post_delete signals — users "
        "with reviews predating that change won't have it populated until "
        "they add or delete a review, or this command is run."
    )

    def handle(self, *args, **options):
        users = User.objects.filter(reviews__isnull=False).distinct()
        total = users.count()
        self.stdout.write(f"Backfilling taste_embedding for {total} users with reviews...")

        for i, user in enumerate(users, 1):
            _recalculate_taste_vector(user)
            if i % 50 == 0 or i == total:
                self.stdout.write(f"  {i}/{total} done")

        self.stdout.write(self.style.SUCCESS("Backfill complete."))