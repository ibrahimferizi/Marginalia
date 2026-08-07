from django.urls import path
from .views import MeView, RegisterView, UserProfileView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("<str:username>/", UserProfileView.as_view(), name="user-profile"),
]