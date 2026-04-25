from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import PasswordResetRequestView, PasswordResetConfirmView, naics_list



urlpatterns = [
    path('signup/', views.signup_api, name='signup_api'),
    path('signup-vis/', views.signup_view, name='signup_view'),
    path('login/', views.login_api, name='login_api'),
    path('login-vis/', views.login_view, name='login_view'),
    path('reset-password-confirm/', PasswordResetConfirmView.as_view(), name='reset_password_confirm'),
    path("forgot-password/", PasswordResetRequestView.as_view(), name="forgot_password"),
    path('logout/', auth_views.LogoutView.as_view(next_page='/accounts/login-vis/'), name='logout_view'),
    path('linked-emails/', views.linked_emails_api, name='linked_emails_api'),
    path('linked-emails/<int:email_id>/', views.linked_email_detail_api, name='linked_email_detail_api'),
    path('mailbox-connections/', views.mailbox_connections_api, name='mailbox_connections_api'),
    path('mailbox-connections/sync/', views.mailbox_connections_sync_api, name='mailbox_connections_sync_api'),
    path('mailbox-connections/<int:connection_id>/sync/', views.mailbox_connection_sync_api, name='mailbox_connection_sync_api'),
    path('naics/', naics_list, name='naics-list'),
]
