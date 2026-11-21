import json
import pytest

from acc_v8_qa.dashboard import (
    MAX_UPLOAD_BYTES,
    parse_campaign_upload,
)


def test_valid_campaign_upload():
    payload = {
        "campaign_id": "DEMO-001",
        "audience_count": 100,
        "historical_average": 100,
        "invalid_consent_count": 0,
        "suppressed_recipient_count": 0,
        "workflow_status": "Finished",
        "typology_active": True,
        "proof_approved": True,
        "delivery_status": "not_started",
        "subject": "Synthetic test",
    }
    assert parse_campaign_upload(
        json.dumps(payload).encode()
    )["campaign_id"] == "DEMO-001"


def test_invalid_json_rejected():
    with pytest.raises(ValueError):
        parse_campaign_upload(b"{bad json")


def test_non_object_json_rejected():
    with pytest.raises(ValueError):
        parse_campaign_upload(b'["not", "an", "object"]')


def test_oversized_upload_rejected():
    with pytest.raises(ValueError):
        parse_campaign_upload(b" " * (MAX_UPLOAD_BYTES + 1))


def test_unexpected_fields_rejected():
    with pytest.raises(ValueError):
        parse_campaign_upload(
            b'{"campaign_id":"DEMO","secret":"value"}'
        )


def test_boolean_not_accepted_as_integer():
    with pytest.raises(ValueError):
        parse_campaign_upload(
            b'{"audience_count":true}'
        )


def test_negative_count_rejected():
    with pytest.raises(ValueError):
        parse_campaign_upload(
            b'{"invalid_consent_count":-1}'
        )


def test_invalid_boolean_rejected():
    with pytest.raises(ValueError):
        parse_campaign_upload(
            b'{"typology_active":"yes"}'
        )


def test_non_utf8_rejected():
    with pytest.raises(ValueError):
        parse_campaign_upload(b"\xff\xfe")


def test_oversized_subject_rejected():
    payload = {"subject": "A" * 501}
    with pytest.raises(ValueError):
        parse_campaign_upload(json.dumps(payload).encode())
