from pathlib import Path


def test_live_verifier_has_secret_and_cleanup_guardrails() -> None:
    script = Path("scripts/verify_supabase_live.py").read_text()
    workflow = Path(".github/workflows/supabase-live.yml").read_text()
    for name in (
        "SUPABASE_TEST_URL",
        "SUPABASE_TEST_PUBLISHABLE_KEY",
        "SUPABASE_TEST_ACTOR_A_EMAIL",
        "SUPABASE_TEST_ACTOR_A_PASSWORD",
        "SUPABASE_TEST_ACTOR_B_EMAIL",
        "SUPABASE_TEST_ACTOR_B_PASSWORD",
    ):
        assert name in script
        assert f"secrets.{name}" in workflow
    assert "follow_redirects=False" in script
    assert "trust_env=False" in script
    assert "preflight_delete_resource" in script
    assert 'print("SUPABASE_LIVE_VERIFICATION_PASS")' in script
