"""Transparent reference oracle for smoke-testing the V0 QC runner."""

from typing import Any


def check_record(record: dict[str, Any]) -> list[dict[str, str]]:
    latitude, longitude = record.get("latitude"), record.get("longitude")
    if latitude in (None, "") or longitude in (None, ""):
        return []
    lat, lon = float(latitude), float(longitude)
    singapore = 1.13 <= lat <= 1.47 and 103.60 <= lon <= 104.05
    malaysia = 1.30 <= lat <= 2.50 and 102.00 <= lon <= 104.00
    if singapore or malaysia:
        return []
    return [{"flag_code": "outside_approximate_range", "reason": f"Coordinates ({lat}, {lon}) are outside the approximate documented range."}]
