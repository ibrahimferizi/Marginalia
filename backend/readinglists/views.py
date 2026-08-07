from django.shortcuts import render
from rest_framework import permissions, viewsets
from .models import ReadingList
from .serializers import ReadingListSerializer

# Create your views here.

class ReadingListViewSet(viewsets.ModelViewSet):
    serializer_class = ReadingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReadingList.objects.filter(user=self.request.user).select_related("book")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs