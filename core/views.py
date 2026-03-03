from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import User


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
