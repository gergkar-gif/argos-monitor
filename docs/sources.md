# Source Registry & Taxonomy

The declarative source registry is the foundation of Argos Monitor's independent corroboration model. Across **89 country desks**, **1,491 outlets** (**1,672 feeds**) are catalogued in `countries/<id>/sources.yaml` and enriched via `argos/ratings.py`.

You can browse and filter the complete live registry interactively at [`https://argosmonitor.uk/about.html#sources`](https://argosmonitor.uk/about.html#sources).

---

## 1. Declarative Schema (`countries/<id>/sources.yaml`)

Each country pack defines its monitored media ecosystem across three reporting scopes so the clustering engine can distinguish domestic state narratives, diaspora/exile reporting, and international wire coverage:

```yaml
sources:
  - id: vnexpress
    name: VnExpress
    homepage: https://vnexpress.net
    language: vi
    scope: domestic          # domestic | abroad_local | international
    kind: media              # media | official | wire
    governing_body: Ministry of Science and Technology
    state_affiliated: true
    reprints_vna: true
    alignment: state_controlled
    bias: state_aligned
    factuality: mostly_factual
    feeds:
      - url: https://vnexpress.net/rss/thoi-su.rss
        section_label: Thời sự
        category_hint: internal_politics
```

---

## 2. Classification Dimensions

### Reporting Scope (`scope`)
* **`domestic`:** Media organisations, state news agencies, and official government portals operating inside the country.
* **`abroad_local`:** Diaspora, exile, and international public broadcasters publishing in the country's primary languages from outside its jurisdiction (e.g. *Meduza*, *Enab Baladi*, *The Irrawaddy*, *Luật Khoa*, *Radio Farda*, *Efecto Cocuyo*).
* **`international`:** Global and regional wire services, financial dailies, and foreign-affairs publications covering the country externally.

### Source Type (`kind`)
* **`media`:** Newspapers, broadcast networks, investigative portals, and magazines.
* **`wire`:** Statutory and commercial wire agencies (e.g. *VNA*, *TASS*, *Xinhua*, *ANSA*, *EFE*, *PAP*, *Yonhap*, *Kyodo*, *ANTARA*, *BERNAMA*).
* **`official`:** Ministries of Foreign Affairs, executive offices, central banks, and statutory commissions. Stories containing an `official` source are badged `Official source`.

### Political Alignment (`alignment`)
* **`state_controlled`:** Directly operated by the state, ruling party, or armed forces.
* **`pro_government`:** Privately held or foundation-backed outlets closely aligned with the governing executive.
* **`public_broadcaster`:** Statutory public service broadcasters with editorial charters (e.g. *BBC*, *ARD/ZDF*, *NHK*, *Yle*, *NRK*, *ABC*).
* **`independent`:** Editorially independent commercial or non-profit newsrooms.
* **`opposition`:** Outlets explicitly aligned with political opposition movements or exiled dissident groups.

### Editorial Leaning (`bias`) & Factuality (`factuality`)
* **Editorial Leaning:** `left`, `center-left`, `center`, `center-right`, `right`, `state_aligned`.
* **Factuality:** `very_high`, `high`, `mostly_factual`, `mixed` (derived from established international media-bias and fact-checking standards, combined with structural rules for official and state-controlled organs).

---

## 3. Syndication & Wire Deduplication

State wire dispatches and commercial agency copy are frequently reprinted verbatim across dozens of domestic portals. Argos prevents artificial amplification through two mechanisms:
1. **Normalized Content Hashing & Cosine Deduplication:** Articles within the same story cluster with embedding cosine similarity $\ge 0.95$ or identical normalised headlines are linked via `syndicated_of` and counted once in independent outlet totals.
2. **Aggregator Resolution (`aggregator: google_news`):** For outlets that block automated RSS polling via cloud IP ranges, country packs ingest targeted Google News publisher/query feeds, resolving the original publisher identity (`gn:<publisher>`) and applying the same rating taxonomy and deduplication rules.

---

## 4. Verification & Maintenance

Feed reachability and schema integrity across all 87 country packs are validated via:
```powershell
python -m unittest discover -s tests
python tools/check_feeds.py
```
