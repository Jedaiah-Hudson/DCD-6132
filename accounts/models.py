from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager
)

from django.conf import settings
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

class AdditionalEmail(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name = 'additional_email') ## link to the user model
    email = models.EmailField(unique=True) ## unique email field for additional emails
    label = models.CharField(max_length=50, blank=True) ## optional label for the additional email

    class Meta: 
        unique_together = ('user', 'email') ## ensure that each email is unique for a given user
    def __str__(self):
        return f"{self.user.email} - {self.label}" ## display the email and its label when printed

class CapabilityProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='capability_profiles'
    )
    selected_email = models.ForeignKey(
        'AdditionalEmail',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='capability_profiles'
    )
    company_name = models.CharField(max_length=255, blank=True)
    capability_summary = models.TextField(blank=True)
    core_competencies = models.TextField(blank=True)
    differentiators = models.TextField(blank=True)
    naics_codes = models.TextField(blank=True)
    certifications = models.TextField(blank=True)
    past_performance = models.TextField(blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    source_pdf = models.FileField(upload_to='capability_pdfs/', null=True, blank=True)
    ocr_extracted_text = models.TextField(blank=True)
    is_ocr_generated = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name or f"Capability Profile {self.id}"
    


