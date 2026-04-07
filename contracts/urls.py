from django.urls import path
from .view import contract_list

urlpatterns = [
    path("api/contracts/", contract_list, name="contract-list"),
]