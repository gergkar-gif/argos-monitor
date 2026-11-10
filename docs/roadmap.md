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
   - State: Source depth audit script `tools/audit_sources.py` implemented; Tier 1 priority desks expanded to >= 10 verified independent sources (US: 11, China: 10, Brazil: 11, UK: 10, Vietnam: 27, Hungary: 16, South Africa: 14, Cambodia: 10).
   - Next: Expand remaining 79 regional country packs to >= 10 direct, independent sources (excluding aggregators) with verified RSS/Atom feeds to pass `tools/audit_sources.py --fail-under`.
