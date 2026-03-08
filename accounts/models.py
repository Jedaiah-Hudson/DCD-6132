from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager
)
# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email))
        user.set_password(password) # hash the password before saving
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
    
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True) # unique email field for authentication
    password = models.CharField(max_length=225) ## store hashed password
    date_joined = models.DateTimeField(default=timezone.now) ## track when user joined
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager() ## use the custom user manager for creating users and superusers

    def set_password(self, raw_password):
        self.password = make_password(raw_password) ## hash the password before saving

    def check_password(self, raw_password):
        return check_password(raw_password, self.password) ## check the hashed password against the raw 
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
 # creates user table : id , email(unique) , password, date_joined