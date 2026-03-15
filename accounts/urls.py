from django.urls import path
from . import views
from .views import PasswordResetRequestView, PasswordResetConfirmView


urlpatterns = [
    path('signup/', views.signup_api, name='signup_api'),
    path('signup-vis/', views.signup_view, name='signup_view'),
    path('login/', views.login_api, name='login_api'),
    path('login-vis/', views.login_view, name='login_view'),
    path('reset-password-confirm/', PasswordResetConfirmView.as_view(), name='reset_password_confirm'),
    path("forgot-password/", PasswordResetRequestView.as_view(), name="forgot_password"),
]