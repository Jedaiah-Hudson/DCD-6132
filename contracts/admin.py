from django.contrib import admin
from .models import Contract, NAICSCode, ContractNote


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "agency", "deadline", "status")

from .models import Contract, ContractNote


@admin.register(ContractNote)
class ContractNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "contract", "user", "created_at")
    search_fields = ("title", "body")

@admin.register(NAICSCode)
class NAICSCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "broad_category")
    search_fields = ("code", "title", "broad_category")