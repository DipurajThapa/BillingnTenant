"""Owned, non-sensitive diagnostic catalog."""

CORE_CODES = frozenset(
    {
        "CFG_INVALID",
        "CFG_UNKNOWN_FIELD",
        "CFG_REFERENCE_INVALID",
        "CFG_UNSUPPORTED_SCHEMA",
        "CORE_EXTERNAL_NOT_ENABLED",
        "CORE_INTERRUPTED",
        "PORT_MISSING",
        "PORT_INVALID_RETURN",
        "PORT_WRONG_RUN",
        "PORT_PRIVILEGED_AUTH",
        "SCN_DEPENDENCY_ERROR",
        "SCN_UNEXPECTED",
        "EVD_FIELD_REJECTED",
        "EVD_SENSITIVE_VALUE",
        "CLN_JOURNAL_INVALID",
        "CLN_PARTIAL",
        "CLN_FAILED",
        "RPT_SCHEMA_INVALID",
        "RPT_RENDER_FAILED",
    }
)
RESERVED_PREFIXES = ("STR_", "SUP_", "HTTP_", "GHA_", "A11Y_", "CPANEL_")


def validate_code(code: str) -> str:
    if code not in CORE_CODES or code.startswith(RESERVED_PREFIXES):
        raise ValueError("unknown or reserved diagnostic code")
    return code
