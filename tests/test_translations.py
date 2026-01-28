"""Test translation files are in sync."""

import json
from pathlib import Path


def get_nested_keys(d, prefix=""):
    """Recursively get all keys from nested dict."""
    keys = set()
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(get_nested_keys(value, full_key))
    return keys


def test_translation_files_in_sync():
    """Test that strings.json and translation files have matching keys."""
    base_path = Path(__file__).parent.parent / "custom_components" / "signal_gateway"

    strings_file = base_path / "strings.json"
    en_file = base_path / "translations" / "en.json"
    fr_file = base_path / "translations" / "fr.json"

    with open(strings_file) as f:
        strings = json.load(f)

    with open(en_file) as f:
        en = json.load(f)

    with open(fr_file) as f:
        fr = json.load(f)

    strings_keys = get_nested_keys(strings)
    en_keys = get_nested_keys(en)
    fr_keys = get_nested_keys(fr)

    # strings.json and en.json should have same keys
    strings_missing = en_keys - strings_keys
    strings_extra = strings_keys - en_keys

    assert not strings_missing, f"strings.json missing keys: {strings_missing}"
    assert not strings_extra, f"strings.json has extra keys: {strings_extra}"

    # en.json and fr.json should have same keys
    fr_missing = en_keys - fr_keys
    fr_extra = fr_keys - en_keys

    assert not fr_missing, f"fr.json missing keys: {fr_missing}"
    assert not fr_extra, f"fr.json has extra keys: {fr_extra}"
