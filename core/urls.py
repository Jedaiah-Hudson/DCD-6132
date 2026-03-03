from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('notifications/', views.notifications, name='notifications'),
    path('profile/', views.profile, name='profile'),
    path('login/', views.login_api, name='login_api'), #added for login api view, url route, endpoint is POST /login/
    path('login-vis/', views.login_view, name='login_view'),  # page to test login
]