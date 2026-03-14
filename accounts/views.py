from urllib import request

from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import User

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
