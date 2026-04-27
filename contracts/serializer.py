from rest_framework import serializers
from contracts.models import Contract, ContractNotification, UserContractProgress


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = "__all__"


class UserContractProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserContractProgress
        fields = [
            "id",
            "contract",
            "contract_progress",
            "workflow_status",
            "relationship_label",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "contract", "created_at", "updated_at"]


class ContractNotificationSerializer(serializers.ModelSerializer):
    contract_title = serializers.CharField(source="contract.title", read_only=True)
    contract_agency = serializers.CharField(source="contract.agency", read_only=True)

    class Meta:
        model = ContractNotification
        fields = [
            "id",
            "contract",
            "contract_title",
            "contract_agency",
            "notification_type",
            "severity",
            "title",
            "message",
            "due_at",
            "is_read",
            "created_at",
            "updated_at",
        ]
