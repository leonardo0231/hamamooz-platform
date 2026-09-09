from rest_framework import serializers


class ValidationIssueSerializer(serializers.Serializer):
    level = serializers.CharField()
    message = serializers.CharField()
    row = serializers.IntegerField(required=False, allow_null=True)
    column = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ImportSummarySerializer(serializers.Serializer):
    students = serializers.IntegerField(default=0)
    classes = serializers.ListField(child=serializers.CharField(), default=list)
    indicators = serializers.IntegerField(default=0)
    periods = serializers.IntegerField(default=0)


class PreviewResponseSerializer(serializers.Serializer):
    summary = ImportSummarySerializer()
    warnings = ValidationIssueSerializer(many=True)
    errors = ValidationIssueSerializer(many=True)
