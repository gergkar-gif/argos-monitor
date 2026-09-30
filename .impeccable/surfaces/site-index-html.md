---
version: 1
slug: "site-index-html"
primary_target: "site/index.html"
related_targets: []
---

# Argos Monitor site (site/index.html)

Mode: Operate. Visitor picks a country, period and topic, presses Research, reads a collection of the week's Vietnam news grouped by topic, then opens a story to check sources.

Audience and constraints: one non-developer owner, daily briefing on laptop and phone; later possibly public. Every line on the page is an article's own headline or a verbatim quote linked to its source. English interface, original-language article text. No translation shown (D11 paused): leave a slot under each headline for one later. Vanilla HTML/CSS/JS, no framework; opens from a local folder (no fetch of local files: data loaded through script tags).

Unresolved: hosting; translation line; more countries.

## Direction contract

THESIS: The page is a press-cuttings bureau's client folder: each story is one clipping pasted on a filing card, quotes are pasted strips, and every claim carries a rubber source stamp. It refuses the news-site headline list and the analytics-dashboard grid of tiles.

OWN-WORLD: Cool grey-green index-card stock (not cream) as the desk, newsprint-white clippings, ink near-black with a green cast. Rubber-stamp inks carry all meaning: indigo for outlet stamps, oxide red for OFFICIAL, teal for "not in domestic press". Topic drawers are index tabs in six muted inks (brick, cobalt, forest, plum, ochre, slate). Source Serif 4 for headlines and quotes, Barlow Condensed caps for stamps and tabs (covers Vietnamese diacritics), Courier Prime only for typed slip labels and numerals. Hairline rules, no shadows heavier than a card's one soft drop, no cards inside cards.

STORY: Within seconds the reader sees what the biggest issues in Vietnam are, sorted by topic, and how independent the coverage is: how many outlets (copies counted once), whether domestic, Vietnamese-language abroad or international, and whether a story is missing from domestic press. They believe it because each strip is stamped with its outlet and links to the original. They act by opening the source or narrowing the topic.

FIRST VIEWPORT: A typed request slip across the top (Country, Period, Topic selects and a stamped Research button, one row on desktop, stacked on phone), beneath it the result line ("Vietnam, last 7 days, 72 stories, updated 14:42"), then a row of topic index tabs with counts, then the first topic drawer with its lead clipping at reading scale (headline in the serif, stamp row, two pasted strips). Primary action: Research, top right of the slip.

FORM: Press-cuttings bureau (candidate 1 of 7 grounded, IMPECCABLE'S PICK, chosen by the user; seed key 18c8e847).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
