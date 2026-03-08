from django.db import models
from django.contrib.auth.hashers import make_password, check_password ## for password authentication to make and check password with hash
from django.utils import timezone ##tracked when login/out
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# Create your models here.

