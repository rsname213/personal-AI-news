# Phase 3: Automation - Research

**Researched:** 2026-03-01
**Domain:** GitHub Actions — scheduled workflow, state persistence, keepalive, secrets
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Full pipeline runs automatically via GitHub Actions on a daily cron at 12:00 UTC (7am EST / 8am EDT) | Cron trigger YAML verified from official GitHub docs |
| INFRA-02 | Pipeline can be triggered manually via `workflow_dispatch` for testing without waiting for cron | workflow_dispatch YAML verified from official GitHub docs |
| INFRA-03 | GitHub Actions workflow includes a 30-minute timeout to prevent runaway jobs | `timeout-minutes: 30` at job level — syntax verified |
| INFRA-04 | A GitHub Actions keepalive workflow prevents the cron from being disabled after 60 days of repo inactivity | `gautamkrishnar/keepalive-workflow@v2` — syntax and permissions verified |
| INFRA-05 | All secrets (GMAIL_USER, GMAIL_APP_PASSWORD, ANTHROPIC_API_KEY) are stored as GitHub Secrets; RSS URLs stored as environment variables — nothing hardcoded | Secrets-to-env mapping pattern verified from official GitHub docs |
</phase_requirements>

---

## Summary

This phase wires the already-working Python pipeline (`orchestrator.py`) into automated daily execution via GitHub Actions. The core work is two YAML files: a main newsletter workflow and a keepalive workflow. No Python code changes are needed — `orchestrator.py` already handles `python-dotenv` with a graceful no-op when env vars are injected by Actions.

The most non-obvious decision in this phase is how to persist `.seen_urls` (the deduplication state file) between daily runs. GitHub Actions provides no native persistent storage. The three options — git commit back, Actions cache, and artifacts — each have tradeoffs. **Git commit back is the correct choice for this project**: it is reliable, permanent, human-readable, aligns with the existing design decision ("stateless per-run is sufficient; deduplication via URL hash file"), and survives the 7-day cache expiry that would cripple the cache-based approach. The `stefanzweifel/git-auto-commit-action@v7` action makes this a 3-line addition to the workflow.

The keepalive problem is well-solved by `gautamkrishnar/keepalive-workflow@v2`, which uses the GitHub API (not dummy commits) to keep the repo active. It requires only `permissions: actions: write` and runs on a separate daily cron so it cannot interfere with the newsletter job. Python dependency caching uses `actions/setup-python@v5` with `cache: 'pip'` — a single line that replaces the manual cache configuration pattern and is the current recommended approach.

**Primary recommendation:** Two workflow files — `.github/workflows/newsletter.yml` (main job) and `.github/workflows/keepalive.yml` (separate keepalive job) — plus `permissions: contents: write` on the main workflow for the git commit-back of `.seen_urls`.

---

## Standard Stack

### Core (GitHub Actions built-ins)

| Action | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `actions/checkout` | `v4` | Check out repo code on runner | Required first step; v4 is current stable |
| `actions/setup-python` | `v5` | Install Python 3.12 + pip cache | Official Python setup; v5 is current stable |

### Supporting (Marketplace)

| Action | Version | Purpose | When to Use |
|--------|---------|---------|-------------|
| `stefanzweifel/git-auto-commit-action` | `v7` | Commit `.seen_urls` back to repo after each run | Needed to persist deduplication state between runs |
| `gautamkrishnar/keepalive-workflow` | `v2` | Prevent 60-day inactivity from disabling cron | Required for repos that go quiet after setup |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| git commit-back for `.seen_urls` | `actions/cache` | Cache expires after 7 days of inactivity — a holiday week would wipe state. Fatal for deduplication. |
| git commit-back for `.seen_urls` | Upload/download artifact | Requires knowing previous run ID to download; circular dependency. No built-in restore. |
| `keepalive-workflow@v2` | Manual monthly dummy commit | Requires human intervention; defeats the "zero manual effort" goal |
| `setup-python@v5 cache: 'pip'` | Manual `actions/cache` step | More verbose, same outcome; setup-python built-in cache is current recommended pattern |

**No installation needed** — this phase is pure YAML. Python deps already exist in `requirements.txt`.

---

## Architecture Patterns

### Recommended File Structure

```
.github/
└── workflows/
    ├── newsletter.yml      # Main job: cron + dispatch, runs orchestrator.py
    └── keepalive.yml       # Separate job: daily cron, keeps repo active
```

### Pattern 1: Main Newsletter Workflow

**What:** Triggered by `schedule` (daily 12:00 UTC) and `workflow_dispatch` (manual). Checks out code, sets up Python with pip cache, installs deps, runs orchestrator.py with secrets mapped to env, then commits `.seen_urls` back.

**When to use:** This is the only shape the main workflow should take.

**Example:**
```yaml
# Source: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule
name: AI Newsletter

on:
  schedule:
    - cron: '0 12 * * *'   # 12:00 UTC = 7am EST (winter) / 8am EDT (summer)
  workflow_dispatch:         # Manual trigger via Actions tab or gh CLI

permissions:
  contents: write            # Required for git-auto-commit-action to push .seen_urls

jobs:
  send-newsletter:
    runs-on: ubuntu-latest
    timeout-minutes: 30      # Kills runaway jobs (30 min = hard ceiling per INFRA-03)

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'       # Caches ~/.cache/pip keyed to requirements.txt hash

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run newsletter pipeline
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          WSJ_RSS_URL: https://feeds.a.wsj.com/rss/RSSWSJD.xml
          THE_INFO_RSS_URL: https://www.theinformation.com/feed
        run: python orchestrator.py

      - name: Commit updated .seen_urls
        uses: stefanzweifel/git-auto-commit-action@v7
        with:
          commit_message: 'chore: update seen URLs [skip ci]'
          file_pattern: '.seen_urls'
```

**Key notes:**
- `[skip ci]` in the commit message prevents the commit from triggering another workflow run (standard convention; GitHub also respects this natively for the default token)
- `file_pattern: '.seen_urls'` restricts what gets committed — never accidentally commits `.env` or other files
- `permissions: contents: write` is set at the workflow level; it applies to the `GITHUB_TOKEN` used by `git-auto-commit-action`
- `workflow_dispatch` with no `inputs:` block is valid — it adds a manual trigger button with no parameters

### Pattern 2: Keepalive Workflow

**What:** A separate workflow that runs on its own daily cron and uses the GitHub API (not a dummy commit) to signal activity. Prevents the main newsletter cron from being disabled after 60 days.

**When to use:** Always — this repo will go quiet once the pipeline is working.

**Example:**
```yaml
# Source: https://github.com/marketplace/actions/keepalive-workflow
name: Keepalive

on:
  schedule:
    - cron: '0 13 * * *'   # 13:00 UTC, 1 hour after newsletter — avoids peak-load collision
  workflow_dispatch:

permissions:
  actions: write             # Required for API-based keepalive (v2 default mode)

jobs:
  keepalive:
    name: Keepalive Workflow
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gautamkrishnar/keepalive-workflow@v2
        with:
          time_elapsed: 45  # Trigger keepalive when last commit is 45+ days old
```

**Key notes:**
- `v2` uses the GitHub API by default (no dummy commits) — `permissions: actions: write` is sufficient
- `time_elapsed: 45` triggers 15 days before the 60-day GitHub limit — provides buffer
- Run it at 13:00 UTC, 1 hour after the main job, to avoid peak-hour scheduling conflicts

### Pattern 3: Mapping Secrets to Environment Variables

**What:** GitHub Secrets are accessed via `${{ secrets.SECRET_NAME }}` in the `env:` block of a step.

**Example:**
```yaml
# Source: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions
- name: Run script
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GMAIL_USER: ${{ secrets.GMAIL_USER }}
    GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
  run: python orchestrator.py
```

**How it works in `orchestrator.py`:** The script uses `python-dotenv` with a `try/except ImportError` — when env vars are already set by Actions, `load_dotenv()` is called but silently does nothing (`.env` file is not present on the runner). The `_check_env()` pre-flight reads from `os.environ` which is already populated. No code changes needed.

**Why not job-level `env:`:** Putting secrets in the job-level `env:` block exposes them to all steps, including third-party actions. Step-level `env:` limits exposure to only the `run: python orchestrator.py` step.

### Anti-Patterns to Avoid

- **Scheduling at the top of the hour (`0 * * * *`):** GitHub Actions peak load hits every hour at `:00`. Schedule at `:12` or use a non-round offset.
  - **Exception:** `0 12 * * *` is explicitly approved in the project requirements and is a reasonable tradeoff.
