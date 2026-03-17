import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

def generate_reset_token():
    return secrets.token_urlsafe(32)
##using secrete funct to create secrete token for use
def get_reset_token_expiration():
    return timezone.now() + timedelta(minutes=10)
##time limit of token

def send_password_reset_email(user, reset_link):
    subject = "Reset your password"
    message = (
        f"Hi {user.email},\n\n"
        f"Use the link below to reset your password:\n\n"
        f"{reset_link}\n\n"
        f"This link will expire in 1 hour.\n\n"
        f"If you did not request this, you can ignore this email."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )