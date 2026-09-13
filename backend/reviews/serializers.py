from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "user", "username", "book", "book_title", "rating", "text", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "username", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None:
            if Review.objects.filter(user=request.user, book=attrs["book"]).exists():
                raise serializers.ValidationError("You've already reviewed this book.")
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