- **Using `actions/cache` for `.seen_urls`:** Cache entries expire after 7 days of inactivity. A holiday week silently wipes deduplication state. Use git commit-back instead.
- **Committing `.seen_urls` without `[skip ci]`:** Without skip-ci, the commit triggers another workflow run, which runs `orchestrator.py` again, which sends a second email. Always include `[skip ci]` in the commit message.
- **Global `permissions: contents: write`:** Only the `git-auto-commit-action` step needs write access. Use workflow-level `permissions: contents: write` rather than granting it to third-party steps via `with: token`.
- **Hardcoding RSS URLs in Python:** Per INFRA-05, RSS URLs must be env vars. Both `WSJ_RSS_URL` and `THE_INFO_RSS_URL` belong in the workflow `env:` block, not in source code.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Commit `.seen_urls` back to repo | Custom `git config && git add && git push` bash block | `stefanzweifel/git-auto-commit-action@v7` | Handles dirty-check (no-op when no changes), git user config, branch detection, error handling, and `[skip ci]` correctly |
| Keep repo active | Separate "activity commit" workflow with content generation | `gautamkrishnar/keepalive-workflow@v2` | Handles idempotency, uses API not commits, has configurable `time_elapsed` threshold |
| Python pip caching | Manual `actions/cache` step with cache key templating | `actions/setup-python@v5` with `cache: 'pip'` | Built-in, automatically keys on `requirements.txt` hash, matches GitHub's documented recommendation |

**Key insight:** The git commit-back and keepalive patterns each have subtle correctness requirements (skip-ci, dirty-check, API vs commit mode) that the marketplace actions already handle. Using raw shell is solving a solved problem.

---

## Common Pitfalls

### Pitfall 1: `.seen_urls` Commit Triggers Infinite Re-Run

**What goes wrong:** The git commit-back step pushes a commit to the default branch. If the newsletter workflow has a `push:` trigger (or if `workflow_dispatch` is mis-configured), the commit triggers a new run, which sends a second email, which commits again.

**Why it happens:** GitHub Actions default token commits DO re-trigger workflow runs under some conditions. The `[skip ci]` convention and the `stefanzweifel/git-auto-commit-action` default behavior both guard against this, but only if the workflow does not add a `push:` trigger.

**How to avoid:** Never add `push:` to the newsletter workflow's `on:` block. Use only `schedule:` and `workflow_dispatch:`. The `[skip ci]` commit message is a belt-and-suspenders measure.

**Warning signs:** Two emails received on the same morning; Actions tab shows two runs started within seconds of each other.

### Pitfall 2: 60-Day Inactivity Silently Kills Cron

**What goes wrong:** Once the pipeline is stable, the repo has no commit activity. After 60 days, GitHub automatically disables scheduled workflows. The newsletter stops arriving. No notification is sent.

**Why it happens:** GitHub's documented policy: "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." (Source: GitHub official docs — HIGH confidence)

**How to avoid:** The `keepalive.yml` workflow covers this. The `time_elapsed: 45` parameter triggers keepalive 15 days before the limit.

**Warning signs:** Actions tab shows no runs for 24+ hours; GitHub shows banner "This scheduled workflow is disabled because there hasn't been activity in this repository for at least 60 days."

### Pitfall 3: GitHub Actions Cron Is Not On-Time

**What goes wrong:** The cron fires up to 60 minutes late during peak GitHub load periods. `0 12 * * *` may run at 12:47 UTC.

**Why it happens:** GitHub official docs state: "The `schedule` event can be delayed during periods of high loads of GitHub Actions workflow runs. High load times include the start of every hour."

**How to avoid:** The 25-hour recency window in `filter_articles()` already absorbs this delay (per decision [01-03] in STATE.md). No additional mitigation needed.

**Warning signs:** Article timestamp filtering removes articles from the previous evening because the cron fired at 12:58 instead of 12:00.

### Pitfall 4: GITHUB_TOKEN Default Permissions Block `.seen_urls` Push

**What goes wrong:** The `git-auto-commit-action` step silently fails to push because the `GITHUB_TOKEN` has only `contents: read` by default (the restricted default for new repos or repos configured with "Read repository contents and packages permissions").

**Why it happens:** GitHub's default workflow permissions can be set to "Read repository contents" at the org or repo level. New personal repos may have restrictive defaults.

**How to avoid:** Declare `permissions: contents: write` explicitly at the workflow level. This overrides any repo-default setting and is always explicit.

**Warning signs:** `git-auto-commit-action` step shows "Nothing to commit" even though `.seen_urls` was modified; or the step fails with a 403 on `git push`.

