"""Tests for request body building."""

from meraki_client import MerakiClient


def test_nullable_body_fields_send_null_only_when_given() -> None:
    """An explicit None on a nullable field is sent as null; an omitted field is left out."""
    client = MerakiClient(api_key="test")

    unassigned = client.batch.devices.update_device("Q234-ABCD-5678", floor_plan_id=None)
    untouched = client.batch.devices.update_device("Q234-ABCD-5678", lat=1.0)

    assert unassigned.body == {"floorPlanId": None}
    assert untouched.body == {"lat": 1.0}
