---
phase: 01-core-pipeline
plan: "04"
subsystem: email
tags: [jinja2, premailer, gmail, smtp, html-email]

# Dependency graph
requires:
  - phase: 01-01
    provides: SummarizedArticle dataclass with source_category, summary, why_it_matters, summarization_failed fields
provides:
  - Jinja2 table-based HTML email template (templates/digest.html.j2) with section headers per source_category
  - render_email() function that groups articles by SECTION_ORDER and inlines CSS via premailer
  - send_email() function that delivers via Gmail SMTP_SSL on port 465 with self-send
  - build_subject() that produces "AI Briefing — {date}" with em dash and current date
affects:
  - 01-05 (orchestrator wires render_email + send_email together)
  - Phase 2 (all sources feed into render_email via SummarizedArticle)

# Tech tracking
tech-stack:
  added: [jinja2, premailer]
  patterns:
    - Table-based email layout (no Flexbox/Grid) for Gmail compatibility
    - premailer.transform() for CSS inlining — converts <style> block to inline style= attributes
    - SMTP_SSL port 465 (not STARTTLS/587) for simpler Gmail auth
    - Credentials read at call time from os.environ (not at import) for testability

key-files:
  created:
    - templates/digest.html.j2
    - pipeline/render.py
    - pipeline/send.py
  modified: []

key-decisions:
  - "SMTP_SSL port 465 over STARTTLS/587 — simpler, no explicit starttls() call, sufficient for Gmail App Password"
  - "Credentials (GMAIL_USER, GMAIL_APP_PASSWORD) read at send_email() call time, not module import — allows import without env vars set"
  - "SECTION_ORDER constant in render.py controls email section sequence (Personal Blogs, WSJ, The Information, Anthropic)"

patterns-established:
  - "Email sections: articles grouped by source_category then filtered to non-empty before render"
  - "SMTP errors: catch SMTPAuthenticationError and SMTPException separately, log [ERROR], raise SystemExit(1)"
  - "Email body: text/plain attached before text/html (email clients prefer last MIME part)"

requirements-completed: [EMAIL-03, DEL-01, DEL-02, DEL-03, DEL-04]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 1 Plan 04: Email Rendering and Gmail Delivery Summary

**Jinja2 table-based email template with premailer CSS inlining and Gmail SMTP_SSL delivery via App Password self-send**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T18:48:29Z
- **Completed:** 2026-03-01T18:50:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Jinja2 HTML template (digest.html.j2) with table-based layout, section headers per source_category, per-article cards showing title, meta, summary, and why_it_matters, plus fallback for summarization_failed
- render_email() groups articles by SECTION_ORDER, suppresses empty sections, inlines CSS via premailer.transform(), and returns (html_body, text_body) tuple
- send_email() delivers via smtplib.SMTP_SSL port 465 with GMAIL_USER as both From and To (self-send), catches SMTP errors and raises SystemExit(1)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create templates/digest.html.j2 and pipeline/render.py** - `80013c9` (feat)
2. **Task 2: Create pipeline/send.py — Gmail SMTP delivery** - `9059aac` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `templates/digest.html.j2` - Table-based Jinja2 email template; iterates sections dict for section headers and article cards
- `pipeline/render.py` - render_email() groups by SECTION_ORDER, removes empty sections, renders template, runs premailer.transform(), builds plain-text fallback
- `pipeline/send.py` - send_email() via SMTP_SSL port 465 with error handling; build_subject() returns "AI Briefing — {date}" with em dash

## Decisions Made
- SMTP_SSL port 465 over STARTTLS/587: simpler implementation, no explicit starttls() call needed for Gmail App Password auth
- Credentials read at call time from os.environ (not at module import): allows importing pipeline/send.py in tests without GMAIL_USER set
- SECTION_ORDER list in render.py: makes section display order explicit and easy to update

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

**External services require manual configuration.** Gmail App Password must be configured before send_email() can deliver:

- `GMAIL_USER` — Your Gmail address (e.g. you@gmail.com)
- `GMAIL_APP_PASSWORD` — Google Account -> Security -> 2-Step Verification -> App passwords -> Generate for 'Mail'

Dashboard steps:
1. Enable 2-Step Verification at myaccount.google.com/security
2. Generate App Password for 'Mail' at myaccount.google.com/apppasswords

Verification: `GMAIL_USER=you@gmail.com GMAIL_APP_PASSWORD=xxxx python3 -c "from pipeline.send import build_subject; print(build_subject())"`

## Next Phase Readiness
- render_email() and send_email() are ready for the orchestrator (01-05) to wire together
- All three output-layer files (template + render + send) exist and import cleanly
- No Gmail credentials needed in CI until orchestrator runs end-to-end (Phase 1 plan 05)

---
*Phase: 01-core-pipeline*
*Completed: 2026-03-01*

## Self-Check: PASSED

- FOUND: templates/digest.html.j2
- FOUND: pipeline/render.py
- FOUND: pipeline/send.py
- FOUND: 01-04-SUMMARY.md
- FOUND commit: 80013c9 (Task 1 - template + renderer)
- FOUND commit: 9059aac (Task 2 - SMTP sender)
