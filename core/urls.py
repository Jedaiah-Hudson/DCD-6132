from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('notifications/', views.notifications, name='notifications'),
    path('profile/', views.profile, name='profile'),
]