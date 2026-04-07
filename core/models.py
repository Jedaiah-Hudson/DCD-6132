from django.db import models
from django.contrib.auth.hashers import make_password, check_password ## for password authentication to make and check password with hash
from django.utils import timezone ##tracked when login/out
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# Create your models here.


class Opportunity(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    naics_code = models.CharField(max_length=6, db_index=True)
    agency = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.title
