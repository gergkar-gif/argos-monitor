---
name: Argos Monitor
description: A press-cuttings bureau on cool index-card stock; every story a newsprint clipping, every source a rubber stamp.
colors:
  desk: "#d9e0d8"
  desk-deep: "#c9d2c8"
  card: "#f6f7f3"
  ink: "#1a201d"
  ink-2: "#414a45"
  rule: "#bfc8bf"
  field-edge: "#8c988e"
  indigo: "#2b3a8c"
  red: "#a82a1f"
  teal: "#0b6262"
  tab-internal-politics: "#9a3b2e"
  tab-economics: "#24508f"
  tab-foreign-policy: "#2f6b45"
  tab-defence-security: "#5c3d78"
  tab-society: "#8f6210"
  tab-other: "#4b5a63"
typography:
  headline-lead:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.2
  headline:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.28
    letterSpacing: "-0.005em"
  masthead:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.9rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.55
  stamp:
    fontFamily: "Barlow Condensed, Arial Narrow, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "0.1em"
  tab:
    fontFamily: "Barlow Condensed, Arial Narrow, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.08em"
  typed:
    fontFamily: "Courier Prime, Courier New, monospace"
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  sm: "2px"
  md: "3px"
spacing:
  xs: "0.35rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2.5rem"
components:
  clipping:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "1.1rem 1.15rem 1rem"
  request-slip:
    backgroundColor: "{colors.desk}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.9rem"
  button-research:
    backgroundColor: "transparent"
    textColor: "{colors.indigo}"
    typography: "{typography.tab}"
    rounded: "{rounded.md}"
    padding: "0.5rem 1.6rem"
    height: "2.75rem"
  button-research-hover:
    backgroundColor: "{colors.indigo}"
    textColor: "{colors.card}"
  tab:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink-2}"
    typography: "{typography.tab}"
    rounded: "0"
    padding: "0.4rem 0.9rem 0.35rem"
    height: "2.5rem"
  tab-pressed:
    backgroundColor: "{colors.tab-economics}"
    textColor: "{colors.card}"
  stamp:
    textColor: "{colors.indigo}"
    typography: "{typography.stamp}"
    rounded: "{rounded.md}"
    padding: "0.18rem 0.5rem 0.12rem"
  select-field:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.typed}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 2.25rem 0.5rem 0.75rem"
    height: "2.75rem"
---

# Design System: Argos Monitor

## Overview

**Creative North Star: "The Press-Cuttings Bureau"**

This is a new world, not an inherited one: the site was built from a chosen direction (seed key 18c8e847) and this file records what shipped. A client folder at a cuttings agency: cool grey-green index-card stock is the desk, each story is a newsprint clipping taped to a card, and every claim carries a rubber source stamp. It is quiet and clerical, dense but ruled, and carries meaning through ink color rather than decoration.

The physical metaphor is deliberately modest and done in CSS only. Stamps tilt a couple of degrees and pass through one SVG rough-edge filter (`#ink`, fractal noise plus a 1.6 displacement) so edges look pressed. Clippings carry a small tilted translucent tape strip and a single soft drop. There are no raster assets anywhere: no photographs, textures, or paper scans. All paper feel comes from flat color, hairlines, and those two effects.

**Key Characteristics:**
- Grey-green desk, near-white newsprint clippings, ink with a green cast; nothing cream.
- Meaning lives in stamp inks (indigo, oxide red, teal) and six topic tab inks.
- Three faces with fixed jobs: serif for reading, condensed caps for stamps and tabs, typewriter for slip labels and numerals.
- Hairline rules, square-ish corners (2px to 3px), one soft shadow, no cards inside cards.

## Colors

A cool, low-chroma paper palette with saturated-but-muted ink accents that each carry one meaning.