### Pitfall 5: Secrets Not Set Before First Manual Run

**What goes wrong:** The workflow YAML is committed but the GitHub Secrets (GMAIL_USER, GMAIL_APP_PASSWORD, ANTHROPIC_API_KEY) are not yet configured. `workflow_dispatch` is triggered for testing and `orchestrator.py` exits with `[ERROR] Missing required environment variables`.

**Why it happens:** Secrets must be configured in the GitHub repository settings UI before the workflow can use them. The YAML commit doesn't trigger this.

**How to avoid:** In the plan, make "Configure GitHub Secrets" a prerequisite task before any trigger test. Document the three secret names and where to find each value.

**Warning signs:** Workflow fails at `python orchestrator.py` with missing env var error rather than at the network/API stage.

---

## Code Examples

Verified patterns from official sources:

### Complete Main Newsletter Workflow

```yaml
# .github/workflows/newsletter.yml
# Source: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule
# Source: https://github.com/marketplace/actions/setup-python (setup-python@v5 cache: pip)
# Source: https://github.com/marketplace/actions/git-auto-commit (git-auto-commit-action@v7)

name: AI Newsletter

on:
  schedule:
    - cron: '0 12 * * *'
    # 12:00 UTC = 7am EST (Nov–Mar) / 8am EDT (Mar–Nov). ET offset varies seasonally.
    # GitHub Actions cron runs in UTC only — no timezone parameter exists.
  workflow_dispatch:
    # Adds a manual "Run workflow" button in the Actions tab. No inputs required.

permissions:
  contents: write  # Required for git-auto-commit-action to push .seen_urls

jobs:
  send-newsletter:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
          # Automatically caches ~/.cache/pip, keyed to requirements.txt hash.
          # Cache is restored at start of job, saved at end.

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run newsletter pipeline
        env:
          # Secrets mapped to env vars — orchestrator.py reads via os.environ
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          # RSS URLs stored as env vars per INFRA-05 (not hardcoded in Python)
          WSJ_RSS_URL: https://feeds.a.wsj.com/rss/RSSWSJD.xml
          THE_INFO_RSS_URL: https://www.theinformation.com/feed
        run: python orchestrator.py

      - name: Commit updated .seen_urls
        uses: stefanzweifel/git-auto-commit-action@v7
        with:
          commit_message: 'chore: update seen URLs [skip ci]'
          file_pattern: '.seen_urls'
          # [skip ci] prevents this commit from triggering another workflow run.
          # file_pattern restricts commits to only .seen_urls — never .env or other files.
          # Action is a no-op if .seen_urls has not changed (e.g. 0 new articles).
```

### Complete Keepalive Workflow

```yaml
# .github/workflows/keepalive.yml
# Source: https://github.com/marketplace/actions/keepalive-workflow

name: Keepalive

on:
  schedule:
    - cron: '0 13 * * *'
    # 13:00 UTC — 1 hour after newsletter job, avoids peak-load overlap
  workflow_dispatch:

permissions:
  actions: write
  # v2 uses GitHub API to signal activity (no dummy commits).
  # Only needs actions: write, not contents: write.

jobs:
  keepalive:
    name: Keepalive Workflow
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gautamkrishnar/keepalive-workflow@v2
        with:
          time_elapsed: 45
          # Trigger when last commit is 45+ days old.
          # GitHub disables cron after 60 days — this gives a 15-day buffer.
```

### Secrets Configuration (GitHub UI — not YAML)

Three secrets required in GitHub repo Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Where to Get It |
|-------------|----------------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |
| `GMAIL_USER` | Your Gmail address (e.g. `rsname213@gmail.com`) |
| `GMAIL_APP_PASSWORD` | Google Account → Security → 2-Step Verification → App Passwords |

The `.env` file values in the repo are the source of truth for what to paste. The secret names must match exactly — the workflow's `${{ secrets.GMAIL_USER }}` is case-sensitive.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `actions/checkout@v2` | `actions/checkout@v4` | 2023 | v2 deprecated; v4 is current |
| `actions/setup-python@v3` with manual `actions/cache` | `actions/setup-python@v5` with `cache: 'pip'` | 2023 | Built-in cache is simpler and officially recommended |
| `keepalive-workflow@v1` (dummy commits) | `keepalive-workflow@v2` (GitHub API) | 2024 | v2 avoids polluting git history; only needs `actions: write` |
| Manual `git config && git add && git commit && git push` in run: block | `stefanzweifel/git-auto-commit-action@v7` | Ongoing | Handles all edge cases including dirty-check and skip-ci |

