from urllib import request

from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import User
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .serializers import PasswordResetConfirmSerializer
from .serializers import PasswordResetRequestSerializer
from .utils import generate_reset_token, get_reset_token_expiration, send_password_reset_email, send_password_reset_email

# Create your views here.


# view to login api endpoints
@api_view(['POST'])
def login_api(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    #check if email exist in database
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response ({
            "success": False,
            "message": "Email does not exist."
        }, status=status.HTTP_404_NOT_FOUND)
   
    #check if password is correct
    if not user.check_password(password):
        return Response ({
            "success": False,
            "message": "Incorrect password. Try again."
        }, status=status.HTTP_401_UNAUTHORIZED)
   
    #create/get token for user
    token, created = Token.objects.get_or_create(user=user)
    return Response({
        "success": True,
        "message": "Login Successful!",
        "token": token.key,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }, status=status.HTTP_200_OK)

def login_view(request):
    return render(request, 'accounts/login.html')

@api_view(['POST'])
def signup_api(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if User.objects.filter(email=email).exists():
        return Response({
            "success": False,
            "message": "Email already registered."
        }, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(email=email, password=password)

    token = Token.objects.create(user=user)

    return Response({
        "success": True,
        "message": "Account created successfully!",
        "token": token.key,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }, status=status.HTTP_201_CREATED)

def signup_view(request):
    return render(request, 'accounts/signUp.html')


User = get_user_model()

class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # safer to avoid revealing whether email exists
            return Response(
                {"message": "If an account with that email exists, a reset link has been sent."},
                status=status.HTTP_200_OK
            )

        token = generate_reset_token()
        expiration = get_reset_token_expiration()

        user.reset_token = token
        user.reset_token_expiration = expiration
        user.save(update_fields=["reset_token", "reset_token_expiration"])

        reset_link = f"http://localhost:3000/reset-password?token={token}"
        # replace localhost:3000 with your frontend URL later

        # Placeholder for now:
        send_password_reset_email(user, reset_link)
        
        return Response(
            {
                "message": "If an account with that email exists, a reset link has been sent.",
                "reset_link_placeholder": reset_link  # remove later in production
            },
            status=status.HTTP_200_OK
        )
    

class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(reset_token=token)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid reset token."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.reset_token_expiration:
            return Response(
                {"error": "Reset token is invalid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.reset_token_expiration < timezone.now():
            return Response(
                {"error": "Reset token has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as e:
            return Response(
                {"error": e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )
        
## user password is update an dtokeninfo is cleared 
        user.set_password(new_password)  # hashes password properly
        user.reset_token = None
        user.reset_token_expiration = None
        user.save(update_fields=["password", "reset_token", "reset_token_expiration"])

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK
        )