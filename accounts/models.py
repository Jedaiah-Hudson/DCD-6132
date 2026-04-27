from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager
)
from django.db.models.functions import Lower

from django.conf import settings
from django.core import signing

from contracts.models import NAICSCode


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
    ##adding frogoten info feilds
    reset_token = models.CharField(max_length=255, blank=True, null=True) ## field to store password reset token
    reset_token_expiration = models.DateTimeField(blank=True, null=True)
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
        related_name='additional_email'
    )
    email = models.EmailField()
    label = models.CharField(max_length=50, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                name='unique_lower_email_globally',
            ),
        ]
        
    def __str__(self):
        return f"{self.user.email} - {self.label}" ## display the email and its label when printed


class MailboxConnection(models.Model):
    class Provider(models.TextChoices):
        GMAIL = "gmail", "Gmail"
        OUTLOOK = "outlook", "Outlook"

    class Status(models.TextChoices):
        CONNECTED = "connected", "Connected"
        NEEDS_ATTENTION = "needs_attention", "Needs attention"
        DISCONNECTED = "disconnected", "Disconnected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mailbox_connections",
    )
    additional_email = models.ForeignKey(
        AdditionalEmail,
        on_delete=models.SET_NULL,
        related_name="mailbox_connections",
        null=True,
        blank=True,
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    mailbox_email = models.EmailField()
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scope = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.CONNECTED,
        db_index=True,
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_cursor = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "user",
                "provider",
                Lower("mailbox_email"),
                name="unique_mailbox_connection_per_user_provider_email",
            ),
        ]

    # Security debt: Django signing prevents silent token tampering but is not
    # true at-rest encryption. Replace with Fernet/KMS-backed encrypted fields
    # before storing production mailbox OAuth tokens.
    TOKEN_SIGNING_SALT = "accounts.mailbox_connection.token"

    def _sign_token(self, raw_token):
        if not raw_token:
            return ""
        return signing.dumps(raw_token, salt=self.TOKEN_SIGNING_SALT)

    def _unsign_token(self, signed_token):
        if not signed_token:
            return ""
        try:
            return signing.loads(signed_token, salt=self.TOKEN_SIGNING_SALT)
        except signing.BadSignature:
            return ""

    def set_access_token(self, raw_token):
        self.access_token = self._sign_token(raw_token)

    def get_access_token(self):
        return self._unsign_token(self.access_token)

    def set_refresh_token(self, raw_token):
        self.refresh_token = self._sign_token(raw_token)

    def get_refresh_token(self):
        return self._unsign_token(self.refresh_token)

    def set_tokens(self, access_token="", refresh_token=""):
        self.set_access_token(access_token)
        self.set_refresh_token(refresh_token)

    def __str__(self):
        return f"{self.user.email} - {self.get_provider_display()} - {self.mailbox_email}"

class CapabilityProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='capability_profiles'
    )

    company_name = models.CharField(max_length=255, blank=True)
    capability_summary = models.TextField(blank=True)
    core_competencies = models.TextField(blank=True)
    differentiators = models.TextField(blank=True)

    naics_codes = models.ManyToManyField(
        NAICSCode,
        blank=True,
        related_name="capability_profiles"
    )
    
    
    certifications = models.TextField(blank=True)
    past_performance = models.TextField(blank=True)
    services_offered = models.JSONField(default=list, blank=True)
    target_industries = models.JSONField(default=list, blank=True)
    preferred_opportunity_types = models.JSONField(default=list, blank=True)
    matchmaking_tags = models.JSONField(default=list, blank=True)
    geographic_preferences = models.JSONField(default=list, blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    ocr_extracted_text = models.TextField(blank=True, default='')
    def __str__(self):
        return self.company_name or f"Capability Profile {self.id}"
    
