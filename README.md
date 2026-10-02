<img src="site/assets/eye.png" alt="Argos Monitor logo" width="80">

# Argos Monitor

A news monitoring dashboard, starting with Vietnam. See [CLAUDE.md](CLAUDE.md) for what it does and the rules it follows.

## How to run

Open PowerShell in this project folder. Run each command on its own and wait for it to finish.

**1. Install the packages (once).**
```
python -m pip install -r requirements.txt
```

**2. Check the setup (once, and any time something seems broken).**
```
python setup_check.py
```
It creates the data folder `C:\ArgosData` (outside Google Drive, because Drive corrupts database files) and checks that everything is in place. The last line should say `setup OK`. If it says `Setup FAILED`, it lists what to fix.

**3. Check that the news feeds still work (optional).**
```
python tools/check_feeds.py
```
The last line should say `50/50 feeds OK` (the number may change as feeds are added or removed).

To keep the data somewhere other than `C:\ArgosData`, set the `ARGOS_DATA_DIR` environment variable to a local folder before running.

**4. Collect the news and build the site.**
```
python run.py
```
This fetches the feeds of every country, reads the articles, groups them into stories, ranks them and writes the data files the website reads. The first run takes most of an hour (thousands of articles); later runs only read what is new. You can also run one stage, for example `python run.py export`.

**5. Open the website.** Double-click `site\index.html`. Choose a country, a period and a topic, then press Research. (Vietnam and Hungary are set up so far; each country is a folder under `countries`.) If you see "No data found", run step 4 first.

If the page looks broken or your browser complains about a `file:` address, open it over a local address instead. It's one command:
```
python serve.py
```
That opens the site in your browser at `http://localhost:8770/`. Press Ctrl+C in the window to stop it.

The website lives in the `site` folder and is plain files, so it can be published to a free static host later (decision D12).
