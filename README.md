# SaaS Preflight

Python implementation of the Version 1.5 Core Development Baseline.

The Version 1.5 Core Development Baseline is complete. The reference profile never contacts
external providers or claims external verification. A separate, explicitly named Supabase test
integration is verified. Stripe and cPanel deployment remain deferred. Automated accessibility
acceptance and the documented human NVDA/Chrome and Narrator/Edge protocol pass for the recorded,
hash-bound standalone report. This is not a third-party certification or a claim about later report
versions.

See `PROJECT_STATUS.md` for executed evidence, `docs/spec/` for authoritative requirements,
`docs/decisions/` for activated integration boundaries, and
`docs/validation/A11Y_WCAG_2_2_AA_MANUAL_PROTOCOL.md` for the formal accessibility release gate.

## Local dashboard quick start

With CPython 3.12 (including 3.12.10):

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install .
mkdir preflight-workspace && cd preflight-workspace
preflight init --non-interactive
preflight doctor --ci
preflight dashboard
```

Open the printed `http://127.0.0.1:<port>` URL. The dashboard is intentionally local-only and runs
reference verification; it must not be exposed through a public host or treated as customer-system
verification. See `docs/USER_GUIDE.md` for the complete workflow and troubleshooting.
