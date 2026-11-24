"""Tests for response validation of real endpoint calls, with the HTTP layer mocked."""

from typing import Any

import httpx
import pytest

from meraki_client import MerakiClient
from meraki_client.exceptions import InvalidResponseError


def _client_returning(monkeypatch: pytest.MonkeyPatch, body: Any) -> MerakiClient:
    """Client whose HTTP requests all get a 200 response with the given JSON body."""
    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda _transport, _request: httpx.Response(200, json=body),
    )
    return MerakiClient(api_key="test")


def _ssid_status(*, serial: Any, bssid: Any, channel: Any) -> dict[str, Any]:
    return {
        "serial": serial,
        "name": "AP 1",
        "network": {"id": "N_1", "name": "Office"},
        "basicServiceSets": [
            {
                "bssid": bssid,
                "ssid": {"name": "Guest", "number": 1, "enabled": True, "advertised": True},
                "radio": {
                    "isBroadcasting": True,
                    "band": "5",
                    "channel": channel,
                    "channelWidth": 40,
                    "power": 12,
                    "index": "1",
                },
            }
        ],
    }


def test_ssid_statuses_accept_object_and_string_bssids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Some access points report bssid as an object instead of the documented string."""
    client = _client_returning(
        monkeypatch,
        {
            "items": [
                _ssid_status(
                    serial="Q2XX-AAAA-0001",
                    bssid={"mac_address": "aa:bb:cc:dd:ee:ff", "enabled": True},
                    channel=36,
                ),
                _ssid_status(serial="Q2XX-AAAA-0002", bssid="11:22:33:44:55:66", channel=40),
            ],
            "meta": {"counts": {"items": {"total": 2, "remaining": 0}}},
        },
    )

    statuses = client.wireless.get_organization_wireless_ssids_statuses_by_device("1").collect()

    assert [status.basic_service_sets[0].bssid for status in statuses] == [
        {"mac_address": "aa:bb:cc:dd:ee:ff", "enabled": True},
        "11:22:33:44:55:66",
    ]


@pytest.mark.parametrize("invalid_item_count", [1, 3])
def test_invalid_response_message_lists_each_distinct_failure_once(
    monkeypatch: pytest.MonkeyPatch, invalid_item_count: int
) -> None:
    """The message is the same for any number of failing items and contains no input values."""
    client = _client_returning(
        monkeypatch,
        {
            "items": [
                _ssid_status(
                    serial=["Q2XX-SECRET-0001"],
                    bssid="11:22:33:44:55:66",
                    channel={"primary": 36},
                )
                for _ in range(invalid_item_count)
            ]
        },
    )

    with pytest.raises(InvalidResponseError) as exc_info:
        client.wireless.get_organization_wireless_ssids_statuses_by_device("1").collect()

    assert str(exc_info.value) == (
        "InvalidResponseError: Response validation failed for "
        "getOrganizationWirelessSsidsStatusesByDevice: "
        "items.*.basicServiceSets.*.radio.channel: int_type (got dict); "
        "items.*.serial: string_type (got list)"
    )


def test_invalid_response_message_names_root_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """A response of the wrong shape as a whole is reported at `<root>`, not an empty path."""
    client = _client_returning(monkeypatch, ["unexpected"])

    with pytest.raises(InvalidResponseError) as exc_info:
        client.networks.get_network_pii_sm_devices_for_key("N_1")

    assert str(exc_info.value) == (
        "InvalidResponseError: Response validation failed for getNetworkPiiSmDevicesForKey: "
        "<root>: dict_type (got list)"
    )
