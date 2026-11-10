# Roadmap

Active queue and open work only. Completed work is logged in `ACHIEVED.md`.

## Active Queue

1. **Saved watches and morning executive brief automation**
   - State: Local browser localStorage watch chips and static printable brief page (`site/brief.html`) implemented.
   - Next: Build automated email or webhook delivery of the morning executive delta brief (e.g. top surging stories, international pickups, macro agenda shifts) via scheduled GitHub Actions runner.

2. **Optional LLM layer for top stories with strict quote verification**
   - State: Architectural decision D2 rules that core pipeline requires no LLM; quote-verification check specified in Rule 1 and Rule 2.
   - Next: Create optional post-processing script (`argos/llm_digest.py`) using Gemini or local llama.cpp that takes top 5 story clusters, writes bullet-point summaries, and drops any sentence lacking a verbatim string-match quote in the stored article text.

3. **Independent source expansion across all country desks (Phase 3)**
   - State: Source depth audit script `tools/audit_sources.py` implemented; 38 major global and regional desks expanded to >= 10 verified independent sources (Vietnam: 27, Hungary: 16, South Africa: 14, Ireland: 12, Australia: 10, Belgium: 11, Brazil: 11, Canada: 10, Czechia: 11, Finland: 11, Indonesia: 11, Myanmar: 11, Netherlands: 10, Nigeria: 10, Norway: 10, Portugal: 11, Serbia: 11, South Korea: 11, Spain: 11, Sweden: 11, Taiwan: 11, Thailand: 11, United States: 11, Cambodia: 10, China: 10, France: 10, Germany: 10, India: 10, Italy: 10, Japan: 10, Philippines: 10, Poland: 10, Russia: 10, Singapore: 10, Slovakia: 10, Turkey: 10, Ukraine: 10, United Kingdom: 10).
   - Next: Expand remaining 49 regional country packs to >= 10 direct, independent sources (excluding aggregators) with verified RSS/Atom feeds to pass `tools/audit_sources.py --fail-under`.
