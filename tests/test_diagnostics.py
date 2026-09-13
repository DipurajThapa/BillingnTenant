import pytest

from preflight.diagnostics import CORE_CODES, validate_code


def test_catalog_is_unique_and_owned() -> None:
    assert len(CORE_CODES) == 19
    assert all(
        code.split("_", 1)[0] in {"CFG", "CORE", "PORT", "SCN", "EVD", "CLN", "RPT"}
        for code in CORE_CODES
    )


def test_unknown_and_reserved_codes_are_rejected() -> None:
    with pytest.raises(ValueError):
        validate_code("STR_BAD_SIGNATURE")
    with pytest.raises(ValueError):
        validate_code("UNKNOWN")