### Primary
- **Outlet Indigo** (#2b3a8c): outlet and REPORTED stamps, the Research button, links on hover, focus ring, text selection.

### Secondary
- **Oxide Red** (#a82a1f): OFFICIAL stamp, error and notice text and borders.
- **Not-Domestic Teal** (#0b6262): the "not in domestic press" stamp.

### Tertiary (topic tab inks)
- **Brick** (#9a3b2e) internal politics, **Cobalt** (#24508f) economics, **Forest** (#2f6b45) foreign policy, **Plum** (#5c3d78) defence and security, **Ochre** (#8f6210) society, **Slate** (#4b5a63) other. Each sets the tab's top edge, the pressed fill, the drawer heading rule, and the "more" button of its drawer.

### Neutral
- **Index-Card Grey-Green** (#d9e0d8): page background and request slip. **Deep Card** (#c9d2c8) is declared but unused in the shipped stylesheet.
- **Newsprint** (#f6f7f3): clippings, header, legend, inputs, tabs.
- **Green-Cast Ink** (#1a201d) text; **Faded Ink** (#414a45) secondary text and labels.
- **Hairline** (#bfc8bf) dividers and clipping borders; **Field Edge** (#8c988e) dashed slip border and select border (hardcoded in CSS, not a custom property).

### Named Rules
**The Ink Means Something Rule.** Indigo, red, and teal are stamp inks with fixed meanings; topic inks belong to tabs and their drawers. Never use a stamp ink as decoration or a topic ink as a stamp.

## Typography

**Display/Body Font:** Source Serif 4 (Georgia, Times New Roman, serif), self-hosted variable 400-700
**Label Font:** Barlow Condensed (Arial Narrow fallback), self-hosted 500 and 600, caps; covers Vietnamese diacritics
**Typed Font:** Courier Prime (Courier New, monospace), self-hosted 400 and 700

**Character:** A newspaper serif for what is read, a stamping-die condensed sans for what is asserted, a typewriter for what is filed.

### Hierarchy
- **Masthead** (700, 1.9rem, 1.1; 1.6rem on phones): site title.
- **Lead headline** (700, 1.75rem, 1.2, max 40rem): the first clipping of a drawer.
- **Headline** (700, 1.25rem, 1.28, balanced): every other clipping; drawer headings are 700 1.5rem.
- **Body** (400, 1.0625rem, 1.55): strips (quotes) capped at 62ch.
- **Stamp and tab** (Barlow 600, 0.85rem stamps, 1rem tabs and buttons, uppercase, 0.08em to 0.14em tracking): stamps, tabs, buttons, summaries, field labels; bylines are 500 at 0.95rem, 0.05em.
- **Typed** (Courier Prime 400, 0.8 to 0.95rem): select values, result line, slip lines, counts, meta.

### Named Rules
**The Three Jobs Rule.** Serif reads, condensed caps assert, typewriter files. Do not set headlines in Barlow or slip numerals in the serif.

## Layout

A single centered column, max-width 68rem, 1rem side padding. Order: header with request slip, result line, tab row, then topic drawers. Drawers are a one-column grid on phones and two columns from 46rem; the lead clipping (and an orphan last clipping) spans both. The slip is four columns on desktop (three selects plus Research), a two-column stack on phones with the third select and button full width. Tabs scroll horizontally on phones instead of wrapping. Rhythm is rem-based: 0.35 to 0.8rem inside components, 1rem grid gap, 1.5rem between tabs and drawers, 2.5rem between drawers. Touch targets are at least 2.5rem tall (2.75rem for select and Research).

## Elevation & Depth

Mostly flat: depth is tonal (desk versus newsprint) plus hairlines. Only clippings lift, with one shadow (`0 1px 0 rgba(26,32,29,0.06), 0 8px 16px -10px rgba(26,32,29,0.4)`). The tape strip (3.6rem by 1.1rem, translucent grey-green, rotated -2.5deg, hanging 0.55rem above the top edge) is the other depth cue. Nothing else casts a shadow.

### Named Rules
**The One Drop Rule.** Only the clipping has a shadow, and it is soft. Nested containers stay flat and separate with a hairline.

## Shapes

Small, near-square corners: 2px on clippings, slip, and selects; 3px on stamps and outlined buttons; tabs are square with a 4px topic-ink top edge. The slip uses a dashed border; all other borders are 1px hairlines. Stamps tilt about -2deg (even children +1.6deg) and are roughened by the `#ink` filter, which is also applied to the Research button.

## Components

### Buttons
- **Research:** outlined stamp, 2px indigo border, transparent fill, indigo Barlow caps at 1.15rem with 0.14em tracking, 3px radius, rough-edge filter. Hover fills indigo with white text (120ms); active nudges down 1px.
- **More:** same outline form in the drawer's topic ink, 1rem caps.

### Tabs
Square newsprint tabs with a 4px topic-ink top edge and a typed count. Pressed state fills with the topic ink and white text.

### Clipping (signature)
Newsprint card, hairline border, 2px radius, one soft drop, tape strip. Contains headline, stamp row, cover line, pasted strips (a hairline-topped quote with a source stamp footer), and a collapsible list of sources. Clippings settle in on load (380ms rise and fade, 45ms stagger), disabled under reduced motion.

### Stamp
Outlined condensed caps in indigo, red, or teal; linked stamps fill indigo on hover.

### Inputs
Selects on newsprint, typewriter text, 1px Field Edge border, 2px radius, inline SVG chevron. Focus is a 2px indigo outline offset 3px on every interactive element.

## Do's and Don'ts

### Do:
- **Do** keep cards flat inside clippings: strips are hairline-separated, not boxed.
- **Do** pair every asserted fact with its source stamp and link.
- **Do** keep stamp tilt within about 2deg and apply the `#ink` filter to stamps only (and Research).
- **Do** honor `prefers-reduced-motion` for entrance animation.

### Don't:
- **Don't** add photographs or raster textures; the paper feel is CSS-only and no raster assets exist.
- **Don't** tint the desk cream or warm; it is cool grey-green.
- **Don't** add shadows beyond the clipping's single drop.
- **Don't** nest boxes inside clippings.
