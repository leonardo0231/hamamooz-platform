import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from hamamooz.apps.accounts.models import Role, RoleAssignment, User
from hamamooz.apps.activities.models import Activity, ActivityParticipation
from hamamooz.apps.behavior.models import BehaviorEvent, BehaviorEventType
from hamamooz.apps.behavior.services import transition_event


@pytest.mark.django_db
def test_behavior_events_api_lists_only_the_selected_school_scope(api_client, base_data):
    """A behavior event collection must be a scoped domain endpoint, not a global event feed."""
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        "/api/v1/behavior-events/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


@pytest.mark.django_db
def test_behavior_event_confirmation_persists_actor_and_timestamp(base_data):
    """A confirmed observation must carry server-side confirmation provenance."""
    event_type = BehaviorEventType.objects.create(
        organization=base_data["organization"],
        code="late-arrival",
        title="Late arrival",
        default_polarity=BehaviorEventType.Polarity.NEGATIVE,
        default_severity=BehaviorEventType.Severity.LOW,
    )
    event = BehaviorEvent.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        enrollment=base_data["enrollments"][0],
        event_type=event_type,
        polarity=BehaviorEvent.Polarity.NEGATIVE,
        severity=BehaviorEvent.Severity.LOW,
        occurred_at=timezone.now(),
        description="Late after break.",
        recorded_by=base_data["teacher1"],
    )

    confirmed = transition_event(
        event=event,
        target_status=BehaviorEvent.Status.CONFIRMED,
        actor=base_data["manager"],
    )

    assert confirmed.status == BehaviorEvent.Status.CONFIRMED
    assert confirmed.confirmed_by == base_data["manager"]
    assert confirmed.confirmed_at is not None


@pytest.mark.django_db
def test_behavior_event_rejects_skipping_from_draft_to_resolved(base_data):
    """The state machine must prevent a draft observation from becoming resolved directly."""
    event_type = BehaviorEventType.objects.create(
        organization=base_data["organization"],
        code="positive",
        title="Positive conduct",
        default_polarity=BehaviorEventType.Polarity.POSITIVE,
        default_severity=BehaviorEventType.Severity.LOW,
    )
    event = BehaviorEvent.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        enrollment=base_data["enrollments"][0],
        event_type=event_type,
        polarity=BehaviorEvent.Polarity.POSITIVE,
        severity=BehaviorEvent.Severity.LOW,
        occurred_at=timezone.now(),
        description="Observed positive behavior.",
        recorded_by=base_data["teacher1"],
    )

    with pytest.raises(ValidationError):
        transition_event(
            event=event,
            target_status=BehaviorEvent.Status.RESOLVED,
            actor=base_data["manager"],
        )

    event.refresh_from_db()
    assert event.status == BehaviorEvent.Status.DRAFT


@pytest.mark.django_db
def test_activities_api_lists_only_the_selected_school_scope(api_client, base_data):
    """Activities require their own scoped domain endpoint, rather than a generic event feed."""
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        "/api/v1/activities/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


@pytest.mark.django_db
def test_student_360_behavior_returns_confirmed_facts_without_event_description(
    api_client, base_data
):
    """The 360 projection exposes confirmed behavior evidence without a broad narrative payload."""
    event_type = BehaviorEventType.objects.create(
        organization=base_data["organization"],
        code="conduct",
        title="Conduct",
        default_polarity=BehaviorEventType.Polarity.NEGATIVE,
        default_severity=BehaviorEventType.Severity.MEDIUM,
    )
    event = BehaviorEvent.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        enrollment=base_data["enrollments"][0],
        event_type=event_type,
        polarity=BehaviorEvent.Polarity.NEGATIVE,
        severity=BehaviorEvent.Severity.MEDIUM,
        occurred_at=timezone.now(),
        description="Internal narrative must remain in the behavior domain endpoint.",
        recorded_by=base_data["teacher1"],
    )
    transition_event(
        event=event,
        target_status=BehaviorEvent.Status.CONFIRMED,
        actor=base_data["manager"],
    )
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        f"/api/v1/students/{event.enrollment.student_id}/360/behavior/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["events"] == [
        {
            "id": str(event.id),
            "event_type": "Conduct",
            "polarity": "negative",
            "severity": "medium",
            "status": "confirmed",
        }
    ]


