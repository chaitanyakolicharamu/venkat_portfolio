# Recorded validation

Reference run: September 30, 2026 · Python 3.12.14 · Linux.

| Check | Result |
|---|---|
| Agent automated tests | 11 passed, including real MCP stdio client/server integration |
| RAG automated tests | 11 passed |
| Agent guarded-workflow evaluation | 43/43 scenarios passed; 26/26 supported tasks |
| RAG filtered-hybrid evaluation | 46/46 scenarios passed; 32/32 correct first-ranked policies |
| Scale benchmark | 500,000 synthetic records actually indexed; full timing samples committed |
| Browser flows | Incident trace, pause/reject/approve, policy block, tenant-specific citations, abstention passed |
| Browser errors | No uncaught JavaScript errors during the smoke test |
| Responsive layout | No horizontal overflow at 390px in either app |
| Optional SDK compatibility | RAGAS imports and 32-row dataset schema validated; Pinecone and LangSmith imports validated |
| Documentation links | All relative file links resolve |

Screenshots are captured from the running applications with Chromium. Browser checks are reproducible using [verify_demo.py](scripts/verify_demo.py) and [verify_browser.cjs](scripts/verify_browser.cjs).

Cloud API/model execution and Docker image builds were not part of the local validation. The GitHub Actions workflow installs each project in its own environment, runs its tests, checks its evaluation outcomes, and uploads fresh reports.

These are authored synthetic fixtures, not a held-out benchmark or production validation. Exact metrics and dataset hashes are in each project's result report.
