import secrets
from datetime import timedelta
from django.utils import timezone

def generate_reset_token():
    return secrets.token_urlsafe(32)
##using secrete funct to create secrete token for use
def get_reset_token_expiration():
    return timezone.now() + timedelta(minutes=10)
##time limit of token

def send_password_reset_email(user, reset_link):
    print(f"Send this to {user.email}: {reset_link}")