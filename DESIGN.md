---
name: Argos Monitor
description: Minimalist white broadsheet and world directory; slate-black ink on pure white, vertical left bars, and red reserved strictly for crisis and violence.
colors:
  bg: "#ffffff"
  surface-warm: "#fbfaf8"
  ink: "#111827"
  ink-2: "#4b5563"
  ink-3: "#6b7280"
  rule: "#d1d5db"
  rule-soft: "#e2e8f0"
  bar: "#1e2433"
  indigo: "#1e3a8a"
  red: "#991b1b"
  teal: "#0f766e"
  purple: "#6b21a8"
  orange: "#c2410c"
  t-internal_politics: "#1e2433"
  t-economics: "#1e3a8a"
  t-foreign_policy: "#0f766e"
  t-defence_security: "#312e81"
  t-society: "#78350f"
  t-other: "#4b5a63"
typography:
  sans: '-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
  scale:
    xs: "0.75rem"
    sm: "0.85rem"
    base: "1rem"
    lg: "1.2rem"
    xl: "1.5rem"
    2xl: "2rem"
rounded:
  sm: "2px"
  md: "4px"
spacing:
  xs: "0.35rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2.5rem"
---

# Design System: Argos Monitor

## Overview

**Creative North Star: "Minimalist Broadsheet & World Directory"**

Argos Monitor is an evidence-first open-source media and crisis intelligence dashboard for foreign-affairs analysts. The interface is a clean, high-contrast white broadsheet (`#ffffff`) with deep slate-black ink (`#111827`), hairline dividers (`#d1d5db`), and thick vertical left accent bars (`#1e2433`) on story blocks. On the home screen, the **87-country directory** is the primary focal point, preceded only by a compact one-line alert summary and followed by thematic story sections.

**Key Characteristics:**
- Pure white canvas (`#ffffff`) with warm-tinted utility bars (`#fbfaf8`) for secondary controls.
- **Red Means Crisis:** `#991b1b` is reserved strictly for crisis alerts, violence/armed clash indicators, and surge warnings — never for active navigation links or active region tabs.
- Single sans-serif family (`--sans`) across the operational dashboard, with `tabular-nums` on directory counts and timestamps.
- Zero emojis anywhere in the interface; clean typographic labels and directional arrows only.

## Colors

### Primary & Semantic Inks
- **Slate Ink (`--ink`, `#111827`):** primary headlines, active navigation/tab underlines, focus rings, country tags.
- **Secondary Ink (`--ink-2`, `#4b5563`):** quotes, secondary labels, table headers.
- **Muted Ink (`--ink-3`, `#6b7280`):** metadata, timestamps, counts, placeholders (minimum 4.83:1 contrast on `#ffffff`).
- **Indigo (`--indigo`, `#1e3a8a`):** links on hover, reported/corroborated indicators, international pickups.
- **Crisis Red (`--red`, `#991b1b`):** crisis alerts, official/state-dominated warnings, surge indicators, armed clash tags.
- **Teal (`--teal`, `#0f766e`):** new stories (0–24h), non-domestic reporting.
- **Purple (`--purple`, `#6b21a8`):** election tracking and religious-sensitivity flags.
- **Orange (`--orange`, `#c2410c`):** mixed state and independent coverage.

### Neutrals & Surfaces
- **Canvas (`--bg`, `#ffffff`):** page background and story area.
- **Warm Paper (`--surface-warm`, `#fbfaf8`):** secondary control bars (`.bilateral-bar`, `.monitor-bar`, `.agenda-bar`, combobox group headers).
- **Hairline (`--rule`, `#d1d5db`)** and **Soft Rule (`--rule-soft`, `#e2e8f0`):** section and row dividers.
- **Accent Bar (`--bar`, `#1e2433`):** 5px vertical left bar on story items and alert blocks.

## Typography

**Primary Font (`--sans`):** `-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`

### 6-Step Type Scale
- **`--fs-2xl` (`2rem`):** desktop masthead title (drops to `--fs-lg` on mobile).
- **`--fs-xl` (`1.5rem`):** lead story headline.
- **`--fs-lg` (`1.2rem`):** standard story headline, mobile masthead.
- **`--fs-base` (`1rem`):** body copy, quoted excerpts, mobile form inputs (prevents iOS zoom).
- **`--fs-sm` (`0.85rem`):** table cells, desktop inputs, metadata lines, descriptions.
- **`--fs-xs` (`0.75rem`):** uppercase section headers, navigation links, region tabs, stamps, form labels.

## Layout & Hierarchy

- **Container:** single centered column (`max-width: 68rem`), `1.5rem` horizontal padding on desktop (`1rem` on mobile).
- **Home Page Order:**
  1. Masthead, unified 8-link primary navigation (including Top Reported printable brief and About), and filter bar (Country combobox + debounced Search with inline clear).
  2. Pinned desks / watch chips (when set) and 2-zone crisis alert summary (lead alert + Refresh / All link).
  3. **Monitored countries directory** (top 15 by Attention with expand-all to 87, inline Region select and Sort controls; stacked cards on mobile).
  4. Thematic story sections below (Elections & ballot coverage, Fastest growing, Most reported) with two-layer card metadata (concise headline + source/velocity stamps on the surface; secondary signals, perspective mix, and similarity bands inside `All N articles`).
- **Touch Targets:** minimum `44px` (`2.75rem`) height for interactive controls on mobile.
