from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import User


# Create your views here.
def dashboard(request):
    template_data = {'title': 'Dashboard'}
    return render(request, 'core/dashboard.html', {'template_data': template_data})

def notifications(request):
    template_data = {'title': 'Notifications'}
    return render(request, 'core/notifications.html', {'template_data': template_data})

def profile(request):
    template_data = {'title': 'Profile'}
    return render(request, 'core/profile.html', {'template_data': template_data})

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
    return render(request, 'core/login.html')