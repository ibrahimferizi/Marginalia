from rest_framework import permissions, viewsets
from .models import ReadingList
from .serializers import ReadingListSerializer
from books.pagination import BookPagination

class ReadingListViewSet(viewsets.ModelViewSet):
    pagination_class = BookPagination
    serializer_class = ReadingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReadingList.objects.filter(user=self.request.user).select_related("book")
        status_param = self.request.query_params.get("status")
        book_param = self.request.query_params.get("book")
        if status_param:
            qs = qs.filter(status=status_param)
        if book_param:
            qs = qs.filter(book_id=book_param)
        return qs
