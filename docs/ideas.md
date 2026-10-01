# Ideas saved for later

Not planned. Parked so they are not lost. Checked on 2026-10-01 from the author's PC unless stated.

## Crisis and official watch feeds (more relevant for developing countries)
The user decided to save these for later: they matter most for countries where security, disasters or humanitarian
situations drive the news. Each would appear as an "official" item, filtered to the country.

| Source | Check result | Notes |
|---|---|---|
| UK Foreign Office travel advice, `https://www.gov.uk/foreign-travel-advice/<country>.atom` | Works | One entry: the latest advisory update. Open Government Licence. |
| US State Department travel advisories, `https://travel.state.gov/_res/rss/TAsTWs.xml` | Works (217 items, all countries) | Filter by country name. |
| GDACS disaster alerts (UN/EU), `https://www.gdacs.org/xml/rss.xml` | Works (global, 212 items) | Floods, storms, earthquakes; filter by country name. |
| Crisis Group, `https://www.crisisgroup.org/rss` | Works (10 recent items) | Filter for the country. The CrisisWatch monthly page itself is blocked (403). |
| USGS significant earthquakes (Atom) | Works | Global. |
| Wikipedia "Current events" portal (API) | Works | Daily event lists with source links; needs HTML parsing; CC BY-SA. |
| ReliefWeb (UN humanitarian reports) | HTTP 202 (access challenge) | Needs a registered app name. |
| ACLED (conflict events) | Needs an API key | Free for researchers. |
| WHO Disease Outbreak News, EU Council, IMF, Europe Media Monitor feeds | Blocked (403) | EMM's web page opens; its feed does not. |

## Other
- A scraper for the state broadcaster (hirado.hu / MTI) for Hungary: it is the government's own voice and has no feed.
- Eurotopics (multilingual European press review) has no feed at the obvious addresses; worth a look for press-review content.
- Fetch article text only for the stories the site shows (about a third of the articles): cuts a run by about two thirds.
