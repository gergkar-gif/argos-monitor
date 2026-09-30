# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
A static site (`site/`): plain HTML, CSS and a little vanilla JavaScript, no framework. A Python pipeline writes precomputed data files (JSON) per country and period; the page filters them in the browser. Runs from a local folder now; to be published to a free static host later (hosting undecided, decision D12).

## Users
One person (the project owner), who does not write code and does not read Vietnamese fluently. Reads it on a laptop and on a phone. The main routine is a daily briefing: skim the top issues in a few minutes, then open a story to see who reported it and follow links to the original articles.

## Product Purpose
Argos Monitor answers "what are the main issues happening in and with Vietnam?". The user picks a country (only Vietnam is set up), a time period (24 hours or 7 days at first) and a topic (or all topics), and presses Research. The app collects news, groups articles about the same event into stories, sorts stories by subject, ranks them, and shows where the coverage comes from: domestic outlets, Vietnamese-language outlets abroad, and international outlets. Only stories that are about Vietnam or involve it are shown. Success: the user can see the ten most important issues in minutes and trust that each claim traces to a real article.

## Positioning
Evidence-first. Every sentence on the page is either an article's own headline or text quoted verbatim from a stored article, linked to its source article. Source counts are independent counts, not raw article counts: syndicated copies (for example reprints of Vietnam News Agency copy) count once. The page also flags stories covered abroad but missing from domestic media, which matters because Vietnamese domestic outlets are all state-affiliated.

## Operating Context
Runs locally on a Windows 11 laptop (8 GB RAM, CPU only), no LLM in the core pipeline, refreshed manually or by Windows Task Scheduler every few hours. Output is a single static HTML file opened in a browser.

## Capabilities and Constraints
- Story data available now: category (internal politics, economics, foreign policy, defence and security, society, other), score, article and independent-source counts, split by domestic / abroad_vi / international, representative headline, member articles with source, time and original URL, and an evidence label (OFFICIAL if any member article is from an official source such as the government portal, otherwise REPORTED).
- Article titles are in Vietnamese (mostly) or English. The original-language article is the authoritative source; a translation is never evidence (project rule 4).
- The international side is currently empty until GDELT or a Google News feed works, so the "covered abroad, missing at home" flag cannot yet be shown with real data.
- Must stay light: no heavy client-side frameworks, works offline once generated.
- **Headline language (D11, decided).** English is the primary line on every headline, quote and source-list title, translated by the reader's own browser (on-device Translator API; Chrome and Edge on a computer). The original Vietnamese is hidden by default (English only) and appears beside each line when the reader turns on "Show original"; every headline links to the original article. Where the browser cannot translate, the original is shown with a note. The app writes and stores no translations and no summaries of its own.

## Brand Commitments
Working name "Argos Monitor". No logo or brand assets exist. Interface labels and headings in English (inferred from the user's own language; confirm if a Vietnamese interface is wanted). Article titles and quotes are shown in their original language.

## Evidence on Hand
Real data in the local database: about 6,150 articles from 20+ outlets, 1,637 stories in the 7-day window, with categories and scores. Sample top stories: the Bến Lức–Long Thành expressway opening, customs priority enterprises, the Yên Bái and Mai Anh trials. No international or Vietnamese-language-abroad stories in the top ranks yet. No user testimonials, no brand assets.

## Product Principles
1. No source, no statement: nothing appears that is not an article's own headline or a verbatim quote linked to its article.
2. Show independent coverage, not volume: counts that collapse syndicated copies, with the domestic / abroad / international split visible on every story.
3. Briefing first, evidence one step down: the top issues are readable in minutes; sources and quotes are one click away.
4. Vietnam-relevant only: foreign stories appear only when they concern Vietnam.
5. Honest about gaps: empty or thin sections say so rather than being padded.

## Accessibility & Inclusion
Must be readable on a phone. Text in two scripts: Vietnamese diacritics must render correctly with a font that covers them. Ordinary contrast and keyboard-accessibility standards apply; no product-specific requirement beyond that was stated.
