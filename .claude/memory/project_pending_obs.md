---
name: project_pending_obs
description: Pending observations from CLI testing session 002 - fuzzy matching, event states, FAQ, Nations League verification
type: project
---

From CLI testing session #002 (2026-03-20), these items are pending:

1. **OBS-01: Fuzzy contact matching** — ContactManager needs search_by_name with partial/fuzzy match. User said "Deberia poder hacerme una sugerencia de los Koen"
2. **OBS-02: Nations League assignment** — User counts 9 events for Koen, data shows 10. Nations League may be wrongly assigned. Needs Excel verification from user.
3. **OBS-04: Event status system** — Need to distinguish pendiente (unconfirmed) vs confirmado (date locked) vs cancelado. User said "Creo que es importante crear un 'status evento por confirmar' y 'status evento por ocurrir'"
4. **OBS-05: FAQ document** — Create faq.json to handle common questions without LLM calls. User said "proceder" (proceed).

See docs/issues-cli-testing-002.md for full details.
