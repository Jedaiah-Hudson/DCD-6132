from rest_framework import serializers


class OpportunitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    naics_code = serializers.CharField(allow_blank=True)
    naics_category = serializers.CharField(allow_blank=True, required=False)
    agency = serializers.CharField(allow_blank=True)
    status = serializers.CharField(allow_blank=True)
    partner = serializers.CharField(allow_blank=True, required=False)
    source = serializers.CharField(allow_blank=True, required=False)
    deadline = serializers.DateTimeField(allow_null=True, required=False)
    hyperlink = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    updated_at = serializers.DateTimeField(allow_null=True, required=False)
    contract_progress = serializers.CharField(allow_blank=True, required=False)
    workflow_status = serializers.CharField(allow_blank=True, required=False)

    relationship_label = serializers.CharField(allow_blank=True, required=False)

    match_score = serializers.IntegerField(required=False)
    match_reasons = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    matched_reasons = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    match_percentage = serializers.IntegerField(required=False)
    strongest_alignment = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    weak_alignment = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    match_breakdown = serializers.DictField(
        child=serializers.IntegerField(),
        required=False,
    )
