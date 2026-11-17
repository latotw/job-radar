# Global Remote Job Radar

A local, evidence-based job discovery and application tracking tool for a candidate in Taiwan. It collects public job feeds, classifies Taiwan engagement eligibility separately from fit, ranks opportunities deterministically, and stores all data in SQLite. Applications, messages, and generated materials remain drafts for human review.

## Setup

Requires Python 3.11+. A project-local `.venv` is recommended:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

`config/profile.yaml` contains Summer's private candidate profile and is excluded from Git. On a fresh checkout, copy `config/profile.example.yaml` to `config/profile.yaml` and populate it with verified information; items marked `TODO` need manual confirmation. Database, logs, reports, environment files, and local profile files are excluded from Git.

## Use

```bash
jobradar search             # Fetch configured sources, classify, score, save, and report
jobradar search --offline   # Rebuild reports from saved data
streamlit run app/dashboard.py
pytest
```

Daily Markdown/HTML and CSV reports are written to `reports/`. The SQLite database is `data/jobs.db`. A `CONFIRMED` result means the posting contains worldwide or Taiwan-specific evidence and no explicit Taiwan exclusion was detected. It is not legal advice or a substitute for confirming payroll/entity arrangements with the employer.

## Sources and constraints

Himalayas, We Work Remotely, Remote OK, and configured Greenhouse, Lever, and Ashby public boards are supported. Company board identifiers are in `config/target_companies.yaml`; provider availability and individual board data can change. The defaults enable Greenhouse public boards for GitLab and Automattic. LinkedIn is provided only as a manual search link: this project does not scrape LinkedIn, automate logged-in browsing, or submit applications. Actually Remote and Alion are manual research links only.

## Scheduling (macOS)

`scripts/install_launchd.sh` installs and activates a LaunchAgent for a daily 23:00 run in the Mac's local time zone. Run `scripts/uninstall_launchd.sh` to unload and remove it. `scripts/run_daily.py` is the standalone scheduled entry point.

## Privacy and limitations

Candidate data stays local. The optional prompt package is generated locally; no LLM call is implemented. SMTP notification settings are examples only and email sending is not implemented. Salary conversion, live currency conversion, verified closure checks, historical change snapshots, and official employer cross-verification are not yet implemented. A failed source is logged and does not prevent other sources from running. Do not treat aggregator labels as employer confirmation; use the saved recruiter questions for uncertain listings.
