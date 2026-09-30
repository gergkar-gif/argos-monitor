# Sources

The source registry is the core of the product. Each outlet needs metadata (scope, governing body, whether it reprints VNA), so the app can count *independent* coverage.

> **Status: verified 2026-09-30.** Results are in the table below; the machine-readable registry is [`sources.yaml`](../sources.yaml). Re-check with `python tools/check_feeds.py` (needs `pyyaml`; exits non-zero if any active feed fails). Governing bodies are marked "(to confirm)" in the yaml where I could not check them.

## Verification results
| Outlet | Result |
|---|---|
| VnExpress (+ International), Tuổi Trẻ, Thanh Niên, Dân trí, VietnamNet, Nhân Dân, VietnamPlus (vi + en), VOV, BBC vi, RFI vi, Luật Khoa, The Diplomat, SCMP, CNA | **Working**, fresh items. Section feeds are in the yaml. |
| Quân đội Nhân dân | Working, but only the "latest news" feed found, and it needs cookies kept across requests. |
| Báo Chính phủ, National Statistics Office | Working (feeds at `/<section>.rss`; NSO is low volume). |
| Nikkei Asia | Feed works, headlines only (paywall). |
| GDELT DOC API | Works. One request per 5 seconds. |
| Dân trí (Xã hội feed) | Stale since Sep 2025; other Dân trí feeds are fine. |
| VOV | Main `/rss/` page is stale (May 2025); the section feeds work. Returns 403 to a Chrome-like User-Agent. |
| VOA Tiếng Việt | **Dead.** Feeds respond but the newest item is March 2025. |
| RFA Tiếng Việt | Site still publishes, but its RSS is empty. Needs scraping if wanted. |
| DW Tiếng Việt | **Gone.** dw.com/vi redirects to the English site. |
| Người Việt | Unreachable from this PC (TLS handshake fails). Retry later. |
| MOFA, State Bank, National Assembly, Tạp chí Cộng sản, dangcongsan.vn | **No working RSS.** Would need listing-page scraping. Left out of the MVP. |
| Reuters | Blocks scripts (HTTP 401), no public RSS. Use GDELT for discovery. |

Things the ingest code must handle: Dân trí fails Python's TLS check (curl works); Tuổi Trẻ and Báo Chính phủ dates look like `9/30/2026`; VietnamNet feeds hold about 1000 items; The Diplomat, SCMP and CNA feeds cover many topics, so filter for Vietnam.

## Registry fields
See `source` and `feed` in [architecture.md](architecture.md). The minimum for each outlet is name, homepage, language, scope, kind, governing body (*cơ quan chủ quản*), whether it reprints VNA, and its section feed URLs with a category hint for each.

## Candidates: domestic (scope=domestic)
| Outlet | Language | Governing body (to verify) | Notes |
|---|---|---|---|
| VnExpress | vi | Ministry of Science & Technology | Very high volume, has section RSS |
| Tuổi Trẻ | vi | Ho Chi Minh City Youth Union | |
| Thanh Niên | vi | Vietnam Youth Federation | |
| Dân trí | vi | Ministry of Home Affairs (?) | |
| VietnamNet | vi | Ministry of Science & Technology (?) | |
| Nhân Dân | vi | Communist Party Central Committee | The Party's official line |
| Quân đội Nhân dân | vi | Ministry of Defence | Useful for defence & security |
| VnExpress International | en | as VnExpress | Domestic, even though in English |
| VietnamPlus / VNA | vi, en | Vietnam News Agency | **Wire service: the main source of syndicated copies** |
| VOV | vi | Voice of Vietnam | |
| Tiền Phong, Lao Động, Người Lao Động, Pháp Luật TP.HCM | vi | various | Add if volume or diversity is needed |

## Candidates: official (scope=domestic, kind=official)
| Source | Notes |
|---|---|
| Báo Điện tử Chính phủ (baochinhphu.vn) | Government portal |
| Ministry of Foreign Affairs (mofa.gov.vn): spokesperson statements | Foreign policy |
| National Assembly (quochoi.vn) | Legislation |
| State Bank of Vietnam (sbv.gov.vn) | Economics: rates, currency |
| General Statistics Office / National Statistics Office | Economics: GDP, CPI |
| Tạp chí Cộng sản / dangcongsan.vn | Party decisions, personnel |
These may lack RSS. If so, scraping the listing pages may be needed, so check each one.

## Candidates: Vietnamese-language, outside Vietnam (scope=abroad_vi)
| Outlet | Notes |
|---|---|
| BBC News Tiếng Việt | |
| RFI Tiếng Việt | |
| VOA Tiếng Việt | **Check whether it still publishes.** US funding cuts in 2025. |
| RFA Tiếng Việt | **Check whether it still publishes.** Heavily reduced in 2025. |
| Luật Khoa tạp chí / The Vietnamese Magazine | Independent, focused on politics and law |
| Người Việt (California) | Diaspora press |
| DW Tiếng Việt | Check whether it still exists |

## Candidates: international (scope=international)
| Outlet | Notes |
|---|---|
| GDELT DOC API | Discovery across many languages. Query for Vietnam; free; returns URLs + metadata, not article text |
| Reuters (Asia) | May be paywalled or have no RSS. Rely on GDELT for discovery |
| Nikkei Asia | Paywalled. Headlines only |
| The Diplomat (Southeast Asia) | |
| South China Morning Post (Southeast Asia) | |
| Channel NewsAsia | |
| AP / AFP via other outlets | Syndication: count once |

## Category hints for section feeds
Map section names to categories when adding a feed, for example:
`Thời sự / Chính trị` → internal_politics · `Kinh doanh / Kinh tế` → economics · `Thế giới` → foreign_policy (only if Vietnam is involved; otherwise skip) · `Pháp luật` → internal_politics or security (decide per story) · `Quân sự / Quốc phòng` → defence_security · `Giáo dục / Sức khỏe / Xã hội` → society.
