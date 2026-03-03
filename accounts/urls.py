from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_api, name='signup_api'),
    path('signup-vis/', views.signup_view, name='signup_view'),
    path('login/', views.login_api, name='login_api'),
    path('login-vis/', views.login_view, name='login_view'),
]