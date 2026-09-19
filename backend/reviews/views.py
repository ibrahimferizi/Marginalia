from rest_framework import permissions, viewsets
from .models import Review
from .serializers import ReviewSerializer

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user_id == request.user.id

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("user", "book").all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        book_id = self.request.query_params.get("book")
        if book_id:
            qs = qs.filter(book_id=book_id)
        username = self.request.query_params.get("username")
        if username:
            qs = qs.filter(user__username=username)
        return qs.order_by("-created_at", "-id")
