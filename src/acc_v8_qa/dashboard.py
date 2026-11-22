import json

MAX_UPLOAD_BYTES = 256 * 1024

ALLOWED_FIELDS = {
    "campaign_id",
    "audience_count",
    "historical_average",
    "invalid_consent_count",
    "consent_evidence_ref",
    "legal_basis_evidence_ref",
    "suppressed_recipient_count",
    "workflow_status",
    "typology_active",
    "proof_approved",
    "delivery_status",
    "subject",
}

INTEGER_FIELDS = {
    "audience_count",
    "historical_average",
    "invalid_consent_count",
    "suppressed_recipient_count",
}

STRING_FIELDS = {
    "campaign_id",
    "consent_evidence_ref",
    "legal_basis_evidence_ref",
    "workflow_status",
    "delivery_status",
    "subject",
}

BOOLEAN_FIELDS = {
    "typology_active",
    "proof_approved",
}


def parse_campaign_upload(raw: bytes) -> dict:
    if not isinstance(raw, bytes):
        raise ValueError("Upload must contain JSON bytes.")

    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 256 KB upload limit.")

    try:
        campaign = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Invalid UTF-8 JSON file.") from None

    if not isinstance(campaign, dict):
        raise ValueError("Campaign input must be a JSON object.")

    unexpected = set(campaign) - ALLOWED_FIELDS
    if unexpected:
        raise ValueError(
            "Unexpected fields detected: " + ", ".join(sorted(unexpected))
        )

    for field in INTEGER_FIELDS:
        if field in campaign:
            value = campaign[field]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{field} must be an integer.")
            if value < 0:
                raise ValueError(f"{field} cannot be negative.")

    for field in STRING_FIELDS:
        if field in campaign:
            value = campaign[field]
            if not isinstance(value, str):
                raise ValueError(f"{field} must be text.")
            if len(value) > 500:
                raise ValueError(f"{field} exceeds 500 characters.")

    for field in BOOLEAN_FIELDS:
        if field in campaign and type(campaign[field]) is not bool:
            raise ValueError(f"{field} must be true or false.")

    return campaign
