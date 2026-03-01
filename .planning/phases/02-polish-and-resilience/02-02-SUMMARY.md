---
phase: 02-polish-and-resilience
plan: "02"
subsystem: ui
tags: [email, html, jinja2, premailer, dark-mode, css-inlining, gmail]

# Dependency graph
requires:
  - phase: 01-core-pipeline
    provides: render_email() pipeline, digest.html.j2 Phase 1 template, premailer integration
provides:
  - Wispr Flow-inspired email template with dark mode @media block (data-premailer=ignore)
  - premailer transform with keep_style_tags=True + strip_important=False
  - 16 render tests covering correctness, CSS inlining, dark mode, size limits, EMAIL-06
affects:
  - 02-polish-and-resilience (subsequent plans using the render pipeline)
  - Any plan that modifies templates/digest.html.j2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "data-premailer=ignore on dark mode <style> block — premailer skips it, preserving @media rules in output"
    - "keep_style_tags=True + strip_important=False in premailer.transform() — belt-and-suspenders dark mode safety"
    - "Style block size guard: warn if >7000 chars (approaching Gmail 8KB <style> limit)"
    - "TDD for email rendering: test dark mode survival, CSS inlining, HTML size, style block size, EMAIL-06"

key-files:
  created:
    - tests/test_render.py
  modified:
    - templates/digest.html.j2
    - pipeline/render.py

key-decisions:
  - "data-premailer=ignore is sufficient for dark mode preservation even without keep_style_tags=True — but both are used for belt-and-suspenders safety"
  - "HTML comments must not contain 'data-premailer' string — plan verification checks entire HTML output, not just element attributes"
  - "EMAIL-06 verification must strip style blocks before checking for section-label — class name appears in CSS rules but not as rendered elements"
  - "Table-based layout (no flexbox/grid/border-radius/box-shadow) — Gmail strips modern CSS; system font stack only"

patterns-established:
  - "Email template comment strings must not contain attribute names that verification scripts check in full HTML output"
  - "EMAIL-06 empty section suppression tested by stripping <style> blocks before asserting class absence"

requirements-completed: [EMAIL-01, EMAIL-02, EMAIL-04, EMAIL-05, EMAIL-06]

# Metrics
duration: 5min
completed: 2026-03-01
---

# Phase 2 Plan 02: Email Template Redesign Summary

**Wispr Flow-inspired email template with dark mode @media block preserved by premailer via data-premailer=ignore; 16 render tests verify CSS inlining, size limits, and EMAIL-06 empty section suppression**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-01T19:07:12Z
- **Completed:** 2026-03-01T19:12:02Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Full rewrite of digest.html.j2 with Wispr Flow design tokens: white card (#ffffff) on light gray (#f5f5f5) background, system font stack, generous whitespace (40px/36px padding), 10px uppercase section labels
- Dark mode @media block wrapped in `<style data-premailer="ignore">` — premailer skips this block, so all 13 color overrides survive CSS inlining and appear in Apple Mail / iOS Mail
- Fixed premailer call from `transform(raw_html)` to `transform(raw_html, keep_style_tags=True, strip_important=False)` with style block size warning
- 16 render tests covering all success criteria — all pass in 0.5s

## Task Commits

Each task was committed atomically:

1. **Task 1: Redesign digest.html.j2 with Wispr Flow aesthetic + dark mode block** - `1ad1825` (feat)
2. **Task 2: Fix premailer call in render.py and verify output quality (TDD)** - `e369e26` (feat)

## Files Created/Modified

- `templates/digest.html.j2` - Full rewrite: Wispr Flow design system, Gmail-safe table layout, dark mode @media block with data-premailer=ignore, EMAIL-06 empty section guard
- `pipeline/render.py` - Changed transform() to transform(keep_style_tags=True, strip_important=False); added style block size warning
- `tests/test_render.py` - 16 tests: render correctness, dark mode survival, CSS inlining, failed summary fallback, HTML size (<102KB), style block size (<8KB), EMAIL-06 empty section suppression

## Decisions Made

- `data-premailer="ignore"` is the primary mechanism for preserving the dark mode `@media` block; `keep_style_tags=True` in the transform call provides belt-and-suspenders safety
- HTML comments in the template must not contain the string `data-premailer` — the plan's end-to-end verification checks the entire rendered HTML output, not just element attributes
- EMAIL-06 verification strips `<style>` blocks before checking for `section-label` — the class name legitimately appears in CSS rules but should not appear as a rendered element attribute when sections are empty
- Removed the inner nested `<table class="article">` wrapper from Phase 1 template — simpler flat structure, same semantic output, slightly smaller HTML

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] HTML comment contained "data-premailer" string, failing plan verification**
- **Found during:** Task 2 (end-to-end verification run)
- **Issue:** The comment `<!-- DARK MODE BLOCK — data-premailer="ignore" tells premailer to skip this block entirely -->` caused the plan's verification assertion `assert 'data-premailer' not in html` to fail
- **Fix:** Rewrote comment to `<!-- DARK MODE BLOCK — skipped by premailer CSS inliner -->` — removes the attribute name from comment text
- **Files modified:** templates/digest.html.j2
- **Verification:** `assert 'data-premailer' not in html` now passes
- **Committed in:** e369e26 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in comment text causing false failure)
**Impact on plan:** Trivial comment text fix, no behavioral change. All success criteria met.

## Issues Encountered

- Plan's EMAIL-06 verification command `assert 'section-label' not in html or html.count('section-label') == 0` is overly broad — it fails because `section-label` appears as a CSS class name in the preserved `<style>` block. The tests use the correct approach: strip style blocks before checking. The actual EMAIL-06 requirement (no rendered section header elements when sections are empty) is fully satisfied.

## Self-Check

- `templates/digest.html.j2` exists: FOUND
- `pipeline/render.py` has `keep_style_tags=True`: FOUND
- `tests/test_render.py` exists: FOUND
- Commit `1ad1825`: FOUND (feat — template redesign)
- Commit `e369e26`: FOUND (feat — premailer fix + tests)
- 16/16 tests pass: PASS
- HTML size 4,056 bytes (limit 102,000): PASS
- Style block size 2,438 chars (limit 8,192): PASS
- Dark mode @media in output: PASS
- CSS inlined (style= present): PASS
- data-premailer stripped from output: PASS

## Self-Check: PASSED

## Next Phase Readiness

- Email rendering pipeline is fully polished and tested — ready for Phase 2 plan 03
- Dark mode works in Apple Mail / iOS Mail via preserved @media block
- Gmail receives proper inlined CSS (no stripped styles)
- All render tests provide regression safety for future template changes

---
*Phase: 02-polish-and-resilience*
*Completed: 2026-03-01*
