from django.db import models
from django.contrib.auth.models import AbstractUser
from pgvector.django import VectorField

# Create your models here.

class User(AbstractUser):
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    taste_vector = models.JSONField(default=dict, blank=True)
    taste_embedding = VectorField(dimensions=384, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username