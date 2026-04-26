from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('notifications/', views.notifications, name='notifications'),
    path('profile/', views.profile, name='profile'),
    path('api/profile/', views.get_capability_profile, name='get_capability_profile'),
    path('api/profile/extract/', views.extract_capability_profile, name='extract_capability_profile'),
    path('api/profile/save/', views.save_capability_profile, name='save_capability_profile'),
    path('api/opportunities/', views.OpportunityListView.as_view(), name='opportunity_list'),
    path('api/matched-contracts/', views.MatchedContractListView.as_view(), name='matched_contract_list'),
    path('api/matches/', views.MatchmakingCacheView.as_view(), name='matchmaking_cache'),
]
