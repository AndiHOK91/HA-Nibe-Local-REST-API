"""Keep release metadata, README and changelog in sync."""

import json
import re
from pathlib import Path

_ROOT = Path(__file__).parents[1]
_MANIFEST = _ROOT / "custom_components" / "nibe_local" / "manifest.json"


def test_release_version_is_consistent() -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    version = manifest["version"]
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    current_version_line = f"Aktuelle Integrationsversion: **{version}**"
    assert readme.count(current_version_line) == 1
    assert f"## {version}" in changelog

    documented_release_versions = re.findall(
        r"\*\*v(\d+\.\d+\.\d+) ist ein regulärer Release\.\*\*",
        readme,
    )
    assert documented_release_versions
    assert set(documented_release_versions) == {version}
