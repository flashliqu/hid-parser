# Temporal report comparison

Open `temporal/index.html` locally or visit the GitHub Pages `/temporal/` page. Select the original, new-spatial/old-temporal, and new-spatial/new-temporal IFPSim HTML reports in their labeled slots. Generate a preview, then download the standalone comparison HTML.

All processing happens locally in the browser. Source reports and generated results are not committed or uploaded. No Node.js installation is needed to use the webpage.

The converter expects the FolderAccuracy report format with per-file spatial/temporal counts, nine-region grids, source-label summaries, and settle latency. It checks matching recording names, aggregate counts, region counts, and latency touch counts, and rejects incompatible reports. Missing latency is an error rather than zero. Assign configurations explicitly; filenames need not follow a fixed naming convention.

Latency mean, median, p95, maximum, and touch count are retained as reported. Finger and thumb remain separate in latency tables; accuracy combines them. Stage denominators can differ, so accuracy deltas are descriptive rather than matched-frame comparisons.

GitHub Pages publishes this directory alongside the existing HID decoder through `.github/workflows/deploy-pages.yml`.

Run converter validation with three local source reports (the reports stay outside the repository):

```sh
node test_temporal.js /path/acm_original.html /path/new_spatial_old_temp.html /path/new_spatial_new_temp.html
```

## Run on a local port

Requires Python 3. On Windows, double-click `temporal/start-local.cmd`, then open
<http://127.0.0.1:8000/>. Keep the launcher window open while using the page.

From a terminal, run from the repository root:

```sh
python temporal/serve.py
```

Use `python3` if that is your system's Python 3 command. For a different port:

```sh
python temporal/serve.py --port 8001
```

Open the printed URL, select the three reports, generate the comparison, and download
its HTML. Press Ctrl+C in the terminal to stop the server. The launcher binds only
to `127.0.0.1` and serves only the converter's HTML and JavaScript assets, regardless
of the working directory. It does not accept report uploads or serve your reports.
The HID decoder link returns to this same converter when running locally.
