# SaaS Preflight local user guide

## Install

Use CPython 3.12 (including 3.12.10). From the repository root:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

On Windows PowerShell, create and activate the environment with:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Run each command separately. Confirm `python --version` reports Python 3.12 before installation.

## Initialize a workspace

Run these commands from the directory whose Preflight configuration and evidence you want to own:

```bash
preflight init --non-interactive
preflight doctor --ci
```

Initialization creates `.preflight/core.yml` and `.preflight/reference.yml`. Review `core.yml`
before running. The current dashboard accepts only the `reference` profile and cannot contact or
claim verification of a customer or external provider.

## Start the dashboard

```bash
preflight dashboard
```

Open the exact URL printed by the command, normally `http://127.0.0.1:8765`. Keep the terminal open.
Press Ctrl+C in that terminal to stop the dashboard. To select another local port:

```bash
preflight dashboard --port 8877
```

The dashboard intentionally binds only to the local computer. Do not place it behind a proxy,
forward the port, or expose it to a LAN or the internet.

## Run and review verification

1. Select no suite to use the approved suites in `.preflight/core.yml`, or select an offered suite
   override.
2. Choose **Start verification** and wait for the run detail page.
3. Review the final decision, verification level, unverified scopes and scenario results.
4. Open the standalone HTML report for the full evidence view.
5. Return to **Runs** to see newest-first history.

Artifacts remain the source of truth under `.preflight/runs/<run-id>/`:

- `run.json` — validated machine-readable result;
- `preflight-report.html` — standalone evidence report;
- `journal.jsonl` — fixture lifecycle evidence.

## Decision meanings

- `PASS`: required assertions completed without a blocking defect.
- `WARN`: only accepted non-blocking findings occurred.
- `FAIL`: a required product assertion failed.
- `INCOMPLETE`: execution, required coverage or cleanup did not complete reliably.

A reference PASS proves the bundled reference behavior and engine. It does not prove an external
application. Use the CLI `preflight clean <run-id>` when an incomplete report supplies that recovery
instruction.

## Troubleshooting

- **Configuration unavailable:** run `preflight init`, then `preflight doctor --ci`, and correct the
  named validation error.
- **Port already in use:** restart with another port between 1024 and 65535.
- **Run busy:** wait for the active local run to finish; the dashboard prevents concurrent mutation.
- **Run/report not found:** use the Runs page. Invalid, corrupt or mismatched artifacts are not served.
- **Browser cannot connect:** confirm the terminal is still running and use its printed `127.0.0.1`
  URL rather than a remote hostname.