@pytest.mark.django_db
def test_student_360_activities_returns_scoped_participation_facts(api_client, base_data):
    """The 360 activity tab must compose participation facts without a separate student model."""
    activity = Activity.objects.create(
        organization=base_data["organization"],
        school=base_data["school1"],
        academic_year=base_data["year"],
        title="School chess competition",
        kind=Activity.Kind.COMPETITION,
        starts_at=timezone.now(),
        status=Activity.Status.COMPLETED,
        created_by=base_data["manager"],
    )
    participation = ActivityParticipation.objects.create(
        activity=activity,
        enrollment=base_data["enrollments"][0],
        status=ActivityParticipation.Status.PARTICIPATED,
        participation_role="team member",
        placement=2,
    )
    api_client.force_authenticate(base_data["manager"])

    response = api_client.get(
        f"/api/v1/students/{participation.enrollment.student_id}/360/activities/",
        HTTP_X_SCHOOL_ID=str(base_data["school1"].id),
    )

    assert response.status_code == 200
    assert response.data["participations"] == [
        {
            "id": str(participation.id),
            "activity": "School chess competition",
            "kind": "competition",
            "status": "participated",
            "participation_role": "team member",
            "result": "",
            "placement": 2,
        }
    ]


@pytest.mark.django_db
def test_student_affairs_has_whole_school_behavior_activity_and_student_read_scope(
    api_client, base_data
):
    """This domain role is broad only for its defined student-facing domains."""

    deputy = User.objects.create_user(
        username="student-affairs",
        email="student-affairs@example.com",
        password="Strong-pass-123",
    )
    RoleAssignment.objects.create(
        user=deputy,
        organization=base_data["organization"],
        school=base_data["school1"],
        role=Role.STUDENT_AFFAIRS_DEPUTY,
    )
    event_type = BehaviorEventType.objects.create(
        organization=base_data["organization"],
        code="student-affairs-scope",
        title="Student affairs scope",
        default_polarity=BehaviorEventType.Polarity.NEGATIVE,
        default_severity=BehaviorEventType.Severity.LOW,
    )
    headers = {"HTTP_X_SCHOOL_ID": str(base_data["school1"].id)}
    api_client.force_authenticate(deputy)

    created_event = api_client.post(
        "/api/v1/behavior-events/",
        {
            "organization": str(base_data["organization"].id),
            "school": str(base_data["school1"].id),
            "academic_year": str(base_data["year"].id),
            "enrollment": str(base_data["enrollments"][0].id),
            "event_type": str(event_type.id),
            "polarity": BehaviorEvent.Polarity.NEGATIVE,
            "severity": BehaviorEvent.Severity.LOW,
            "occurred_at": timezone.now().isoformat(),
            "description": "Recorded by the student-affairs deputy.",
        },
        format="json",
        **headers,
    )
    assert created_event.status_code == 201
    assert api_client.get("/api/v1/behavior-events/", **headers).data["count"] == 1

    activity = api_client.post(
        "/api/v1/activities/",
        {
            "organization": str(base_data["organization"].id),
            "school": str(base_data["school1"].id),
            "academic_year": str(base_data["year"].id),
            "title": "Student affairs activity",
            "kind": Activity.Kind.CULTURAL,
            "starts_at": timezone.now().isoformat(),
        },
        format="json",
        **headers,
    )
    assert activity.status_code == 201
    participation = api_client.post(
        "/api/v1/activity-participations/",
        {"activity": activity.data["id"], "enrollment": str(base_data["enrollments"][0].id)},
        format="json",
        **headers,
    )
    assert participation.status_code == 201

    student = api_client.get(
        f"/api/v1/students/{base_data['enrollments'][0].student_id}/360/summary/", **headers
    )
    assert student.status_code == 200
    assert student.data["current_enrollment"]["id"] == str(base_data["enrollments"][0].id)
    assert (
        api_client.get(
            "/api/v1/behavior-events/", HTTP_X_SCHOOL_ID=str(base_data["school2"].id)
        ).status_code
        == 403
    )
