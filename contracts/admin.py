from django.contrib import admin
from .models import Contract, EmailIngestionMessage, NAICSCode, ContractNote, UserContractProgress


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "agency", "deadline", "status")


@admin.register(ContractNote)
class ContractNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "contract", "user", "created_at")
    search_fields = ("title", "body")

@admin.register(NAICSCode)
class NAICSCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "broad_category")
    search_fields = ("code", "title", "broad_category")

@admin.register(UserContractProgress)
class UserContractProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "contract", "contract_progress", "updated_at")


@admin.register(EmailIngestionMessage)
class EmailIngestionMessageAdmin(admin.ModelAdmin):
    list_display = ("mailbox_connection", "contract", "external_message_id", "was_candidate", "received_at")
    search_fields = ("external_message_id", "sender", "subject", "source_email")
