from rest_framework import serializers
from django.utils import timezone
from .models import ReadingList

class ReadingListSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = ReadingList
        fields = [
            "id",
            "user",
            "book",
            "book_title",
            "status",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "book_title", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None:
            if ReadingList.objects.filter(user=request.user, book=attrs["book"]).exists():
                raise serializers.ValidationError("This book is already on your reading list.")
        status = attrs.get("status", self.instance.status if self.instance else ReadingList.Status.WANT_TO_READ)
        status_changed = self.instance is None or status != self.instance.status
        if status_changed:
            if status == ReadingList.Status.READING and not attrs.get("started_at", self.instance.started_at if self.instance else None):
                attrs["started_at"] = timezone.now()
            if status == ReadingList.Status.FINISHED and not attrs.get("finished_at"):
                attrs["finished_at"] = timezone.now()
            elif status != ReadingList.Status.FINISHED:
                attrs["finished_at"] = None
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
