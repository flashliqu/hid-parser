# Report comparison

Open `temporal/index.html` locally or visit the GitHub Pages `/temporal/` page. Name each configuration yourself, pick its IFPSim folder-accuracy HTML report, generate a preview, then download the standalone comparison HTML.

Two reports are enough; a third slot is optional. The names you type become the table headings and the generated report's title, so no fixed naming convention is required for the configurations or the files.

All processing happens locally in the browser. Source reports and generated results are not committed or uploaded. No Node.js installation is needed to use the webpage.

The converter expects the FolderAccuracy report format with per-file spatial/temporal counts, nine-region grids, source-label summaries, and settle latency. Reports that also record the EdgeFilter stage (`EF` in the region grids, plus the object-type `Region summary` table) are compared over all three stages; older reports without it still work and show — for EdgeFilter. It checks matching recording names, aggregate counts, region counts, the object-type region summary when present, and latency touch counts, and rejects incompatible reports. Missing latency is an error rather than zero.

Scopes follow the report's source labels, so finger, thumb, and palm are counted separately alongside the overall totals. Latency mean, median, p95, maximum, and touch count are retained as reported. Stage denominators can differ, so accuracy differences are descriptive rather than matched-frame comparisons.

GitHub Pages publishes this directory alongside the existing HID decoder through `.github/workflows/deploy-pages.yml`.

Run converter validation with two or three local source reports (the reports stay outside the repository):

```sh
node test_temporal.js /path/baseline.html /path/candidate.html [/path/third.html]
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

Open the printed URL, name and select the reports, generate the comparison, and download
its HTML. Press Ctrl+C in the terminal to stop the server. The launcher binds only
to `127.0.0.1` and serves only the converter's HTML and JavaScript assets, regardless
of the working directory. It does not accept report uploads or serve your reports.
The HID decoder link returns to this same converter when running locally.
