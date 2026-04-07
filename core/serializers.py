from rest_framework import serializers

from .models import Opportunity


class OpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = ['id', 'title', 'description', 'naics_code', 'agency', 'status']
