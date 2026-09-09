from rest_framework import serializers


class AssessmentPeriodSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField()
    period_type = serializers.CharField()
    academic_year = serializers.CharField(required=False, allow_blank=True)


class IndicatorSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField(required=False, allow_blank=True)
    weight = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)


class AssessmentRecordSerializer(serializers.Serializer):
    student = serializers.UUIDField()
    period = serializers.UUIDField()
    indicator = serializers.UUIDField()
    score = serializers.DecimalField(max_digits=6, decimal_places=2)