**Deprecated/outdated:**
- `actions/cache@v3`: Use `v4`. v3 had limitations around the new Actions cache service (rolled out Feb 2025).
- `actions/checkout@v2/v3`: Use `v4`. Earlier versions use Node 16 which is deprecated on GitHub's hosted runners.
- `setup-python@v4`: Use `v5`. v5 adds support for `cache-dependency-path` and improved Python version resolution.

---

## Open Questions

1. **Should `.seen_urls` be in `.gitignore`?**
   - What we know: The file currently exists in the repo root (per `SEEN_URLS_PATH` in `deduplicate.py`). The git commit-back strategy requires it NOT to be gitignored.
   - What's unclear: Whether it's currently gitignored.
   - Recommendation: Check `.gitignore` in Wave 0. If `.seen_urls` is listed, remove that line. The file should be tracked.

2. **What happens on the very first run when `.seen_urls` doesn't exist yet?**
   - What we know: `load_seen_urls()` returns `{}` on `FileNotFoundError` — this is already handled gracefully.
   - What's unclear: Whether `git-auto-commit-action` will create and commit a new file (not just modify an existing one).
   - Recommendation: It will — `git-auto-commit-action` runs `git add` which stages new files. First run creates and commits the file with the day's seen URLs.

3. **Does `orchestrator.py` use `WSJ_RSS_URL` and `THE_INFO_RSS_URL` from env vars, or are they hardcoded?**
   - What we know: INFRA-05 requires these as env vars. The `.env` file has them. Whether the Python fetchers read from `os.environ` is unknown without reading the fetcher code.
   - What's unclear: If they're hardcoded in `fetchers/rss.py`, that violates INFRA-05 and requires a code change.
   - Recommendation: Add a Wave 0 task to audit `fetchers/rss.py` for hardcoded URLs and migrate to `os.environ.get('WSJ_RSS_URL', ...)` if needed.

---

## Sources

### Primary (HIGH confidence)
- [GitHub Actions schedule event official docs](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule) — cron syntax, inactivity disable, delay behavior
- [GitHub Actions workflow_dispatch official docs](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#workflow_dispatch) — manual trigger syntax
- [GitHub Actions timeout-minutes official docs](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#jobsjob_idtimeout-minutes) — job-level timeout syntax
- [GitHub Actions using secrets official docs](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions) — secrets context, env mapping
- [GitHub Actions setup-python marketplace](https://github.com/marketplace/actions/setup-python) — `cache: 'pip'` parameter (v5)
- [GitHub Actions Python tutorial](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) — complete workflow shape for Python projects
- [gautamkrishnar/keepalive-workflow marketplace](https://github.com/marketplace/actions/keepalive-workflow) — v2 syntax, permissions, `time_elapsed` parameter
- [stefanzweifel/git-auto-commit-action marketplace](https://github.com/marketplace/actions/git-auto-commit) — v7 syntax, `file_pattern`, `[skip ci]` behavior, permissions

### Secondary (MEDIUM confidence)
- [GitHub Community discussion: persistence between workflow runs](https://github.com/orgs/community/discussions/137587) — confirmed Actions cache 7-day expiry makes it unsuitable for daily state; git commit-back is the de facto standard
- [GitHub Actions controlling permissions for GITHUB_TOKEN](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token) — `contents: write` must be explicit
- [actions/cache GitHub repo](https://github.com/actions/cache) — 7-day sliding expiry confirmed; 10GB per-repo default

### Tertiary (LOW confidence)
- None — all critical claims verified against official docs

---

## Metadata

**Confidence breakdown:**
- INFRA-01/02/03 (cron, dispatch, timeout): HIGH — verified directly against official GitHub docs
- INFRA-04 (keepalive): HIGH — verified against marketplace action README and official GitHub docs re: 60-day rule
- INFRA-05 (secrets mapping): HIGH — verified against official secrets docs
- `.seen_urls` git commit-back strategy: HIGH — confirmed by official cache docs (7-day expiry), official git-auto-commit-action docs, community discussion
- Keepalive v2 API mode: HIGH — verified against action README
- `setup-python@v5 cache: 'pip'`: HIGH — verified against official Python tutorial and marketplace page

**Research date:** 2026-03-01
**Valid until:** 2026-06-01 (GitHub Actions syntax is stable; action versions may increment but patterns remain)
