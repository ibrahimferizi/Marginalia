from rest_framework.routers import DefaultRouter
from .views import ReadingListViewSet

router = DefaultRouter()
router.register("", ReadingListViewSet, basename="readinglist")
urlpatterns = router.urls