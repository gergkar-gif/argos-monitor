# Roadmap

Active queue and open work only. Completed work is logged in `ACHIEVED.md`.

## Active Queue

1. **Saved watches and morning executive brief automation**
   - State: Local browser localStorage watch chips and static printable brief page (`site/brief.html`) implemented.
   - Next: Build automated email or webhook delivery of the morning executive delta brief (e.g. top surging stories, international pickups, macro agenda shifts) via scheduled GitHub Actions runner.

2. **Basic Social Watch from accessible sources**
   - State: Reddit subreddit monitoring and Google Trends ingestion active in sidebar.
   - Next: Ingest public Telegram channels and Bluesky accounts for high-priority desks (e.g. Ukraine, Russia, Central Asia, Levant) into verified auxiliary signals.

3. **Offline headline translation (`opus-mt-vi-en` / Marian)**
   - State: In-browser WebAssembly client-side translation active via Transformers.js for selected languages.
   - Next: Evaluate local Python Marian pipeline step for pre-translating non-English headlines prior to static JSON export for low-resource devices.

4. **Optional LLM layer for top stories with strict quote verification**
   - State: Architectural decision D2 rules that core pipeline requires no LLM; quote-verification check specified in Rule 1 and Rule 2.
   - Next: Create optional post-processing script (`argos/llm_digest.py`) using Gemini or local llama.cpp that takes top 5 story clusters, writes bullet-point summaries, and drops any sentence lacking a verbatim string-match quote in the stored article text.
