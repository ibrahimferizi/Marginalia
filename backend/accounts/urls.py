from django.urls import path
from .views import (
    CookieTokenObtainView,
    CookieTokenRefreshView,
    LogoutView,
    MeView,
    RegisterView,
    UserProfileView,
    ReadingStatsView,
)

urlpatterns = [
    path("me/stats/", ReadingStatsView.as_view(), name="reading-stats"),
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", CookieTokenObtainView.as_view(), name="token_obtain"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("<str:username>/", UserProfileView.as_view(), name="user-profile"),
]
