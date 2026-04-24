# accounts/serializers.py
from rest_framework import serializers
from .models import NAICSCode

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs   



class NAICSCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NAICSCode
        fields = ["id", "code", "title"]

from rest_framework import serializers
from .models import CapabilityProfile


class CapabilityProfileSerializer(serializers.ModelSerializer):
    naics_codes = NAICSCodeSerializer(many=True, read_only=True)
    naics_code_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=NAICSCode.objects.all(),
        source='naics_codes',
        write_only=True
    )

    class Meta:
        model = CapabilityProfile
        fields = "__all__"