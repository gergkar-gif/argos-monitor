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
   - State: Source depth audit script `tools/audit_sources.py` implemented; 83 major global and regional desks expanded to >= 10 verified independent sources (Jordan: 11, Qatar: 11, Saudi Arabia: 10, Lebanon: 12, Syria: 12, United Arab Emirates: 10, DR Congo: 11, Iraq: 10, Iran: 10, Egypt: 10, Denmark: 11, Georgia: 11, Israel: 10, Algeria: 10, Morocco: 10, Uzbekistan: 10, West Africa: 10, Kyrgyzstan: 10, Kosovo: 10, Ecuador: 10, Vietnam: 27, Hungary: 16, South Africa: 14, Ireland: 12, Argentina: 10, Armenia: 10, Australia: 10, Austria: 10, Azerbaijan: 10, Baltics: 10, Belarus: 10, Belgium: 11, Bosnia: 10, Brazil: 11, Canada: 10, Caribbean: 11, Central America: 11, Chile: 10, Colombia: 11, Czechia: 11, East Africa: 10, Ethiopia: 10, Finland: 11, Greece: 10, Indonesia: 11, Kazakhstan: 10, Kenya: 10, Malaysia: 10, Mexico: 10, Moldova: 10, Myanmar: 11, Netherlands: 10, Nigeria: 10, Norway: 10, Pacific Islands: 10, Pakistan: 10, Peru: 10, Portugal: 11, Romania: 10, Serbia: 11, South Korea: 11, Spain: 11, Sweden: 11, Switzerland: 10, Taiwan: 11, Thailand: 11, United States: 11, Venezuela: 11, Cambodia: 10, China: 10, France: 10, Germany: 10, India: 10, Italy: 10, Japan: 10, Philippines: 10, Poland: 10, Russia: 10, Singapore: 10, Slovakia: 10, Turkey: 10, Ukraine: 10, United Kingdom: 10).
   - Next: Expand final 4 deficit packs (Bangladesh, Sri Lanka, Laos, North Korea) to >= 10 direct, independent sources (excluding aggregators) with verified RSS/Atom feeds to achieve 100% compliance across all 87 desks.
