# Argos Monitor: Delta Comparison Specification ("What Changed?")

This document defines the mathematical models, classification rules, data schemas, and UI rendering standards for comparing news coverage between contiguous monitoring windows.

Settled decisions: [D24](decisions.md#d24) (zero-emoji broadsheet policy) and [D25](decisions.md#d25) (deterministic delta comparisons).

---

## 1. Operational Rationale

Foreign-ministry press reviewers and geopolitical analysts face severe attention bottlenecks. Cumulative coverage numbers (e.g. "34 articles on transport infrastructure") often obscure critical shifts in news momentum:
- A routine infrastructure project may generate 34 steady articles over 7 days with zero urgency.
- An unexpected cross-border incident or ministerial corruption arrest may generate 16 articles in 4 hours having had 0 articles previously.
- A local environmental controversy previously restricted to domestic regional outlets may suddenly be picked up by international wires (Reuters, Bloomberg, Nikkei), transforming into a diplomatic risk.

The **"What Changed?"** engine calculates delta comparisons between the current monitoring window $T$ and the immediately preceding equivalent slice $T_{-1}$ without using LLMs, heuristic guesswork, or synthetic claims.

---

## 2. Window Slicing Architecture

Let $t_{\text{ref}}$ be the run timestamp (UTC). Let $W$ be the duration of the active window (e.g. 24 hours, 7 days, or 30 days).

The monitoring timeline is partitioned into two contiguous, non-overlapping windows:
- **Current Window ($T$):** $[t_{\text{ref}} - W, \, t_{\text{ref}}]$
- **Prior Reference Window ($T_{-1}$):** $[t_{\text{ref}} - 2W, \, t_{\text{ref}} - W]$

Articles are assigned to windows based on their publication timestamp, with fallback to fetch timestamp:
$$t_{\text{art}} = \text{COALESCE}(\text{published\_at}, \, \text{fetched\_at})$$

An article belongs to window $T$ if $t_{\text{ref}} - W \le t_{\text{art}} \le t_{\text{ref}}$.
An article belongs to window $T_{-1}$ if $t_{\text{ref}} - 2W \le t_{\text{art}} < t_{\text{ref}} - W$.

---

## 3. Story-Level Movement Classification

For each story cluster $S$, let:
- $N_T(S)$: Number of articles associated with $S$ published during window $T$.
- $N_{T_{-1}}(S)$: Number of articles associated with $S$ published during window $T_{-1}$.
- $\Delta N(S) = N_T(S) - N_{T_{-1}}(S)$: Net volume change.
- $V(S) = \frac{N_T(S)}{\max(1, N_{T_{-1}}(S))}$: Velocity multiplier.

### 3.1 Movement States

Every story is deterministically assigned one of five movement states:

| State | Condition | Meaning | Broadsheet Badge |
| :--- | :--- | :--- | :--- |
| `new` | $N_{T_{-1}}(S) = 0 \;\land\; N_T(S) \ge 2$ | Fresh emergence; story had no recorded coverage in the prior period. | `[NEW]` |
| `surging` | $\Delta N(S) \ge 3 \;\land\; V(S) \ge 1.75$ | Strong upward acceleration in reporting volume. | `[SURGE +ΔN]` |
| `cooling` | $-\Delta N(S) \ge 3 \;\land\; V(S) \le 0.40$ | Coverage is fading compared to the prior period. | `[COOLING]` |
| `steady` | $\neg(\text{new} \lor \text{surging} \lor \text{cooling}) \;\land\; N_T(S) \ge 2$ | Active sustained coverage with normal variance. | (none / neutral) |
| `trace` | $N_T(S) < 2 \;\land\; N_{T_{-1}}(S) < 2$ | Isolated or low-frequency reporting. | (none / muted) |

### 3.2 Scope Escalation ("International Pickup")

A key diplomatic indicator is when a domestic issue breaks out into the international press:

Let $\mathcal{O}_T(S)$ be the set of reporting scopes ($\{\text{domestic}, \text{abroad\_local}, \text{international}\}$) present in $S$ during window $T$.

If:
$$\mathcal{O}_{T_{-1}}(S) = \{\text{domestic}\} \quad\text{and}\quad \text{international} \in \mathcal{O}_T(S)$$
The story is tagged:
- `scope_shift: "international_pickup"`
- Broadsheet Badge: `[INTL PICKUP]`

If $\mathcal{O}_{T_{-1}}(S) = \{\text{domestic}\}$ and $\text{abroad\_local} \in \mathcal{O}_T(S)$ (with no international coverage):
- `scope_shift: "diaspora_pickup"`
- Broadsheet Badge: `[DIASPORA PICKUP]`

### 3.3 State Media Narrative Drift (D22 Integration)

Using source ratings established in [D22](decisions.md#d22):
- Let $\text{state\_share}_T(S)$ be the proportion of core articles in $S$ during $T$ from state-controlled, pro-government, or official ministry sources.
- Let $\Delta \text{state\_share}(S) = \text{state\_share}_T(S) - \text{state\_share}_{T_{-1}}(S)$.

If $N_T(S) \ge 4$ and $N_{T_{-1}}(S) \ge 4$:
- If $\Delta \text{state\_share}(S) \ge +0.30$: Story exhibits an **official narrative campaign** (`state_surge: true`).
- If $\Delta \text{state\_share}(S) \le -0.30$: Independent coverage has overtaken state coverage (`state_recede: true`).

---

## 4. Macro Agenda & Category Movement

To measure shifts in the national information environment as a whole, the engine computes category share deltas across the 6 standard Argos topics:
- `internal_politics`
- `economics`
- `foreign_policy`
- `defence_security`
- `society`
- `other`

Let $C_T(c)$ be the total articles in category $c$ in window $T$:
$$S_T(c) = \frac{C_T(c)}{\sum_{k} C_T(k)}$$

The percentage-point shift in topic attention is:
$$\Delta S(c) = \left( S_T(c) - S_{T_{-1}}(c) \right) \times 100$$

A positive $\Delta S(c) \ge +5.0\%$ denotes a **surging topic** (e.g. `Politics ↑ +14%`).
A negative $\Delta S(c) \le -5.0\%$ denotes a **contracting topic** (e.g. `Economy ↓ -11%`).

---

## 5. Export JSON Schema

Delta metrics are serialized directly into `site/data/<country>-<window>.json`:

### 5.1 Story-Level `delta` Object

```json
{
  "id": 1042,
  "headline": {
    "title": "Deputy Minister questioned in semiconductor subsidy probe",
    "url": "https://...",
    "source": "Tuổi Trẻ",
    "language": "vi"
  },
  "articles": 14,
  "independent_sources": 8,
  "delta": {
    "curr": 14,
    "prev": 2,
    "net": 12,
    "ratio": 7.0,
    "state": "surging",
    "scope_shift": "international_pickup",
    "state_share_curr": 0.43,
    "state_share_prev": 0.00
  }
}
```

### 5.2 Macro Agenda `agenda_delta` Object

Attached at the root of `site/data/<country>-<window>.json`:

```json
{
  "country": "vietnam",
  "period": "24h",
  "days": 1,
  "generated_at": "2026-11-03T12:00:00Z",
  "agenda_delta": {
    "internal_politics": { "curr": 48, "prev": 22, "net": 26, "share_pct": 32.4, "share_delta_pct": 14.1 },
    "defence_security": { "curr": 31, "prev": 14, "net": 17, "share_pct": 20.9, "share_delta_pct": 9.2 },
    "foreign_policy": { "curr": 24, "prev": 25, "net": -1, "share_pct": 16.2, "share_delta_pct": -3.8 },
    "economics": { "curr": 26, "prev": 46, "net": -20, "share_pct": 17.6, "share_delta_pct": -13.5 },
    "society": { "curr": 15, "prev": 18, "net": -3, "share_pct": 10.1, "share_delta_pct": -3.9 },
    "other": { "curr": 4, "prev": 6, "net": -2, "share_pct": 2.7, "share_delta_pct": -2.1 }
  }
}
```

---

## 6. Broadsheet UI Guidelines (Rule 7: Zero Emojis)

In accordance with Rule 7, all movement indicators use clean typography, neutral borders, and directional characters:

1. **Card Pill Badges:**
   - `[NEW]`: Font 700, uppercase, bordered box (`border: 1px solid var(--accent); color: var(--accent);`).
   - `[SURGE +12]`: Font 700, bold monospace integer counter.
   - `[INTL PICKUP]`: Distinctive bracketed chip (`[INTL PICKUP]`).
   - `[COOLING]`: Muted ink color (`color: var(--ink-muted);`).

2. **Macro Agenda Bar:**
   - Rendered above the story feed:
   - `Agenda Movement (vs prior 24h): Politics ↑ +14% · Security ↑ +9% · Economy ↓ -14%`

3. **Delta Sort / Filter Options:**
   - Filter dropdown or subtabs:
     - `All Stories`
     - `Movement: Surging & New`
     - `Movement: International Pickups`

---

## 7. Computational Performance

- **One-pass aggregation:** All window slicing is evaluated in a single SQLite query using conditional sums:
  ```sql
  SELECT story_id,
         SUM(CASE WHEN t >= cutoff_curr THEN 1 ELSE 0 END) AS curr_count,
         SUM(CASE WHEN t >= cutoff_prev AND t < cutoff_curr THEN 1 ELSE 0 END) AS prev_count
  FROM ...
  GROUP BY story_id;
  ```
- Memory footprint is $O(\text{stories})$, running in under 25 milliseconds per country pack.
