from rest_framework import serializers
from contracts.models import Contract, UserContractProgress


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
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "contract", "created_at", "updated_at"]
