from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup_api, name='signup_api'),
    path('signup-vis/', views.signup_view, name='signup_view'),
    path('login/', views.login_api, name='login_api'),
    path('login-vis/', views.login_view, name='login_view'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/accounts/login-vis/'), name='logout_view'),
    path('linked-emails/', views.linked_emails_api, name='linked_emails_api'),
    path('linked-emails/<int:email_id>/', views.linked_email_detail_api, name='linked_email_detail_api'),
]
