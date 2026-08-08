from rest_framework import serializers


class DashboardTermSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()


class DashboardCountsSerializer(serializers.Serializer):
    students = serializers.IntegerField(min_value=0)
    classes = serializers.IntegerField(min_value=0)
    teachers = serializers.IntegerField(min_value=0)
    missing_scores = serializers.IntegerField(min_value=0)


class DashboardSchoolStudentsSerializer(serializers.Serializer):
    school_name = serializers.CharField()
    organization_name = serializers.CharField()
    students = serializers.IntegerField(min_value=0)


class DashboardClassAverageSerializer(serializers.Serializer):
    enrollment__class_section_id = serializers.UUIDField()
    enrollment__class_section__title = serializers.CharField()
    average = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    students = serializers.IntegerField(min_value=0)


class DashboardActivitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action = serializers.CharField()
    entity_type = serializers.CharField()
    entity_id = serializers.CharField(allow_blank=True)
    actor_id = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField()


class DashboardQuickLinksSerializer(serializers.Serializer):
    score_entry = serializers.CharField()
    report_cards = serializers.CharField()
    imports = serializers.CharField()


class DashboardSummarySerializer(serializers.Serializer):
    selected_term = DashboardTermSerializer()
    counts = DashboardCountsSerializer()
    students_by_school = DashboardSchoolStudentsSerializer(many=True)
    class_averages = DashboardClassAverageSerializer(many=True)
    assessment_workflow = serializers.DictField(child=serializers.IntegerField(min_value=0))
    latest_activities = DashboardActivitySerializer(many=True)
    quick_links = DashboardQuickLinksSerializer()
