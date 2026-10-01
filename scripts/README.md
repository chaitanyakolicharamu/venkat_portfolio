# Portfolio maintenance scripts

- `build_fixtures.py`: authoring source for the committed synthetic corpus and explicit evaluation expectations. It does not copy system output into labels.
- `build_showcase.py`: renders Markdown reports, SVG figures, and demo metric cards from the recorded benchmark JSON. Requires `matplotlib`.
- `verify_demo.py`: starts both installed applications, runs the browser smoke test, captures screenshots, and shuts down its servers.
- `verify_browser.cjs`: Playwright flow checks for both applications. Defaults to ports 8011 and 8012; `AGENT_URL` / `RAG_URL` can override them.

From the repository root, with both Python packages installed in the active environment:

```bash
python -m pip install matplotlib
npm install --no-save playwright@1.62.1
npx playwright install chromium
python scripts/verify_demo.py
python scripts/build_showcase.py
```

For an already installed compatible Chromium, set `CHROMIUM_EXECUTABLE_PATH`. `CHROMIUM_PACKAGE` accepts a serverless Chromium module when needed. The normal path uses Playwright's own browser.

Run each project's evaluation and the RAG scale benchmark before regenerating reports. Quality suites are fast; the scale benchmark needs additional RAM. Generated scorecards always derive from recorded JSON.
