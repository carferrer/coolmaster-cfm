"""Translations and public registry keys must survive the update."""

import json
from pathlib import Path

from custom_components.coolmaster.button import BUTTONS

COMPONENT = Path(__file__).parents[1] / "custom_components" / "coolmaster"


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, f"Duplicate JSON key: {key}"
        result[key] = value
    return result


def test_translations_have_no_duplicate_keys_or_unresolved_core_references():
    for path in [
        COMPONENT / "strings.json",
        *sorted((COMPONENT / "translations").glob("*.json")),
    ]:
        content = path.read_text(encoding="utf-8")
        strings = json.loads(content, object_pairs_hook=unique_keys)
        assert "[%key:" not in content
        assert set(strings["entity"]["binary_sensor"]) == {"clean_filter", "demand"}
        assert set(strings["entity"]["button"]) == {button.key for button in BUTTONS}


def test_legacy_domain_and_version():
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["domain"] == "coolmaster"
    assert manifest["version"] == "1.1.1"
    assert manifest["integration_type"] == "hub"
    assert manifest["requirements"] == []
