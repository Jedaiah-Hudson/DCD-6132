from django.db import models
from django.contrib.auth.hashers import make_password, check_password ## for password authentication to make and check password with hash
from django.utils import timezone ##tracked when login/out
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings

# Create your models here.


class Opportunity(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    naics_code = models.CharField(max_length=6, db_index=True)
    agency = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, blank=True, default='Not Started')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.title


class UserMatchmakingCache(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matchmaking_cache',
    )
    results = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    profile_snapshot_hash = models.CharField(max_length=64, blank=True)
    opportunity_snapshot_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-generated_at', '-updated_at']

    def __str__(self):
        return f'Matchmaking cache for {self.user}'
