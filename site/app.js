/* Argos Monitor page: reads the data files the pipeline wrote and renders the broadsheet. No framework. */
(() => {
  'use strict';

  const TOPICS = [
    { id: 'internal_politics', name: 'Internal politics' },
    { id: 'economics', name: 'Economy' },
    { id: 'foreign_policy', name: 'Foreign policy' },
    { id: 'defence_security', name: 'Defence and security' },
    { id: 'society', name: 'Society' },
    { id: 'other', name: 'Other' },
  ];
  const PER_TOPIC_IN_OVERVIEW = 4;
  const TOPIC_PAGE_CHUNK = 48;
  const STALE_HOURS = 12;
  // Where coverage comes from; the middle label is the country's own ("Vietnamese-language outlets abroad").
  function scopes(cid = country.value) {
    const c = index.countries.find((x) => x.id === cid) || index.countries[0];
    return [['domestic', 'domestic outlets'], ['abroad_local', c.abroad_label], ['international', 'international outlets']];
  }

  const $ = (sel) => document.querySelector(sel);
  const fmtDay = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' });
  const fmtTime = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

  // Build DOM with textContent only: headlines come from third-party feeds and are never treated as HTML.
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'style') el.setAttribute('style', v);
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) {
      if (kid == null || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(kid));
    }
    return el;
  }
  function safeUrl(u) {
    try { const x = new URL(u); return x.protocol === 'https:' || x.protocol === 'http:' ? x.href : '#'; } catch { return '#'; }
  }
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const topicName = (id) => (TOPICS.find((t) => t.id === id) || {}).name || id;
  const topicVar = (id) => `--tab: var(--t-${id})`;
  const fold = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/ł/g, 'l').replace(/ı/g, 'i');

  const index = window.ARGOS_INDEX;
  function getCountryName(id) {
    const c = (index && index.countries || []).find((x) => x.id === id);
    if (c) return c.name;
    const p = (typeof COMMON_PARTNERS !== 'undefined' ? COMMON_PARTNERS : []).find((x) => x.id === id);
    if (p) return p.name;
    return id ? id.charAt(0).toUpperCase() + id.slice(1) : '';
  }

  const country = $('#country'), countrySearch = $('#country-search'), countryMenu = $('#country-menu'), countryArrow = $('#country-arrow');
  const period = $('#period'), topic = $('#topic'), results = $('#results');
  let current = null;   // the loaded data file
  let openTopic = 'all';
  let openRegion = 'all';
  let deskSort = 'attention';
  let deskFilter = '';
  let openSubType = 'all';
  let movementFilter = 'all';
  let extra = {};   // extra stories revealed per topic in the overview ("Show more")
  const GLOBAL_VIEWS = new Set(['home', 'alerts', 'disasters', 'violence', 'relations']);

  const REGIONS = [
    'North America', 'Western Europe', 'Central & Southeast Europe', 'Eastern Europe',
    'South Caucasus', 'Middle East', 'Mediterranean', 'Central Asia', 'South Asia',
    'East Asia', 'Southeast Asia', 'Oceania', 'Sub-Saharan Africa', 'South America', 'Central America', 'Caribbean'
  ];
  const COUNTRY_REGION = {
    canada: 'North America', united_states: 'North America',
    belgium: 'Western Europe', denmark: 'Western Europe', finland: 'Western Europe', france: 'Western Europe', germany: 'Western Europe', ireland: 'Western Europe', italy: 'Western Europe',
    netherlands: 'Western Europe', norway: 'Western Europe', portugal: 'Western Europe', spain: 'Western Europe', sweden: 'Western Europe', switzerland: 'Western Europe', united_kingdom: 'Western Europe',
    austria: 'Central & Southeast Europe', bosnia: 'Central & Southeast Europe', czechia: 'Central & Southeast Europe', hungary: 'Central & Southeast Europe', kosovo: 'Central & Southeast Europe', poland: 'Central & Southeast Europe', serbia: 'Central & Southeast Europe', slovakia: 'Central & Southeast Europe',
    baltics: 'Eastern Europe', belarus: 'Eastern Europe', moldova: 'Eastern Europe', romania: 'Eastern Europe', russia: 'Eastern Europe', ukraine: 'Eastern Europe',
    armenia: 'South Caucasus', azerbaijan: 'South Caucasus', georgia: 'South Caucasus',
    iran: 'Middle East', iraq: 'Middle East', jordan: 'Middle East', qatar: 'Middle East', saudi_arabia: 'Middle East', syria: 'Middle East', united_arab_emirates: 'Middle East',
    algeria: 'Mediterranean', egypt: 'Mediterranean', greece: 'Mediterranean', israel: 'Mediterranean', lebanon: 'Mediterranean', morocco: 'Mediterranean', turkey: 'Mediterranean',
    kazakhstan: 'Central Asia', kyrgyzstan: 'Central Asia', uzbekistan: 'Central Asia',
    bangladesh: 'South Asia', india: 'South Asia', pakistan: 'South Asia', sri_lanka: 'South Asia',
    china: 'East Asia', japan: 'East Asia', north_korea: 'East Asia', south_korea: 'East Asia', taiwan: 'East Asia',
    cambodia: 'Southeast Asia', indonesia: 'Southeast Asia', laos: 'Southeast Asia', malaysia: 'Southeast Asia', myanmar: 'Southeast Asia',
    philippines: 'Southeast Asia', singapore: 'Southeast Asia', thailand: 'Southeast Asia', vietnam: 'Southeast Asia',
    australia: 'Oceania', pacific_islands: 'Oceania',
    dr_congo: 'Sub-Saharan Africa', east_africa: 'Sub-Saharan Africa', ethiopia: 'Sub-Saharan Africa', kenya: 'Sub-Saharan Africa', nigeria: 'Sub-Saharan Africa', south_africa: 'Sub-Saharan Africa', west_africa: 'Sub-Saharan Africa',
    argentina: 'South America', brazil: 'South America', chile: 'South America', colombia: 'South America', ecuador: 'South America', mexico: 'South America', peru: 'South America', venezuela: 'South America',
    central_america: 'Central America',
    caribbean: 'Caribbean',
  };
  const getRegion = (cid) => ((index && index.countries.find((x) => x.id === cid) || {}).region) || COUNTRY_REGION[cid] || 'Other';
  const prettyName = (cid) => ((index && index.countries.find((x) => x.id === cid) || {}).name) || cid.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());

  // ---------- data loading (script tags, so it works when the page is opened from a folder) ----------
  function load(file) {
    const key = file.replace(/\.json$/, '');
    window.ARGOS_DATA = window.ARGOS_DATA || {};
    if (window.ARGOS_DATA[key]) return Promise.resolve(window.ARGOS_DATA[key]);
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      const v = (window.ARGOS_INDEX && window.ARGOS_INDEX.generated_at) ? `?v=${encodeURIComponent(window.ARGOS_INDEX.generated_at)}` : '';
      s.src = `data/${key}.js${v}`;
      s.onload = () => (window.ARGOS_DATA[key] ? resolve(window.ARGOS_DATA[key]) : reject(new Error('empty')));
      s.onerror = () => reject(new Error('missing'));
      document.head.append(s);
    });
  }

  // ---------- form ----------
  function fillSelect(sel, options, value) {
    sel.replaceChildren(...options.map(([v, label]) => h('option', { value: v, text: label })));
    if (value != null && options.some(([v]) => v === value)) sel.value = value;
  }
  let monitorCountry = 'all';
  let monitorPeriod = '7d';

  const MONITOR_PERIODS = [
    ['24h', 'Past 24 hours'],
    ['7d', 'Past 7 days'],
  ];

  const periodCutoff = (per) => {
    const now = Date.now();
    if (per === '24h') return now - 24 * 3600 * 1000;
    if (per === '7d') return now - 7 * 86400 * 1000;
    if (per === '14d') return now - 14 * 86400 * 1000;
    if (per === '30d') return now - 30 * 86400 * 1000;
    return 0;
  };

  function periodPicker(currentVal, onChange) {
    return h('div', { class: 'monitor-filter' },
      h('label', { for: 'mon-period-sel', text: 'Time Window:' }),
      h('select', {
        id: 'mon-period-sel',
        onchange: (e) => onChange(e.target.value)
      },
        ...MONITOR_PERIODS.map(([v, label]) =>
          h('option', { value: v, text: label, selected: v === currentVal }))
      )
    );
  }

  function countryPicker(currentVal, onChange) {
    const groups = new Map(REGIONS.map((r) => [r, []]));
    for (const c of index.countries) {
      const r = getRegion(c.id);
      if (!groups.has(r)) groups.set(r, []);
      groups.get(r).push(c);
    }
    return h('div', { class: 'monitor-filter notranslate', translate: 'no' },
      h('label', { for: 'mon-country-sel', text: 'Filter by Country:' }),
      h('select', {
        id: 'mon-country-sel',
        translate: 'no',
        class: 'notranslate',
        onchange: (e) => onChange(e.target.value)
      },
        h('option', { value: 'all', text: 'All Countries', selected: currentVal === 'all', class: 'notranslate', translate: 'no' }),
        ...[...groups.entries()].filter(([, list]) => list.length).map(([reg, list]) =>
          h('optgroup', { label: reg, class: 'notranslate', translate: 'no' }, ...list.map((c) => h('option', { value: c.id, text: c.name, selected: c.id === currentVal, class: 'notranslate', translate: 'no' }))))
      )
    );
  }

  function fillCountrySelect(value) {
    const groups = new Map(REGIONS.map((r) => [r, []]));
    for (const c of index.countries) {
      const r = getRegion(c.id);
      if (!groups.has(r)) groups.set(r, []);
      groups.get(r).push(c);
    }
    country.replaceChildren(
      ...[...groups.entries()].filter(([, list]) => list.length).map(([reg, list]) =>
        h('optgroup', { label: reg, class: 'notranslate', translate: 'no' }, ...list.map((c) => h('option', { value: c.id, text: c.name, class: 'notranslate', translate: 'no' }))))
    );
    if (value != null && index.countries.some((c) => c.id === value)) country.value = value;
    else if (index.countries.length) country.value = index.countries[0].id;
    syncCountryInput(country.value);
  }

  function syncCountryInput(cid) {
    if (!countrySearch) return;
    if (activeTab === 'country' && cid && cid !== 'all') {
      const name = getCountryName(cid);
      if (name) countrySearch.value = name;
    } else {
      countrySearch.value = '';
    }
  }

  function setupCountryCombobox() {
    if (!countrySearch || !countryMenu) return;

    let highlightedIndex = -1;
    let visibleItems = [];

    function renderMenu(query = '') {
      const q = fold(query.trim());
      visibleItems = [];
      countryMenu.replaceChildren();

      if (!q) {
        // Group by Region
        const groups = new Map(REGIONS.map((r) => [r, []]));
        for (const c of index.countries) {
          const r = getRegion(c.id);
          if (!groups.has(r)) groups.set(r, []);
          groups.get(r).push(c);
        }
        for (const [reg, list] of groups.entries()) {
          if (!list.length) continue;
          countryMenu.append(h('div', { class: 'combobox-group-label', text: reg }));
          for (const c of list) {
            const isSel = c.id === country.value && activeTab === 'country';
            const item = h('div', {
              class: 'combobox-item' + (isSel ? ' selected' : ''),
              role: 'option',
              'data-id': c.id,
              'data-name': c.name,
              onclick: () => selectCountry(c.id, c.name),
            },
              h('span', { class: 'c-name', text: c.name }),
              h('span', { class: 'c-region', text: reg })
            );
            countryMenu.append(item);
            visibleItems.push({ el: item, id: c.id, name: c.name });
          }
        }
      } else {
        // Filter matching countries by name, id, region, or mention aliases
        const matches = index.countries.filter((c) => {
          if (fold(c.name).includes(q) || fold(c.id).includes(q) || fold(getRegion(c.id)).includes(q)) return true;
          return (c.mentions || []).some((m) => fold(m).includes(q));
        });

        if (!matches.length) {
          countryMenu.append(h('div', { class: 'combobox-empty', text: `No countries matching "${query}"` }));
        } else {
          for (const c of matches) {
            const isSel = c.id === country.value && activeTab === 'country';
            const reg = getRegion(c.id);
            const item = h('div', {
              class: 'combobox-item' + (isSel ? ' selected' : ''),
              role: 'option',
              'data-id': c.id,
              'data-name': c.name,
              onclick: () => selectCountry(c.id, c.name),
            },
              h('span', { class: 'c-name', text: c.name }),
              h('span', { class: 'c-region', text: reg })
            );
            countryMenu.append(item);
            visibleItems.push({ el: item, id: c.id, name: c.name });
          }
        }
      }

      highlightedIndex = visibleItems.findIndex((it) => it.id === country.value);
      if (highlightedIndex === -1 && visibleItems.length) highlightedIndex = 0;
      updateHighlight();
    }

    function updateHighlight() {
      visibleItems.forEach((it, idx) => {
        it.el.classList.toggle('highlighted', idx === highlightedIndex);
        if (idx === highlightedIndex) {
          it.el.scrollIntoView({ block: 'nearest' });
        }
      });
    }

    function selectCountry(cid, cname) {
      country.value = cid;
      countrySearch.value = cname;
      closeMenu();
      openCountry(cid);
    }

    function openMenu() {
      renderMenu(countrySearch.value === getCountryName(country.value) ? '' : countrySearch.value);
      countryMenu.hidden = false;
      countrySearch.setAttribute('aria-expanded', 'true');
    }

    function closeMenu() {
      countryMenu.hidden = true;
      countrySearch.setAttribute('aria-expanded', 'false');
      highlightedIndex = -1;
    }

    countrySearch.addEventListener('focus', () => {
      countrySearch.select();
      openMenu();
    });

    countrySearch.addEventListener('input', () => {
      openMenu();
      renderMenu(countrySearch.value);
    });

    countrySearch.addEventListener('keydown', (e) => {
      if (countryMenu.hidden) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter') {
          e.preventDefault();
          openMenu();
          return;
        }
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (visibleItems.length) {
          highlightedIndex = (highlightedIndex + 1) % visibleItems.length;
          updateHighlight();
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (visibleItems.length) {
          highlightedIndex = (highlightedIndex - 1 + visibleItems.length) % visibleItems.length;
          updateHighlight();
        }
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (highlightedIndex >= 0 && visibleItems[highlightedIndex]) {
          selectCountry(visibleItems[highlightedIndex].id, visibleItems[highlightedIndex].name);
        } else if (visibleItems.length === 1) {
          selectCountry(visibleItems[0].id, visibleItems[0].name);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        syncCountryInput(country.value);
        closeMenu();
        countrySearch.blur();
      }
    });

    if (countryArrow) {
      countryArrow.addEventListener('click', (e) => {
        e.preventDefault();
        if (countryMenu.hidden) {
          countrySearch.focus();
          openMenu();
        } else {
          closeMenu();
        }
      });
    }

    document.addEventListener('click', (e) => {
      if (!e.target.closest('.country-field')) {
        if (!countryMenu.hidden) {
          closeMenu();
          syncCountryInput(country.value);
        }
      }
    });
  }
  // Desktop: horizontal tab strip. Mobile (<=45.99rem): native rolldown select so no menu ever scrolls sideways.
  function tabBar(items, activeId, onSelect, labelText, ariaLabel) {
    return h('div', { class: 'tab-bar' },
      h('ul', { class: 'tabs', role: 'list', 'aria-label': ariaLabel || labelText },
        items.map(([id, label, n, style]) =>
          h('li', null, h('button', {
            type: 'button',
            class: 'tab',
            style: style || '',
            'aria-pressed': String(activeId === id),
            onclick: () => onSelect(id),
          }, label, n != null && h('span', { class: 'n', text: String(n) }))))),
      h('label', { class: 'tab-rolldown' },
        h('span', { text: labelText }),
        h('select', {
          'aria-label': ariaLabel || labelText,
          onchange: (e) => onSelect(e.target.value),
        }, items.map(([id, label, n]) =>
          h('option', {
            value: id,
            selected: activeId === id,
            text: n != null ? `${label} (${n})` : label,
          })))));
  }

  function regionTabs(countFn, onChoose) {
    const active = REGIONS.filter((r) => countFn(r) > 0);
    if (active.length < 2) return null;
    const items = [['all', 'All regions', countFn('all')], ...active.map((r) => [r, r, countFn(r)])];
    return tabBar(items, openRegion, (id) => { openRegion = id; onChoose(); }, 'Region', 'Filter by region');
  }
  const ALL_PERIODS = [
    ['24h', 'Last 24 hours'],
    ['7d', 'Last 7 days'],
  ];

  function fillPeriods() {
    const c = index.countries.find((x) => x.id === country.value);
    const available = (c && c.periods && c.periods.length)
      ? c.periods.map((p) => [p.id, p.label])
      : ALL_PERIODS;
    fillSelect(period, available, period.value || (available[0] ? available[0][0] : '7d'));
    period.disabled = topic.disabled = activeTab !== 'country';
  }
  function fillTopics(value) {
    fillSelect(topic, [['all', 'All topics'], ...TOPICS.map((t) => [t.id, t.name])], value);
  }

  let lastCountry = index && index.countries[0] ? index.countries[0].id : '';
  let fallbackNotice = null;
  let activeTab = 'home';
  const hashFor = (t) => {
    const qPart = $('#q').value.trim() ? `/${encodeURIComponent($('#q').value.trim())}` : '';
    if (activeTab === 'home') return `#home${qPart ? '//' + qPart.slice(1) : ''}`;
    if (activeTab === 'relations') return `#relations/${selectedCountries.join(',')}/${relPeriod}`;
    if (activeTab === 'alerts' || activeTab === 'disasters' || activeTab === 'violence') {
      const c = monitorCountry !== 'all' ? monitorCountry : 'all';
      return `#${activeTab}/${c}/${monitorPeriod}${qPart}`;
    }
    return `#${country.value}/${period.value}/${t}${qPart}`;
  };
  function readHash() {
    const [c, p, t, q] = location.hash.replace(/^#/, '').split('/');
    if (c === 'relations') {
      activeTab = 'relations';
      country.value = 'all';
      if (p) {
        if (p.includes(',')) {
          selectedCountries = p.split(',').filter(Boolean);
          if (t) relPeriod = t;
        } else {
          selectedCountries = [p];
          if (t && t !== '30d' && t !== '14d' && t !== '7d') {
            selectedCountries.push(t);
            if (q) relPeriod = q;
          } else if (t) {
            relPeriod = t;
          }
        }
      }
      if (!selectedCountries.length) selectedCountries = ['cambodia', 'vietnam'];
    } else if (c === 'alerts' || c === 'disasters' || c === 'violence') {
      activeTab = c;
      monitorCountry = (p && index.countries.some((x) => x.id === p)) ? p : 'all';
      if (t && ['24h', '7d', '14d', '30d'].includes(t)) {
        monitorPeriod = (t === '14d' || t === '30d') ? '7d' : t;
        try { $('#q').value = q ? decodeURIComponent(q) : ''; } catch {}
      } else {
        try { $('#q').value = t ? decodeURIComponent(t) : ''; } catch {}
      }
    } else if (c === 'home' || !c) {
      activeTab = 'home';
      country.value = 'all';
      syncCountryInput('all');
      try { $('#q').value = p ? decodeURIComponent(p) : ''; } catch {}
    } else {
      activeTab = 'country';
      const cid = c === 'country' ? (lastCountry || index.countries[0].id) : (index.countries.some((x) => x.id === c) ? c : index.countries[0].id);
      country.value = cid;
      lastCountry = cid;
      syncCountryInput(cid);
      try { $('#q').value = q ? decodeURIComponent(q) : ''; } catch {}
    }
    fillPeriods();
    if (activeTab === 'country') {
      if (p && [...period.options].some((o) => o.value === p)) period.value = p;
      if (t && (t === 'all' || TOPICS.some((x) => x.id === t))) topic.value = t;
    }
  }

  // ---------- English, translated by the reader's own browser (decision D11) ----------
  function setHash(value) {
    if (location.protocol === 'file:') return;
    try { history.replaceState(null, '', value); } catch { /* not allowed here: ignore */ }
  }

  function setShowOriginal(on) {
    document.body.classList.toggle('show-orig', on);
    try { localStorage.setItem('argos.showOriginal', on ? '1' : '0'); } catch { /* storage not available: ignore */ }
  }
  try { if (localStorage.getItem('argos.showOriginal') === '1') document.body.classList.add('show-orig'); } catch { /* ignore */ }

  const T = { lang: 'en', state: 'checking', translators: new Map(), cache: new Map(), byText: new Map(), queue: [], running: false };
  const withTimeout = (p, ms) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error('timeout')), ms))]);

  function track(el, text, lang, origEl) {
    if (!lang || lang === 'en') return;
    T.queue.push({ el, text, lang, origEl });
  }
  async function getTranslator(lang, button) {
    if (T.translators.has(lang)) return T.translators.get(lang);
    const tr = await Translator.create({
      sourceLanguage: lang, targetLanguage: 'en',
      monitor(m) { m.addEventListener('downloadprogress', (e) => { if (button) button.textContent = `Downloading English… ${Math.round(e.loaded * 100)}%`; }); },
    });
    T.translators.set(lang, tr);
    return tr;
  }
  async function translatePending() {
    if (T.state !== 'ready' || T.running) return;
    T.running = true;
    while (T.queue.length) {
      const it = T.queue.shift();
      if (!it.el.isConnected) continue;
      try {
        const key = `${it.lang}:${it.text}`;
        let en = T.cache.get(key);
        if (en == null) {
          const tr = await getTranslator(it.lang);
          en = await tr.translate(it.text);
          T.cache.set(key, en);
        }
        T.byText.set(it.text, en);
        it.el.textContent = en;
        it.el.lang = 'en';
        if (en.trim().toLowerCase() !== it.text.trim().toLowerCase()) {
          it.origEl.textContent = it.text;
          it.origEl.lang = it.lang;
          it.origEl.hidden = false;
        }
      } catch { /* keep the original text as it is */ }
    }
    // Pre-translate unrendered lead headlines in the current view so English search finds them too.
    const hm = window.ARGOS_HOME;
    const bgPool = activeTab === 'home' && hm
      ? [...(hm.most_reported || []), ...(hm.growing || [])]
      : (current && current.stories) || [];
    if (bgPool.length) {
      let added = 0;
      for (const s of bgPool) {
        const lang = s.headline && s.headline.language;
        const text = s.headline && s.headline.title;
        if (!lang || lang === 'en' || !text || T.byText.has(text)) continue;
        try {
          const key = `${lang}:${text}`;
          let en = T.cache.get(key);
          if (en == null) {
            const tr = await getTranslator(lang);
            en = await tr.translate(text);
            T.cache.set(key, en);
          }
          T.byText.set(text, en);
          added++;
        } catch { break; }
      }
      if (added && ($('#q').value || '').trim()) {
        T.running = false;
        activeTab === 'home' ? renderHome() : render(false);
        return;
      }
    }
    T.running = false;
  }
  async function startTranslator(button) {
    const langs = T.lang === 'multi' ? [...new Set(T.queue.map((q) => q.lang))] : [T.lang];
    for (const l of langs) await getTranslator(l, button);
    T.state = 'ready';
  }
  function useLanguage(lang) {
    T.lang = lang; T.state = 'checking';
    initTranslator().then(() => { paintTranslationBar(); translatePending(); });
  }
  async function initTranslator() {
    if (T.lang === 'en') { T.state = 'none'; return; }
    if (typeof Translator === 'undefined') { T.state = 'none'; return; }
    try {
      const probe = T.lang === 'multi' ? 'vi' : T.lang;
      const a = await withTimeout(Translator.availability({ sourceLanguage: probe, targetLanguage: 'en' }), 4000);
      if (a === 'available') { T.state = 'ready'; }
      else if (a === 'downloadable' || a === 'downloading') T.state = 'offer';
      else T.state = 'none';
    } catch { T.state = 'none'; }
  }
  function paintTranslationBar() {
    const bar = $('#trans');
    if (!bar) return;
    if (T.lang === 'en') {
      bar.replaceChildren();
      return;
    }
    if (T.state === 'ready') {
      const on = document.body.classList.contains('show-orig');
      const toggle = h('button', { type: 'button', class: 'more', 'aria-pressed': String(on), text: on ? 'Hide original text' : 'Show original text' });
      toggle.addEventListener('click', () => { setShowOriginal(!document.body.classList.contains('show-orig')); paintTranslationBar(); });
      bar.replaceChildren(
        h('p', { class: 'notice quiet', text: 'English lines are machine translations made by your browser and can be wrong. The original text is hidden; every headline links to the original article.' }),
        toggle);
    } else if (T.state === 'offer') {
      const btn = h('button', { type: 'button', class: 'more offer', text: 'Translate headlines to English (one-time download of a small language pack)' });
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        try { await startTranslator(btn); } catch { T.state = 'none'; }
        paintTranslationBar();
        translatePending();
      });
      bar.replaceChildren(btn);
    } else {
      bar.replaceChildren();
    }
  }

  // ---------- rendering ----------
  function trend(s) {
    if (s.last_24h == null || s.articles < 2) return null;
    if (s.last_24h === s.articles) return ['New', 'indigo', 'Every article is from the last 24 hours.'];
    if (s.last_24h >= 3 && s.last_24h * 2 >= s.articles) return ['Growing', 'indigo', 'Half or more of the articles are from the last 24 hours.'];
    if (s.last_24h === 0) return ['Quiet', 'indigo', 'No new articles in the last 24 hours.'];
    return null;
  }

  function openCountry(cid) {
    if (cid === 'home') {
      activeTab = 'home';
      syncCountryInput('all');
    } else if (cid === 'alerts' || cid === 'disasters' || cid === 'violence') {
      activeTab = cid;
      syncCountryInput('all');
    } else if (cid === 'relations') {
      activeTab = 'relations';
      syncCountryInput('all');
    } else {
      activeTab = 'country';
      if (cid && index.countries.some((x) => x.id === cid)) {
        country.value = cid;
        lastCountry = cid;
        syncCountryInput(cid);
      }
    }
    fillPeriods();
    movementFilter = 'all';
    research();
    scrollTo({ top: 0, behavior: 'smooth' });
  }

  function story(s, opts) {
    const sc = scopes(s.country || country.value);
    const present = sc.filter(([id]) => s.by_scope[id]);
    const single = present.length === 1 ? present[0][1] : '';
    const outlets = plural(s.independent_sources, 'independent outlet', 'independent outlets');
    const clip = h('article', { class: 'clip' + (opts.lead ? ' lead' : ''), style: `--i:${opts.i}` });

    const hasEn = Boolean(s.headline && s.headline.en_title);
    const displayTitle = hasEn ? s.headline.en_title : s.headline.title;
    const headLink = h('a', { href: safeUrl(s.headline.url), target: '_blank', rel: 'noopener noreferrer', lang: hasEn ? 'en' : s.headline.language, text: displayTitle });
    const headOrig = h('p', { class: 'orig', hidden: !hasEn, title: 'Original headline', text: hasEn ? s.headline.title : '' });
    if (!hasEn) {
      track(headLink, s.headline.title, s.headline.language, headOrig);
    }
    const shown = opts.lead ? s.excerpts : s.excerpts.slice(0, 1);

    clip.append(...[
      h('div', null,
        h('h3', { class: 'headline' }, headLink),
        headOrig,
      ),
      shown.length > 0 && h('div', { class: 'strips' }, shown.map((x) => {
        const qLang = s.headline.language !== 'en' ? s.headline.language : (T.lang !== 'multi' ? T.lang : 'en');
        const main = h('p', { lang: qLang, text: x.text });
        const orig = h('p', { class: 'orig', hidden: true, title: 'Original quote' });
        track(main, x.text, qLang, orig);
        return h('blockquote', { class: 'strip' }, main, orig,
          x.source !== s.headline.source && h('footer', null, h('a', { class: 'stamp indigo', href: safeUrl(x.url), target: '_blank', rel: 'noopener noreferrer', text: x.source })));
      })),
      h('div', { class: 'slipline' },
        s.country_name && h('button', { type: 'button', class: 'stamp country-tag', title: `Open ${s.country_name} monitor`, text: s.country_name, onclick: () => openCountry(s.country) }),
        s.disaster_type && h('span', { class: 'stamp teal', text: s.disaster_type }),
        s.violence_type && h('span', { class: 'stamp red', text: s.violence_type }),
        s.religious_traditions && s.religious_traditions.length > 0 && h('span', {
          class: 'stamp stamp-sectarian',
          title: `Religious & Sectarian Sensitivity: ${s.religious_traditions.join(', ')}`,
          text: `REL SENSITIVITY: ${s.religious_traditions.join(' / ').toUpperCase()}`
        }),
        h('span', { text: `${s.headline.source}, ${fmtDay.format(new Date(s.last_seen))} · ${outlets}` }),
        s.evidence === 'OFFICIAL' && h('span', { class: 'stamp red', title: 'A government or Party outlet is among the sources.', text: 'Official' }),
        (() => {
          if (!s.perspectives) return null;
          const sh = s.perspectives.state_share;
          if (sh >= 0.7) return h('span', { class: 'stamp red', title: `${Math.round(sh * 100)}% of corroborating coverage is from state-controlled or pro-government outlets`, text: 'State-Dominated' });
          if (sh >= 0.35) return h('span', { class: 'stamp orange', title: 'Mixed reporting between state and independent outlets', text: 'State & Indep' });
          const nAlign = Object.keys(s.perspectives.alignment || {}).length;
          const nBias = Object.keys(s.perspectives.bias || {}).length;
          if (nAlign > 1 || nBias > 1) return h('span', { class: 'stamp indigo', title: 'Coverage spans multiple editorial perspectives and affiliations', text: 'Cross-Spectrum' });
          if (s.independent_sources >= 2) return h('span', { class: 'stamp teal', title: 'Predominantly reported by independent press', text: 'Independent' });
          return null;
        })(),
        (() => {
          if (!s.delta) return null;
          const badges = [];
          if (s.delta.state === 'new') {
            badges.push(h('span', { class: 'stamp stamp-new', title: 'Fresh emergence: no recorded coverage in prior reference window', text: 'NEW' }));
          } else if (s.delta.state === 'surging') {
            const netStr = s.delta.net > 0 ? `+${s.delta.net}` : String(s.delta.net);
            badges.push(h('span', { class: 'stamp stamp-surge', title: `Surging coverage: ${s.delta.curr} articles vs ${s.delta.prev} in prior window (${s.delta.ratio}x velocity)`, text: `SURGE ${netStr}` }));
          } else if (s.delta.state === 'cooling') {
            badges.push(h('span', { class: 'stamp stamp-cooling', title: `Cooling coverage: ${s.delta.curr} articles vs ${s.delta.prev} in prior window`, text: 'COOLING' }));
          }
          if (s.delta.scope_shift === 'international_pickup') {
            badges.push(h('span', { class: 'stamp stamp-pickup', title: 'International wire pickup of domestic reporting', text: 'INTL PICKUP' }));
          } else if (s.delta.scope_shift === 'diaspora_pickup') {
            badges.push(h('span', { class: 'stamp stamp-pickup', title: 'Diaspora / foreign-language pickup of domestic reporting', text: 'DIASPORA PICKUP' }));
          }
          if (s.delta.state_surge) {
            badges.push(h('span', { class: 'stamp red', title: `Official state narrative surge: state-affiliated share increased by ${Math.round((s.delta.state_share_curr - s.delta.state_share_prev) * 100)}%`, text: 'STATE SURGE' }));
          }
          return badges.length ? badges : null;
        })(),
        (!s.delta || s.delta.state === 'steady' || s.delta.state === 'trace') && trend(s) && trend(s)[0] !== 'Quiet' && h('span', { class: 'stamp indigo', title: trend(s)[2], text: trend(s)[0] }),
      ),
    ].filter(Boolean));

    const rest = s.sources || [];
    if (rest.length) {
      const lateItems = [];
      const max = s.per_day && s.per_day.length ? Math.max(...s.per_day.map((d) => d[1])) : 1;
      const bands = [
        ['> 93% · Direct match', rest.filter((r) => (r.sim ?? 100) >= 93)],
        ['85–93% · Close coverage', rest.filter((r) => (r.sim ?? 100) >= 85 && (r.sim ?? 100) < 93)],
        ['75–85% · Broader context', rest.filter((r) => (r.sim ?? 100) < 85)],
      ].filter(([, list]) => list.length > 0);
      const renderItem = (r) => {
        const a = h('a', { class: 't', href: safeUrl(r.url), target: '_blank', rel: 'noopener noreferrer', lang: r.language, text: r.title });
        const o = h('span', { class: 'orig', hidden: true, title: 'Original headline' });
        lateItems.push([a, r.title, r.language, o]);
        const alignLabel = {
          state_controlled: 'State',
          pro_government: 'Pro-Gov',
          public_broadcaster: 'Public',
          independent: 'Indep',
          opposition: 'Opposition',
        }[r.alignment];
        const biasLabel = {
          left: 'Left',
          'center-left': 'Center-Left',
          center: 'Center',
          'center-right': 'Center-Right',
          right: 'Right',
          state_aligned: 'State-aligned',
        }[r.bias];
        const ratingTag = [alignLabel, biasLabel].filter(Boolean).join(' · ');
        return h('li', null, a, o,
          h('span', { class: 'meta' },
            h('span', { class: 'stamp indigo', text: r.source }),
            ratingTag && h('span', { class: 'stamp typed', title: `Affiliation: ${r.alignment || 'unrated'} | Bias: ${r.bias || 'unrated'} | Factuality: ${r.factuality || 'unrated'}`, text: ratingTag }),
            r.sim != null && h('span', { class: 'typed', text: `${r.sim}%` }),
            r.published && h('span', { text: fmtTime.format(new Date(r.published)) }),
            r.copy && h('span', { text: 'reprint, counted once' })));
      };
      const details = h('details', null,
        h('summary', { text: `All ${s.articles} articles` }),
        present.length > 1 && h('div', { class: 'cover', 'aria-label': 'Where the coverage comes from' },
          present.map(([id, label]) => h('span', null, h('b', { text: String(s.by_scope[id]) }), ` ${s.by_scope[id] === 1 ? 'article' : 'articles'} from ${label}`))),
        s.perspectives && (Object.keys(s.perspectives.alignment || {}).length > 0 || Object.keys(s.perspectives.bias || {}).length > 0) && h('div', { class: 'cover', 'aria-label': 'Perspective breakdown' },
          h('span', null, h('b', { text: 'Perspectives: ' }),
            [
              ...Object.entries(s.perspectives.alignment || {}).map(([k, v]) => `${v} ${k.replace(/_/g, ' ')}`),
              ...Object.entries(s.perspectives.bias || {}).map(([k, v]) => `${v} ${k.replace(/_/g, ' ')} leaning`)
            ].join(' · '))),
        s.first && s.articles > 2 && h('div', { class: 'timeline' },
          h('span', { class: 'bars', 'aria-hidden': 'true' }, s.per_day.map(([day, n]) =>
            h('i', { style: `height:${Math.max(15, Math.round(100 * n / max))}%`, title: `${fmtDay.format(new Date(day))}: ${plural(n, 'article', 'articles')}` }))),
          h('span', { text: `First seen in ${s.first.source}, ${fmtTime.format(new Date(s.first.at))}.` })),
        (s.related || []).length > 0 && h('p', { class: 'byline related' }, 'May be the same event: ', s.related.map((r) =>
          h('span', null, h('a', { href: safeUrl(r.url), target: '_blank', rel: 'noopener noreferrer', text: r.title }), ` (${plural(r.articles, 'article', 'articles')}, ${r.source}) `))),
        ...bands.map(([label, list]) => h('div', { class: 'sim-band' },
          h('p', { class: 'band-head' }, h('b', { text: label }), ` (${list.length})`),
          h('ul', { class: 'sources' }, list.map(renderItem)))),
        s.articles > rest.length && h('p', { class: 'byline', text: `Showing ${rest.length} of ${s.articles}.` }),
      );
      details.addEventListener('toggle', () => {
        if (!details.open) return;
        lateItems.splice(0).forEach((it) => track(...it));
        translatePending();
      });
      clip.append(details);
    }
    return clip;
  }

  function drawer(id, stories, total, limit) {
    const shown = limit ? stories.slice(0, limit) : stories;
    const countText = shown.length >= total ? `${total} stories` : `Top ${shown.length} of ${total} stories`;
    const sec = h('section', { class: 'drawer', style: topicVar(id), 'aria-labelledby': `d-${id}` },
      h('div', { class: 'drawer-head' },
        h('h2', { id: `d-${id}`, text: topicName(id) }),
        h('span', { class: 'count', text: countText })),
      h('div', { class: 'grid' }, shown.map((s, i) => story(s, { lead: i === 0, i }))),
    );
    if (limit && stories.length > limit) {
      if (openTopic === 'all') {
        sec.append(
          h('button', { type: 'button', class: 'more', onclick: () => { extra[id] = (extra[id] || 0) + 8; render(false); }, text: `Show ${Math.min(8, stories.length - limit)} more` }),
          h('button', { type: 'button', class: 'more', onclick: () => choose(id), text: `Open all ${topicName(id)} (${total})` })
        );
      } else {
        sec.append(
          h('button', { type: 'button', class: 'more', onclick: () => { extra[id] = (extra[id] || 0) + TOPIC_PAGE_CHUNK; render(false); }, text: `Show ${Math.min(TOPIC_PAGE_CHUNK, stories.length - limit)} more` }),
          h('button', { type: 'button', class: 'more', onclick: () => { extra[id + '_all'] = true; render(false); }, text: `Show all ${stories.length} stories` })
        );
      }
    }
    return sec;
  }

  const trText = (t) => (t ? `${t} ${T.byText.get(t) || ''}` : '');
  const storyText = (s) => fold([
    s.country_name || '',
    s.headline && s.headline.en_title ? s.headline.en_title : '',
    trText(s.headline.title),
    ...(s.sources || []).map((r) => `${trText(r.title)} ${r.source}`),
    ...(s.excerpts || []).map((x) => trText(x.text)),
  ].join(' '));
  const matchStory = (s, q) => storyText(s).includes(fold(q));

  function trends() {
    const tr = (window.ARGOS_TRENDS && (window.ARGOS_TRENDS.countries || (window.ARGOS_TRENDS.trends || {}).countries) || {})[country.value];
    if (!tr || !tr.length) return null;
    const cLang = (index.countries.find((c) => c.id === country.value) || {}).language || 'en';
    return h('section', { class: 'alerts', 'aria-label': 'Trending searches' },
      h('h2', { text: 'Trending searches' }),
      h('ul', { class: 'trend-list' }, tr.map((x) => {
        const n = current.stories.filter((s) => matchStory(s, x.term)).length;
        const termEl = h('span', { class: 'term', lang: cLang, text: x.term });
        const origEl = h('span', { class: 'orig', hidden: true });
        track(termEl, x.term, cLang, origEl);
        return h('li', null,
          termEl, origEl,
          x.traffic && h('span', { class: 'meta', text: x.traffic }),
          n > 0 && h('button', { type: 'button', class: 'desk-link', text: `${plural(n, 'story', 'stories')} →`,
            onclick: () => { $('#q').value = x.term; setHash(hashFor(openTopic)); render(false); results.scrollIntoView({ block: 'start' }); } }));
      })),
      h('p', { class: 'byline', text: 'Google Trends right now.' }));
  }

  function reddit() {
    const r = (window.ARGOS_REDDIT && (window.ARGOS_REDDIT.countries || (window.ARGOS_REDDIT.reddit || {}).countries) || {})[country.value];
    if (!r || !r.posts.length) return null;
    const cLang = (index.countries.find((c) => c.id === country.value) || {}).language || 'en';
    return h('section', { class: 'alerts', 'aria-label': 'On Reddit' },
      h('h2', { text: 'On Reddit today' }),
      h('ul', null, r.posts.map((x) => {
        const a = h('a', { href: safeUrl(x.url), target: '_blank', rel: 'noopener noreferrer', lang: cLang, text: x.title });
        const origEl = h('span', { class: 'orig', hidden: true });
        track(a, x.title, cLang, origEl);
        return h('li', null,
          x.sub && h('span', { class: 'stamp indigo', text: `r/${x.sub}` }),
          x.tag && h('span', { class: 'stamp', text: x.tag }),
          a, origEl);
      })),
      h('p', { class: 'byline', text: `Desk-relevant posts across ${r.subreddit}. Unverified.` }));
  }

  function social() {
    const sData = (window.ARGOS_SOCIAL && (window.ARGOS_SOCIAL.countries || (window.ARGOS_SOCIAL.social || {}).countries) || {})[country.value];
    if (!sData || !sData.length) return null;
    const cLang = (index.countries.find((c) => c.id === country.value) || {}).language || 'en';
    return h('section', { class: 'alerts', 'aria-label': 'Telegram & Bluesky Signals' },
      h('h2', { text: 'Telegram & Bluesky signals' }),
      h('ul', null, sData.map((x) => {
        const a = h('a', { href: safeUrl(x.url), target: '_blank', rel: 'noopener noreferrer', lang: cLang, text: x.text });
        const origEl = h('span', { class: 'orig', hidden: true });
        track(a, x.text, cLang, origEl);
        const platTag = x.platform === 'telegram' ? 'TG' : 'BSKY';
        return h('li', null,
          h('span', { class: 'meta' },
            h('span', { class: 'stamp ' + (x.platform === 'telegram' ? 'indigo' : 'teal'), text: `[${platTag}: ${x.author}]` }),
            x.published && h('span', { text: fmtTime.format(new Date(x.published)) })
          ),
          a, origEl);
      })),
      h('p', { class: 'byline', text: 'Real-time open channels & verified accounts. Unverified desk signals.' }));
  }

  const watched = () => { try { return JSON.parse(localStorage.getItem('argos.watch') || '[]'); } catch { return []; } };
  function setWatched(list) {
    try { localStorage.setItem('argos.watch', JSON.stringify(list)); } catch { /* storage not available: ignore */ }
    activeTab === 'home' ? renderHome() : render(false);
  }
  function watchbar(q, pool = current ? current.stories : []) {
    const list = watched();
    if (!list.length && !q) return null;
    return h('div', { class: 'watch' },
      h('span', { class: 'meta', text: 'Watching' }),
      list.map((w) => h('span', { class: 'chip' },
        h('button', { type: 'button', class: 'more', title: 'Show these stories',
          text: `${w} (${pool.filter((s) => matchStory(s, w)).length})`,
          onclick: () => { $('#q').value = w; setHash(hashFor(openTopic)); activeTab === 'home' ? renderHome() : render(false); } }),
        h('button', { type: 'button', class: 'x', 'aria-label': `Stop watching ${w}`, text: '×', onclick: () => setWatched(list.filter((x) => x !== w)) }))),
      q && !list.includes(q) && h('button', { type: 'button', class: 'more', text: `Watch "${q}"`, onclick: () => setWatched([...list, q]) }));
  }

  const getCrisis = () => { const raw = window.ARGOS_CRISIS; return raw && (raw.countries ? raw : raw.crisis); };
  const isHotAlert = (i) => /^(Red|Orange|Warning|Alert)$/.test(i.level || '') || /Level [34]/.test(i.title) || /^(GDELT Live Event|ACLED)$/.test(i.kind || '');
  function allCrisisAlerts() {
    const c = getCrisis();
    const out = [];
    if (c && c.countries) {
      for (const [cid, list] of Object.entries(c.countries)) {
        const cname = prettyName(cid);
        const region = getRegion(cid);
        for (const item of list) out.push({ ...item, cid, cname, region });
      }
    }
    return out.sort((a, b) => isHotAlert(b) - isHotAlert(a));
  }

  function alerts() {
    const c = getCrisis();
    if (!c) return null;
    const items = c.countries[country.value] || [];
    if (!items.length) return null;
    return h('section', { class: 'alerts side-alert', 'aria-label': 'Official alerts' },
      h('h2', { text: plural(items.length, 'Official alert', 'Official alerts') }),
      h('ul', null, items.map((item) => h('li', null,
        h('span', { class: 'stamp ' + (isHotAlert(item) ? 'red' : 'indigo'), text: item.kind }),
        h('a', { href: safeUrl(item.url), target: '_blank', rel: 'noopener noreferrer', text: item.title }),
        item.summary && h('p', { class: 'byline', text: item.summary })))));
  }

  function renderAlerts() {
    const c = getCrisis();
    const filterCountry = monitorCountry !== 'all' ? monitorCountry : null;
    const cutoff = periodCutoff(monitorPeriod);
    const all = allCrisisAlerts().filter((i) => {
      if (filterCountry && i.cid !== filterCountry) return false;
      if (cutoff && (!i.date || new Date(i.date).getTime() < cutoff)) return false;
      return true;
    });
    // Organised by recency
    all.sort((a, b) => new Date(b.date || 0).getTime() - new Date(a.date || 0).getTime());
    const countryName = filterCountry ? prettyName(filterCountry) : null;
    const periodLabel = (MONITOR_PERIODS.find(([v]) => v === monitorPeriod) || [])[1] || 'Past 7 days';
    const bar = h('div', { class: 'monitor-bar' },
      h('div', { class: 'monitor-filters' },
        countryPicker(monitorCountry, (val) => {
          monitorCountry = val;
          setHash(hashFor('all'));
          renderAlerts();
        }),
        periodPicker(monitorPeriod, (val) => {
          monitorPeriod = val;
          setHash(hashFor('all'));
          renderAlerts();
        })
      ),
      filterCountry
        ? h('button', { type: 'button', class: 'desk-link', text: `View all country alerts (${allCrisisAlerts().length})`, onclick: () => { monitorCountry = 'all'; setHash(hashFor('all')); renderAlerts(); } })
        : h('span', { class: 'typed', text: `${all.length} active alerts (${periodLabel})` })
    );

    results.replaceChildren(...[
      h('p', { class: 'result-line' },
        h('b', { text: filterCountry ? `Official alerts · ${countryName}` : 'Active crisis, conflict & official travel alerts' }),
        ` · ${periodLabel} · ${plural(all.length, 'alert', 'alerts')}${c ? ` · checked ${fmtTime.format(new Date(c.generated_at))}` : ''} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
      all.length
        ? h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null, ['Country', 'Region', 'Source', 'Alert / Advisory & Details', 'Date'].map((x) => h('th', { text: x })))),
            h('tbody', null, all.map((i) => h('tr', null,
              h('td', { class: 'cell-head' }, index.countries.some((x) => x.id === i.cid)
                ? h('button', { type: 'button', class: 'stamp country-tag', text: i.cname, onclick: () => { monitorCountry = i.cid; setHash(hashFor('all')); renderAlerts(); } })
                : h('span', { class: 'stamp', text: i.cname })),
              h('td', { class: 'meta', text: i.region }),
              h('td', null, h('span', { class: 'stamp ' + (isHotAlert(i) ? 'red' : 'indigo'), text: i.kind })),
              h('td', { class: 'cell-body' },
                h('a', { href: safeUrl(i.url), target: '_blank', rel: 'noopener noreferrer', text: i.title }),
                i.summary && h('p', { class: 'byline', text: i.summary })),
              h('td', { class: 'typed', text: i.date ? fmtDay.format(new Date(i.date)) : '—' }))))))
        : h('p', { class: 'state', text: filterCountry ? `No active official alerts for ${countryName}.` : 'No matching alerts.' }),
      h('p', { class: 'fine', text: 'Sources: GDELT 2.0 real-time CAMEO conflict stream (verbatim headline verified), ACLED (optional API), Global Disaster Alert and Coordination System (GDACS), US Geological Survey (USGS M4.5+ earthquakes), NASA Earth Observatory (EONET), United Nations Peace & Security, International Crisis Group, Human Rights Watch (HRW), Long War Journal (LWJ), Médecins Sans Frontières (MSF), UK FCDO, and US Department of State elevated travel advisories.' }),
    ].filter(Boolean));
  }

  // ---------- Disasters & Conflict/Security Monitors ----------
  const DISASTER_RULES = [
    ['Storm & Cyclone', /\b(typhoon|cyclone|hurricane|tropical storm|tornado|gale|sieu bao|ap thap nhiet doi|loc xoay|con bao|taufan|badai|bagyo|พายุ|မုန်တိုင်း|vihar|orkan|burza|tufao|ciclone|firtina|kasirga)\b/],
    ['Flood & Landslide', /\b(flood|floods|flooding|flash flood|landslide|mudslide|inundation|lu lut|ngap lut|ngap sau|sat lo|trieu cuong|banjir|longsor|baha|guho|น้ำท่วม|ดินถล่ม|ရေကြီး|arviz|powodz|poplava|heyelan|enchente|deslizamento)/],
    ['Earthquake & Volcano', /\b(earthquake|tremor|seismic|tsunami|volcano|volcanic|eruption|dong dat|nui lua|song than|gempa|gunung berapi|lindol|bulkan|แผ่นดินไหว|ငလျင်|foldrenges|trzesienie ziemi|zemljotres|deprem|yanardag|terremoto|zelzele)/],
    ['Wildfire & Drought', /\b(wildfire|forest fire|bushfire|drought|heatwave|chay rung|han han|kebakaran hutan|kekeringan|ไฟป่า|ภัยแล้ง|erdotuz|aszaly|pozar lasu|susa|orman yangini|kuraklik|incendio florestal|seca\b)/],
  ];

  // Co-occurrence requirements: religious sensitivity requires BOTH a confessional identity/symbol
  // AND an active conflict, violence, coercion, or persecution vector.
  const CONFLICT_IMPACT_PATTERN = /\b(attack|attacks|assault|clash|clashes|ambush|strike|strikes|airstrike|airstrikes|bomb|bombing|bombed|explosion|shoot|shooting|shot|gunmen|gunbattle|firefight|kill|killed|killing|murder|murdered|dead|death|fatalities|casualties|massacre|behead|beheaded|slaughter|kidnap|kidnapped|kidnapping|abduct|abducted|abduction|hostage|hostages|pogrom|lynch|lynched|arson|burned|burnt|firebomb|desecrat|vandaliz|persecut|persecution|terror|terrorist|terrorism|militant|militants|militia|militias|insurgent|insurgency|jihad|jihadist|extremis|extremist|ied|anti-conversion|blasphemy|forced conversion|expel|expels|expelled|expulsion|displaced|refugee|refugees|fled|fleeing|shelled|shelling|mortar|artillery|drone strike|air strike|missile strike|riot|riots|tear gas|curfew|martial law|coup|crackdown|looting|looted|raid|raided|mass grave|mass graves|tan cong|sat hai|giet|bat coc|khung bo|dot pha|pha huy|bao loan|khong kich|phao kich|giao tranh|merenylet|tamadas|gyilkossag|emberrablas|lefejezes|gyujtogatas|rombolas)\b/i;

  // Strict negative filter: exclude cultural, artistic, theatrical, and sports stories
  const CULTURAL_SPORTS_EXCLUDE = /\b(festival|dance|choreodrama|theatre|theater|concert|music|album|song|singer|film|movie|championship|tournament|league|match|coach|player|stadium|actor|actress|museum|art exhibition|ballet|opera|pfdk|football|soccer|basketball|baseball|cricket|tennis|golf)\b/i;

  const RELIGIOUS_RULES = [
    ['Judaism', /\b(synagogue|anti-semit|antisemit|jewish|judaism|kosher|rabbi|shul|yemenite jew|zsinagoga|zsido|antiszemita|bai do thai)\b/i],
    ['Christianity', /\b(christians|christianity|christian (?:faithful|minority|minorities|community|communities|group|groups|church|churches|pastor|priest|genocide|persecution|population|village|villages|family|families|civilian|civilians)|church|chapel|monastery|cathedral|priest|pastor|nuns|copt|coptic|chaldean|assyrian|maronite|evangelical|templom|lelkipasztor|lelkesz|puspok|kereszteny|nha tho|linh muc|giao dan)\b/i],
    ['Islam', /\b(mosque|minaret|imam|madrassa|madrasa|quran|koran|muslim|islam|islamic|islamist|rohingya|uyghur|uighur|ahmadiyya|hazara|shia|sunni|fatwa|mecset|muszlim|muzulman|nha tho hoi giao)\b/i],
    ['Other Faiths & Sites', /\b(yazidi|bahai|baha'i|hindutva|anti-conversion|blasphemy|sacred site|holy site|cemetery desecrat|pogrom|sectarian|interfaith|inter-communal|istenkaromlas|atterites|vallasi uldozes|giao phai)\b/i],
  ];

  const CONFLICT_TRACKS = [
    ['all', 'All Kinetic Conflict & Unrest'],
    ['armed_clash', 'Armed Clashes & Strikes'],
    ['insurgency', 'Insurgency, Terror & Kidnapping'],
    ['unrest', 'Civil Unrest & Crackdowns'],
    ['rel_all', 'Religious Sensitivity (All)'],
    ['rel_jewish', 'Judaism'],
    ['rel_christian', 'Christianity'],
    ['rel_islam', 'Islam'],
    ['rel_other', 'Other Faiths & Sacred Sites'],
  ];

  const ARMED_CLASH_RE = /\b(airstrike|airstrikes|air strike|drone strike|missile strike|shelling|shelled|mortar|artillery|armed clash|clashes|firefight|gunbattle|gunmen|bombardment|incursion|ceasefire|cross-border|khong kich|phao kich|giao tranh)\b/i;
  const INSURGENCY_RE = /\b(terror|terrorist|terrorism|insurgent|insurgency|militant|militants|boko haram|iswap|al-shabaab|isis|daesh|jihad|jihadist|taliban|houthi|houthis|hezbollah|hamas|ied|suicide bomb|car bomb|ambush|kidnap|kidnapped|abduct|abducted|hostage|massacre|khung bo|bat coc)\b/i;
  const UNREST_RE = /\b(protest|protesters|riot|riots|demonstrat|curfew|martial law|coup|tear gas|water cannon|looting|crackdown|arson|bao loan|bieu tinh|thiet quan luat|dao chinh)\b/i;

  function matchConflictTrack(s, trackId) {
    if (!trackId || trackId === 'all') return true;
    const trads = s.religious_traditions || [];
    if (trackId === 'rel_all') return trads.length > 0;
    if (trackId === 'rel_jewish') return trads.includes('Judaism');
    if (trackId === 'rel_christian') return trads.includes('Christianity');
    if (trackId === 'rel_islam') return trads.includes('Islam');
    if (trackId === 'rel_other') return trads.includes('Other Faiths & Sacred Sites');
    const text = fold([s.headline && s.headline.title, (s.headline && s.headline.en_title) || '', T.byText.get((s.headline && s.headline.title) || '') || '', ...(s.sources || []).slice(0, 4).map((r) => r.title)].join(' '));
    if (CULTURAL_SPORTS_EXCLUDE.test(text)) return false;
    if (trackId === 'armed_clash') return s.violence_type === 'Armed Clash & Strike' || ARMED_CLASH_RE.test(text);
    if (trackId === 'insurgency') return s.violence_type === 'Insurgency & Terror' || INSURGENCY_RE.test(text);
    if (trackId === 'unrest') return s.violence_type === 'Civil Unrest & Crackdown' || UNREST_RE.test(text);
    return true;
  }

  function matchAlertConflictTrack(alert, trackId) {
    if (!trackId || trackId === 'all') return true;
    const hay = fold(`${alert.cname || ''} ${alert.region || ''} ${alert.kind || ''} ${alert.title || ''} ${alert.summary || ''}`);
    if (CULTURAL_SPORTS_EXCLUDE.test(hay)) return false;
    if (trackId.startsWith('rel_') && !CONFLICT_IMPACT_PATTERN.test(hay)) return false;
    if (trackId === 'rel_all') {
      return RELIGIOUS_RULES.some(([, re]) => re.test(hay));
    }
    if (trackId === 'rel_jewish') return RELIGIOUS_RULES[0][1].test(hay);
    if (trackId === 'rel_christian') return RELIGIOUS_RULES[1][1].test(hay);
    if (trackId === 'rel_islam') return RELIGIOUS_RULES[2][1].test(hay);
    if (trackId === 'rel_other') return RELIGIOUS_RULES[3][1].test(hay);
    if (trackId === 'armed_clash') return ARMED_CLASH_RE.test(hay);
    if (trackId === 'insurgency') return INSURGENCY_RE.test(hay);
    if (trackId === 'unrest') return UNREST_RE.test(hay);
    return true;
  }

  function tagEventStory(s) {
    const th = (s.themes || []).join(' ').toLowerCase();
    if (th.includes('sport') || th.includes('culture') || th.includes('entertainment') || s.category === 'sport_culture') return s;
    const leadText = fold([s.headline && s.headline.title, (s.headline && s.headline.en_title) || '', T.byText.get((s.headline && s.headline.title) || '') || '', ...(s.sources || []).slice(0, 3).map((r) => r.title)].join(' '));
    const dType = s.disaster_type || (DISASTER_RULES.find(([, re]) => re.test(leadText)) || [])[0] || null;

    let vType = s.violence_type || null;
    if (!vType && !CULTURAL_SPORTS_EXCLUDE.test(leadText)) {
      if (INSURGENCY_RE.test(leadText)) vType = 'Insurgency & Terror';
      else if (ARMED_CLASH_RE.test(leadText)) vType = 'Armed Clash & Strike';
      else if (UNREST_RE.test(leadText)) vType = 'Civil Unrest & Crackdown';
      else if (CONFLICT_IMPACT_PATTERN.test(leadText) && (s.category === 'defence_security' || th.includes('security') || th.includes('conflict') || th.includes('violence'))) {
        vType = 'Armed Clash & Strike';
      }
    }

    // Strict religious sensitivity: ONLY tag when BOTH a religious group/symbol AND an active conflict/harm event co-occur
    // within the SAME title or quote, while strictly excluding cultural, arts, festival, and sports articles.
    let relTraditions = null;
    const candidates = [
      [s.headline && s.headline.title, `${(s.headline && s.headline.en_title) || ''} ${T.byText.get((s.headline && s.headline.title) || '') || ''}`],
      ...(s.sources || []).slice(0, 3).map((r) => [r.title, ''])
    ];

    for (const [title, trans] of candidates) {
      if (!title) continue;
      const text = fold(`${title} ${trans}`);
      if (CULTURAL_SPORTS_EXCLUDE.test(text)) continue;
      if (!CONFLICT_IMPACT_PATTERN.test(text)) continue;
      const hits = [];
      for (const [trad, re] of RELIGIOUS_RULES) {
        if (re.test(text)) hits.push(trad);
      }
      if (hits.length) {
        relTraditions = hits;
        break;
      }
    }

    return {
      ...s,
      disaster_type: dType,
      violence_type: vType,
      religious_traditions: s.religious_traditions || relTraditions
    };
  }

  const storyRecency = (s) => new Date(s.last_seen || (s.headline && s.headline.published) || s.first_seen || 0).getTime();

  const loadedPeriods = new Set();
  function ensurePeriodLoaded(per) {
    if (loadedPeriods.has(per)) return;
    loadedPeriods.add(per);
    Promise.allSettled(index.countries.map((c) => load(`${c.id}-${per}.json`))).then(() => {
      if (activeTab === 'disasters' || activeTab === 'violence') renderEventMonitor(activeTab);
    });
  }

  function collectEventPool(mode, per = monitorPeriod) {
    const hm = window.ARGOS_HOME || {};
    const seen = new Set();
    const out = [];
    const isDis = mode === 'disasters';
    const cutoff = periodCutoff(per);

    const add = (s, cid, cname, region) => {
      if (!s || seen.has(s.id)) return;
      if (cutoff && storyRecency(s) < cutoff) return;
      const th = (s.themes || []).join(' ').toLowerCase();
      if (th.includes('sport') || th.includes('culture') || th.includes('entertainment') || s.category === 'sport_culture') return;
      const tagged = tagEventStory({ ...s, country: s.country || cid, country_name: s.country_name || cname, region: s.region || region || getRegion(s.country || cid) });
      const keep = isDis
        ? Boolean(tagged.disaster_type)
        : (tagged.category !== 'sport_culture' && (
           Boolean(tagged.violence_type)
           || (tagged.themes || []).includes('Civil unrest and armed conflict')
           || (tagged.themes || []).includes('Sectarian and confessional violence')
           || Boolean(tagged.religious_traditions && tagged.religious_traditions.length)
        ));
      if (keep) { seen.add(s.id); out.push(tagged); }
    };

    const preset = isDis ? (hm.disasters || []) : (hm.violent_events || []);
    preset.forEach((s) => add(s));
    [...(hm.most_reported || []), ...(hm.growing || [])].forEach((s) => add(s));

    for (const c of index.countries) {
      const d = window.ARGOS_DATA && window.ARGOS_DATA[`${c.id}-${per}`];
      if (d && d.stories) d.stories.forEach((s) => add(s, c.id, c.name, getRegion(c.id)));
    }
    ensurePeriodLoaded(per);
    return out.sort((a, b) => storyRecency(b) - storyRecency(a));
  }

  function renderEventMonitor(mode) {
    T.queue.length = 0;
    const isDis = mode === 'disasters';
    const filterCountry = monitorCountry !== 'all' ? monitorCountry : null;
    const cutoff = periodCutoff(monitorPeriod);

    const allStories = collectEventPool(mode, monitorPeriod).filter((s) => {
      if (filterCountry && s.country !== filterCountry) return false;
      return true;
    });
    allStories.sort((a, b) => storyRecency(b) - storyRecency(a));

    const allOfficial = allCrisisAlerts().filter((i) => {
      if (filterCountry && i.cid !== filterCountry) return false;
      if (cutoff && (!i.date || new Date(i.date).getTime() < cutoff)) return false;
      const hay = fold(`${i.cname} ${i.region} ${i.kind} ${i.title} ${i.summary || ''}`);
      if (isDis) return /^(GDACS|USGS|NASA EONET)$/.test(i.kind) || /\b(disaster|earthquake|flood|typhoon|cyclone|volcano|wildfire)\b/.test(hay);
      return /^(GDELT Live Event|ACLED|UN Peace & Security|Crisis Group|Human Rights Watch|Long War Journal|MSF Crisis Update)$/.test(i.kind)
        || /travel/i.test(i.kind)
        || /\b(terror|unrest|conflict|armed|violence|violent|kidnap|martial|security|war|attack|strike|clash)\b/.test(hay);
    });
    allOfficial.sort((a, b) => new Date(b.date || 0).getTime() - new Date(a.date || 0).getTime());

    if (isDis) {
      if (openSubType !== 'all' && !DISASTER_RULES.some(([label]) => label === openSubType)) openSubType = 'all';
    } else {
      if (openSubType !== 'all' && !CONFLICT_TRACKS.some(([id]) => id === openSubType)) openSubType = 'all';
    }

    const stories = isDis
      ? (openSubType !== 'all' ? allStories.filter((s) => s.disaster_type === openSubType) : allStories)
      : (openSubType !== 'all' ? allStories.filter((s) => matchConflictTrack(s, openSubType)) : allStories);

    const filteredOfficial = isDis
      ? allOfficial
      : (openSubType !== 'all' ? allOfficial.filter((i) => matchAlertConflictTrack(i, openSubType)) : allOfficial);

    const subTabs = isDis
      ? tabBar(
          [['all', 'All types', allStories.length], ...DISASTER_RULES.map(([label]) => [label, label, allStories.filter((s) => s.disaster_type === label).length])],
          openSubType,
          (id) => { openSubType = id; renderEventMonitor(mode); },
          'Event',
          'Filter by event type')
      : tabBar(
          CONFLICT_TRACKS.map(([id, label]) => [id, label, allStories.filter((s) => matchConflictTrack(s, id)).length]),
          openSubType,
          (id) => { openSubType = id; renderEventMonitor(mode); },
          'Track',
          'Filter by conflict track & religious sensitivity');

    const countryName = filterCountry ? prettyName(filterCountry) : null;
    const periodLabel = (MONITOR_PERIODS.find(([v]) => v === monitorPeriod) || [])[1] || 'Past 7 days';
    const titleText = filterCountry
      ? (isDis ? `Disasters & Severe Weather · ${countryName}` : `Conflict & Security · ${countryName}`)
      : (isDis ? 'Natural Disasters & Severe Weather Monitor' : 'Conflict & Security Monitor (Live Events, Field Monitors & Press)');

    const bar = h('div', { class: 'monitor-bar' },
      h('div', { class: 'monitor-filters' },
        countryPicker(monitorCountry, (val) => {
          monitorCountry = val;
          setHash(hashFor('all'));
          renderEventMonitor(mode);
        }),
        periodPicker(monitorPeriod, (val) => {
          monitorPeriod = val;
          setHash(hashFor('all'));
          renderEventMonitor(mode);
        })
      ),
      filterCountry
        ? h('button', { type: 'button', class: 'desk-link', text: `View all country ${isDis ? 'disasters' : 'conflict & security alerts'}`, onclick: () => { monitorCountry = 'all'; setHash(hashFor('all')); renderEventMonitor(mode); } })
        : h('span', { class: 'typed', text: `${allStories.length} clusters · ${allOfficial.length} official alerts (${periodLabel})` })
    );

    results.replaceChildren(...[
      h('p', { class: 'result-line' },
        h('b', { text: titleText }),
        ` · ${periodLabel} · ${plural(filteredOfficial.length, isDis ? 'official sensor alert' : 'live event & conflict report', isDis ? 'official sensor alerts' : 'live events & conflict reports')} · ${plural(stories.length, isDis ? 'reported disaster cluster' : 'kinetic conflict & unrest cluster', isDis ? 'reported disaster clusters' : 'kinetic conflict & unrest clusters')} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
      subTabs,
      filteredOfficial.length > 0 && h('section', { class: 'drawer' },
        h('div', { class: 'drawer-head' },
          h('h2', { text: isDis ? 'Official satellite & seismic sensor alerts' : 'Real-time violence events, field monitors & official advisories' }),
          h('span', { class: 'count', text: isDis ? 'GDACS · USGS · NASA EONET' : 'GDELT 2.0 · UN · Crisis Group · HRW · LWJ · MSF · FCDO · State Dept' })),
        h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null, ['Country', 'Region', 'Source', 'Event / Advisory & Details', 'Date'].map((x) => h('th', { text: x })))),
            h('tbody', null, filteredOfficial.map((i) => h('tr', null,
              h('td', { class: 'cell-head' }, h('button', { type: 'button', class: 'stamp country-tag', text: i.cname, onclick: () => { monitorCountry = i.cid; setHash(hashFor('all')); renderEventMonitor(mode); } })),
              h('td', { class: 'meta', text: i.region }),
              h('td', null, h('span', { class: 'stamp ' + (isHotAlert(i) ? 'red' : 'indigo'), text: i.kind })),
              h('td', { class: 'cell-body' },
                h('a', { href: safeUrl(i.url), target: '_blank', rel: 'noopener noreferrer', text: i.title }),
                i.summary && h('p', { class: 'byline', text: i.summary })),
              h('td', { class: 'typed', text: i.date ? fmtDay.format(new Date(i.date)) : '—' }))))))),
      stories.length > 0
        ? homeSection(
            isDis ? 'Reported disaster & severe weather clusters (most recent first)' : 'Reported kinetic conflict, terror & unrest story clusters (most recent first)',
            'Organized by recency across monitored feeds',
            stories.slice(0, 36))
        : h('p', { class: 'state', text: filterCountry ? `No matching reported events for ${countryName}.` : 'No matching reported story clusters.' }),
      h('div', { id: 'trans', class: 'trans' }),
    ].filter(Boolean));
    paintTranslationBar();
    translatePending();
  }

  // ---------- Bilateral & Joint Affairs Monitor ----------
  const COMMON_PARTNERS = [
    { id: 'laos', name: 'Laos', terms: ['laos', 'vientiane', 'luang prabang', 'ລາວ'] },
    { id: 'china', name: 'China', terms: ['china', 'chinese', 'beijing', 'trung quốc', 'kínai', 'chine', 'pekin', 'xi jinping'] },
    { id: 'us', name: 'United States', terms: ['united states', 'usa', 'u.s.', 'washington', 'mỹ', 'hoa kỳ', 'amerika', 'américain', 'biden', 'trump'] },
    { id: 'russia', name: 'Russia', terms: ['russia', 'russian', 'moscow', 'nga', 'orosz', 'kremlin', 'putin', 'россия'] },
    { id: 'eu', name: 'European Union', terms: ['european union', 'eu', 'brussels', 'liên minh châu âu', 'európai unió', 'bruxelles'] },
    { id: 'uk', name: 'United Kingdom', terms: ['united kingdom', 'britain', 'british', 'london', 'anh quốc', 'nagy-britannia'] },
    { id: 'india', name: 'India', terms: ['india', 'indian', 'new delhi', 'ấn độ', 'delhi', 'modi'] },
    { id: 'japan', name: 'Japan', terms: ['japan', 'japanese', 'tokyo', 'nhật bản', 'japán'] },
    { id: 'south_korea', name: 'South Korea', terms: ['south korea', 'korean', 'seoul', 'hàn quốc', 'dél-korea'] },
  ];

  const QUICK_PRESETS = [
    [['cambodia', 'vietnam'], 'Cambodia & Vietnam'],
    [['cambodia', 'laos', 'vietnam'], 'Mekong Basin (KH, LA, VN)'],
    [['japan', 'south_korea', 'taiwan'], 'East Asia Tech & Security (JP, KR, TW)'],
    [['japan', 'malaysia', 'indonesia', 'cambodia', 'laos'], 'East & SE Asia Corridor (JP, MY, ID, KH, LA)'],
    [['kazakhstan', 'azerbaijan', 'georgia', 'turkey'], 'Middle Corridor (KZ, AZ, GE, TR)'],
    [['czechia', 'hungary', 'poland', 'slovakia'], 'Visegrád Four (V4: CZ, HU, PL, SK)'],
    [['serbia', 'kosovo', 'bosnia'], 'Balkans Triangle (RS, XK, BA)'],
    [['uzbekistan', 'kazakhstan', 'kyrgyzstan'], 'Central Asia (UZ, KZ, KG)'],
    [['armenia', 'azerbaijan'], 'Armenia & Azerbaijan'],
    [['malaysia', 'indonesia'], 'Malaysia & Indonesia'],
    [['kenya', 'ethiopia'], 'Horn of Africa (KE, ET)'],
    [['argentina', 'brazil', 'colombia'], 'South America (AR, BR, CO)'],
  ];

  let selectedCountries = ['cambodia', 'vietnam'];
  let relPeriod = '7d';

  function getCountryTerms(id) {
    const c = index.countries.find((x) => x.id === id);
    if (c) {
      const list = [fold(c.name), fold(c.id), ...(c.mentions || []).map(fold)];
      return [...new Set(list.filter((x) => x && x.length > 2 && !(id === 'laos' && x === 'lao')))];
    }
    const p = COMMON_PARTNERS.find((x) => x.id === id);
    if (p) {
      const list = [fold(p.name), fold(p.id), ...p.terms.map(fold)];
      return [...new Set(list.filter((x) => x && x.length > 2 && !(id === 'laos' && x === 'lao')))];
    }
    if (id) {
      return [fold(id)];
    }
    return [];
  }

  function buildTermRegex(terms) {
    const clean = terms.filter(Boolean).map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    if (!clean.length) return null;
    return new RegExp(`(?:^|[^a-z0-9])(?:${clean.join('|')})(?=$|[^a-z0-9])`, 'i');
  }

  async function loadCountryStories(cid, per) {
    const c = index.countries.find((x) => x.id === cid);
    if (!c) return [];
    const p = c.periods.find((x) => x.id === per) || c.periods.find((x) => x.id === '7d') || c.periods[0];
    if (!p) return [];
    try {
      const d = await load(p.file);
      return ((d && d.stories) || []).map((s) => ({ ...s, country: s.country || cid, country_name: s.country_name || c.name }));
    } catch {
      return [];
    }
  }

  function bilateralDeltaPanel(matchedStories, selectedCountries, relPeriod) {
    if (!matchedStories || !matchedStories.length) return null;

    const deltas = matchedStories.map((s) => s.delta).filter(Boolean);
    const currTotal = deltas.reduce((acc, d) => acc + (d.curr || 0), 0);
    const prevTotal = deltas.reduce((acc, d) => acc + (d.prev || 0), 0);
    const netArticles = currTotal - prevTotal;
    const ratio = prevTotal > 0 ? (currTotal / prevTotal).toFixed(2) + 'x' : currTotal > 0 ? `${currTotal}x` : '1.0x';

    const nNew = deltas.filter((d) => d.state === 'new').length;
    const nSurge = deltas.filter((d) => d.state === 'surging').length;
    const nCooling = deltas.filter((d) => d.state === 'cooling').length;
    const nIntl = deltas.filter((d) => d.scope_shift === 'international_pickup').length;
    const nDiaspora = deltas.filter((d) => d.scope_shift === 'diaspora_pickup').length;
    const nStateSurge = deltas.filter((d) => d.state_surge).length;

    // Category distribution
    const catCounts = {};
    for (const s of matchedStories) {
      const c = s.category || 'other';
      catCounts[c] = (catCounts[c] || 0) + 1;
    }
    const topCatEntry = Object.entries(catCounts).sort((a, b) => b[1] - a[1])[0];
    const topCatName = topCatEntry ? topicName(topCatEntry[0]) : null;
    const topCatPct = topCatEntry ? Math.round((topCatEntry[1] / matchedStories.length) * 100) : 0;

    let overallState = 'steady';
    if (prevTotal === 0 && currTotal >= 2) overallState = 'new';
    else if (netArticles >= 3 && (currTotal / Math.max(1, prevTotal)) >= 1.75) overallState = 'surging';
    else if (-netArticles >= 3 && (currTotal / Math.max(1, prevTotal)) <= 0.40) overallState = 'cooling';

    const sign = netArticles > 0 ? '+' : '';
    const arrow = netArticles > 0 ? '↑' : (netArticles < 0 ? '↓' : '·');

    const pills = [];
    if (overallState === 'surging') pills.push(h('span', { class: 'stamp stamp-surge', text: `SURGE ${sign}${netArticles}` }));
    else if (overallState === 'new') pills.push(h('span', { class: 'stamp stamp-new', text: 'NEW EMERGENCE' }));
    else if (overallState === 'cooling') pills.push(h('span', { class: 'stamp stamp-cooling', text: 'COOLING' }));

    if (nNew > 0 && overallState !== 'new') pills.push(h('span', { class: 'stamp stamp-new', text: `${nNew} NEW` }));
    if (nSurge > 0 && overallState !== 'surging') pills.push(h('span', { class: 'stamp stamp-surge', text: `${nSurge} SURGE` }));
    if (nIntl > 0) pills.push(h('span', { class: 'stamp stamp-pickup', text: `${nIntl} INTL PICKUP` }));
    if (nDiaspora > 0) pills.push(h('span', { class: 'stamp stamp-pickup', text: `${nDiaspora} DIASPORA` }));
    if (nStateSurge > 0) pills.push(h('span', { class: 'stamp red', text: `${nStateSurge} STATE SURGE` }));

    return h('div', { class: 'bilateral-delta-panel', role: 'region', 'aria-label': 'Bilateral delta comparisons' },
      h('div', { class: 'bilateral-delta-head' },
        h('strong', { text: selectedCountries.length === 2 ? 'Bilateral News Cycle Momentum' : 'Multilateral News Cycle Momentum' }),
        h('span', { class: 'meta', text: `(vs prior ${relPeriod === '24h' ? '24h' : '7d'}): ` }),
        h('span', { class: 'typed', text: `${currTotal} articles across ${matchedStories.length} joint stories (${arrow} ${sign}${netArticles} articles · ${ratio} velocity)` })
      ),
      h('div', { class: 'bilateral-delta-body' },
        pills.length > 0 && h('div', { class: 'bilateral-delta-pills' }, ...pills),
        topCatName && h('div', { class: 'bilateral-delta-cat' },
          h('span', { class: 'meta', text: 'Lead Focus: ' }),
          h('strong', { text: `${topCatName} (${topCatPct}%)` })
        )
      )
    );
  }

  async function renderRelations() {
    T.queue.length = 0;
    if (!selectedCountries.length) selectedCountries = ['cambodia', 'vietnam'];
    const names = selectedCountries.map(getCountryName);
    const titleStr = names.join(names.length === 2 ? ' & ' : ', ');

    const unselectedCountries = index.countries.filter((c) => !selectedCountries.includes(c.id));
    const unselectedPartners = COMMON_PARTNERS.filter((p) => !selectedCountries.includes(p.id));

    const chips = h('div', { class: 'country-chips' },
      ...selectedCountries.map((cid) =>
        h('span', { class: 'country-chip notranslate', translate: 'no' },
          getCountryName(cid),
          selectedCountries.length > 1 && h('button', {
            type: 'button',
            class: 'x',
            title: `Remove ${getCountryName(cid)}`,
            'aria-label': `Remove ${getCountryName(cid)}`,
            onclick: () => {
              selectedCountries = selectedCountries.filter((x) => x !== cid);
              setHash(hashFor('all'));
              renderRelations();
            }
          }, '×')
        )
      ),
      h('select', {
        class: 'add-country-sel notranslate',
        translate: 'no',
        onchange: (e) => {
          const val = e.target.value;
          if (val && !selectedCountries.includes(val)) {
            selectedCountries.push(val);
            setHash(hashFor('all'));
            renderRelations();
          }
        }
      },
        h('option', { value: '', text: '+ Add country / partner…' }),
        h('optgroup', { label: 'Major Partners & Powers', class: 'notranslate', translate: 'no' },
          ...unselectedPartners.map((p) => h('option', { value: p.id, text: p.name, class: 'notranslate', translate: 'no' }))),
        ...REGIONS.flatMap((r) => {
          const items = unselectedCountries.filter((c) => getRegion(c.id) === r);
          return items.length ? [h('optgroup', { label: r, class: 'notranslate', translate: 'no' }, ...items.map((c) => h('option', { value: c.id, text: c.name, class: 'notranslate', translate: 'no' })))] : [];
        })
      )
    );

    const bar = h('div', { class: 'bilateral-bar' },
      h('div', { class: 'bilateral-controls' },
        h('div', { class: 'field' },
          h('span', { text: selectedCountries.length === 2 ? 'Bilateral Partners' : 'Selected Countries' }),
          chips
        ),
        h('label', { class: 'field' },
          h('span', { text: 'Time Window' }),
          h('select', {
            id: 'rel-sel-period',
            onchange: (e) => { relPeriod = e.target.value; setHash(hashFor('all')); renderRelations(); }
          },
            [['7d', 'Last 7 days'], ['24h', 'Last 24 hours']].map(([v, label]) =>
              h('option', { value: v, text: label, selected: v === relPeriod })))),
      ),
      h('div', { class: 'bilateral-pairs' },
        h('span', { class: 'pair-label', text: 'Quick presets:' }),
        ...QUICK_PRESETS.map(([cids, label]) => {
          const isActive = cids.length === selectedCountries.length && cids.every((c, i) => c === selectedCountries[i]);
          return h('button', {
            type: 'button',
            class: 'pair-pill' + (isActive ? ' active' : ''),
            text: label,
            onclick: () => {
              selectedCountries = [...cids];
              setHash(hashFor('all'));
              renderRelations();
            }
          });
        })
      )
    );

    const loadingState = h('p', { class: 'state', text: `Analyzing reporting for ${titleStr}…` });
    results.replaceChildren(
      h('p', { class: 'result-line' },
        h('b', { text: `Joint & Multilateral Affairs · ${titleStr}` }),
        ` · ${relPeriod === '24h' ? 'Last 24 hours' : 'Last 7 days'} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
      loadingState
    );

    // Fetch datasets for all monitored desks in selectedCountries
    const monitoredSelected = selectedCountries.filter((cid) => index.countries.some((x) => x.id === cid));
    const rawDatasets = await Promise.all(monitoredSelected.map((cid) => loadCountryStories(cid, relPeriod)));

    // Combine pool: all stories from selected desks + global pool (ARGOS_HOME)
    const hm = window.ARGOS_HOME;
    const globalPool = hm ? [...(hm.most_reported || []), ...(hm.growing || [])] : [];
    const pool = [...rawDatasets.flat(), ...globalPool];

    // Deduplicate stories by headline URL or story ID
    const seen = new Set();
    const candidateStories = [];
    for (const s of pool) {
      const hUrl = s.headline && s.headline.url;
      const hTitle = s.headline && s.headline.title;
      const key = hUrl || (hTitle ? `${hTitle}|${s.country || ''}` : String(s.id));
      if (!seen.has(key)) {
        seen.add(key);
        candidateStories.push(s);
      }
    }

    // Matching: story must involve EVERY selected country via word-boundary regex
    const regexMap = new Map(selectedCountries.map((cid) => [cid, buildTermRegex(getCountryTerms(cid))]));
    const storyInvolvesCountry = (s, cid) => {
      if (s.country === cid) return true;
      const re = regexMap.get(cid);
      if (!re) return false;
      return re.test(storyText(s));
    };

    const matchedStories = candidateStories.filter((s) =>
      selectedCountries.every((cid) => storyInvolvesCountry(s, cid))
    );

    // Sort by recency
    matchedStories.sort((a, b) => storyRecency(b) - storyRecency(a));

    loadingState.remove();
    const deltaPanel = bilateralDeltaPanel(matchedStories, selectedCountries, relPeriod);
    results.replaceChildren(
      h('p', { class: 'result-line' },
        h('b', { text: `Joint & Multilateral Affairs · ${titleStr}` }),
        ` · ${plural(matchedStories.length, 'story', 'stories')} found · ${relPeriod === '24h' ? 'Last 24 hours' : 'Last 7 days'} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
      deltaPanel,
      matchedStories.length
        ? h('div', { class: 'grid' }, matchedStories.map((s, i) => story(s, { lead: i === 0, i })))
        : h('p', { class: 'state', text: `No stories found involving all selected partners (${titleStr}) in the ${relPeriod === '24h' ? 'last 24 hours' : 'last 7 days'}.` }),
      h('p', { class: 'fine' },
        `Cross-country intelligence monitor: cross-references reporting across monitored desks to isolate joint communiqués, multilateral agreements, diplomatic summits, territorial disputes, and trade interaction.`
      ),
      h('div', { id: 'trans', class: 'trans' })
    );
    paintTranslationBar();
    translatePending();
  }

  // ---------- Overview homepage (scales to any number of countries via site/data/home.js) ----------
  function homeSection(title, sub, list) {
    if (!list || !list.length) return null;
    return h('section', { class: 'drawer' },
      h('div', { class: 'drawer-head' }, h('h2', { text: title }), h('span', { class: 'count', text: sub })),
      h('div', { class: 'grid' }, list.map((s, i) => story(s, { lead: i === 0, i }))));
  }

  function renderHome() {
    const hm = window.ARGOS_HOME;
    if (!hm) { openCountry(index.countries[0].id); return; }
    T.queue.length = 0;
    const q = ($('#q').value || '').trim().toLowerCase();
    const c = getCrisis();
    const allDesks = [...(hm.desks || [])].map((d) => ({
      ...d,
      region: d.region || getRegion(d.id),
      nAlerts: (c && c.countries && c.countries[d.id] || []).length,
    }));
    if (openRegion !== 'all' && !allDesks.some((d) => d.region === openRegion)) openRegion = 'all';
    const inReg = (x) => openRegion === 'all' || (x.region || getRegion(x.country || x.id)) === openRegion;
    const filter = (arr, limit) => (arr || [])
      .filter((s) => inReg(s) && (!q || matchStory(s, q)))
      .slice(0, limit);
    const allAlerts = allCrisisAlerts().filter(inReg);
    const pool = [...(hm.elections || []), ...(hm.growing || []), ...(hm.most_reported || [])]
      .filter((s, i, a) => inReg(s) && a.findIndex((x) => x.id === s.id) === i);

    const deskQuery = (deskFilter || q).trim().toLowerCase();
    const desks = allDesks.filter((d) => {
      if (!inReg(d)) return false;
      if (!deskQuery) return true;
      return d.name.toLowerCase().includes(deskQuery)
        || d.region.toLowerCase().includes(deskQuery)
        || (d.lead && d.lead.title && d.lead.title.toLowerCase().includes(deskQuery));
    }).sort((a, b) => {
      if (deskSort === '24h') return (b.stories_24h - a.stories_24h) || (b.stories_7d - a.stories_7d);
      if (deskSort === '7d') return (b.stories_7d - a.stories_7d) || (b.stories_24h - a.stories_24h);
      if (deskSort === 'az') return a.name.localeCompare(b.name);
      return (b.nAlerts - a.nAlerts)
        || ((b.elections || 0) - (a.elections || 0))
        || ((b.surging || 0) - (a.surging || 0))
        || (b.stories_24h - a.stories_24h)
        || (b.stories_7d - a.stories_7d);
    });

    const tabs = regionTabs((r) => r === 'all' ? allDesks.length : allDesks.filter((d) => d.region === r).length, renderHome);
    const topAlerts = allAlerts.slice(0, 3);
    const dirSortLabels = [['attention', 'Attention'], ['24h', '24h'], ['7d', '7d'], ['az', 'A–Z']];

    results.replaceChildren(...[
      h('p', { class: 'result-line' },
        h('b', { text: openRegion === 'all' ? 'Overview across all monitored countries' : `Regional Desk · ${openRegion}` }),
        ` · ${plural(allDesks.filter(inReg).length, 'country', 'countries')} · updated ${fmtTime.format(new Date(hm.generated_at))}`),
      watchbar(q, pool),
      tabs,
      allAlerts.length > 0 && h('div', { class: 'crisis-strip', role: 'region', 'aria-label': 'Active crisis alerts' },
        h('div', { class: 'crisis-strip-head' },
          h('span', { class: 'stamp red', text: `${plural(allAlerts.length, 'active alert', 'active alerts')}` }),
          h('button', { type: 'button', class: 'desk-link', text: `All ${allAlerts.length} alerts →`, onclick: () => openCountry('alerts') })),
        h('ul', { class: 'crisis-strip-list' }, topAlerts.map((al) => h('li', null,
          h('button', { type: 'button', class: 'desk-link', text: al.cname, onclick: () => openCountry(al.cid) }),
          ` — ${al.summary || al.title}`)))),
      homeSection('Elections & ballot coverage', 'Priority diplomatic & electoral tracking', filter(hm.elections, 4)),
      homeSection('Fastest growing (last 24 hours)', 'Most new coverage in the last 24 hours', filter(hm.growing, 6)),
      homeSection('Most reported (last 7 days)', 'Ranked by independent outlet count', filter(hm.most_reported, openRegion === 'all' ? 6 : 4)),
      h('section', { class: 'drawer' },
        h('div', { class: 'drawer-head' },
          h('h2', { text: 'Monitored countries directory' }),
          h('span', { class: 'count', text: `${desks.length} active packs` })),
        h('div', { class: 'desk-controls' },
          h('div', { class: 'desk-sorts', role: 'group', 'aria-label': 'Sort countries' },
            h('span', { class: 'meta', text: 'Sort:' }),
            dirSortLabels.map(([id, label]) => h('button', {
              type: 'button',
              class: 'agenda-filter-btn' + (deskSort === id ? ' active' : ''),
              text: label,
              onclick: () => { deskSort = id; renderHome(); }
            }))),
          h('input', {
            type: 'search',
            class: 'desk-filter-input',
            placeholder: 'Filter directory…',
            'aria-label': 'Filter monitored countries directory',
            value: deskFilter,
            oninput: (e) => {
              deskFilter = e.target.value;
              const pos = e.target.selectionStart;
              renderHome();
              const next = $('.desk-filter-input');
              if (next) { next.focus(); if (pos != null) next.setSelectionRange(pos, pos); }
            }
          })),
        h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null,
              h('th', { text: 'Country' }),
              h('th', { text: 'Region' }),
              h('th', { text: '24h' }),
              h('th', { text: '7d' }),
              h('th', { text: 'Signals' }),
              h('th', { text: 'Lead story (7d)' }))),
            h('tbody', null, desks.map((d) => {
              const sigs = [];
              if (d.nAlerts) sigs.push(h('span', { class: 'stamp red', text: `${d.nAlerts} alert${d.nAlerts > 1 ? 's' : ''}` }));
              if (d.elections) sigs.push(h('span', { class: 'stamp indigo', text: '[ELECTION]' }));
              if (d.surging) sigs.push(h('span', { class: 'stamp indigo', text: `↑ ${d.surging}` }));
              return h('tr', null,
                h('td', { class: 'cell-head' }, h('button', { type: 'button', class: 'desk-link', text: `${d.name} →`, onclick: () => openCountry(d.id) })),
                h('td', { class: 'meta', text: d.region }),
                h('td', { class: 'typed', 'data-label': '24h', text: String(d.stories_24h) }),
                h('td', { class: 'typed', 'data-label': '7d', text: String(d.stories_7d) }),
                h('td', { 'data-label': 'Signals' }, sigs.length ? h('span', { class: 'desk-badges' }, sigs) : h('span', { class: 'meta', text: '—' })),
                h('td', { class: 'cell-body' }, d.lead ? (() => {
                  const cl = (index.countries.find((x) => x.id === d.id) || {}).language || 'en';
                  const a = h('a', { href: safeUrl(d.lead.url), target: '_blank', rel: 'noopener noreferrer', lang: cl, text: d.lead.title });
                  const o = h('span', { class: 'orig', hidden: true });
                  track(a, d.lead.title, cl, o);
                  return [a, o, h('span', { class: 'meta', text: ` (${d.lead.source} · ${d.lead.outlets} outlets)` })];
                })() : '—'));
            }))))),
      h('div', { id: 'trans', class: 'trans' }),
    ].filter(Boolean));
    paintTranslationBar();
    translatePending();
  }

  function agendaBar(d) {
    const delta = d.agenda_delta;
    if (!delta) return null;
    const items = Object.entries(delta)
      .map(([cat, info]) => ({ cat, name: topicName(cat), ...info }))
      .filter((x) => x.curr > 0 || x.prev > 0)
      .sort((a, b) => Math.abs(b.share_delta_pct) - Math.abs(a.share_delta_pct));
    if (!items.length) return null;

    const periodStr = d.period || 'window';
    return h('div', { class: 'agenda-bar', role: 'region', 'aria-label': 'Macro agenda movement' },
      h('div', { class: 'agenda-title' },
        h('strong', { text: 'Agenda Movement' }),
        h('span', { class: 'meta', text: `(vs prior ${periodStr}):` })
      ),
      h('ul', { class: 'agenda-list' },
        items.map((it) => {
          const sign = it.share_delta_pct > 0 ? '+' : '';
          const arrow = it.share_delta_pct > 0 ? '↑' : (it.share_delta_pct < 0 ? '↓' : '·');
          const dirClass = it.share_delta_pct >= 5.0 ? 'surging' : (it.share_delta_pct <= -5.0 ? 'cooling' : 'flat');
          return h('li', { class: `agenda-item ${dirClass}` },
            h('button', {
              type: 'button',
              class: 'agenda-btn',
              title: `${it.name}: ${it.curr} articles (${it.share_pct}%), ${sign}${it.share_delta_pct}% share vs prior ${periodStr}`,
              onclick: () => choose(it.cat)
            }, `${it.name} ${arrow} ${sign}${it.share_delta_pct}%`)
          );
        })
      ),
      h('div', { class: 'agenda-filters' },
        h('span', { class: 'meta', text: 'Filter:' }),
        h('button', {
          type: 'button',
          class: 'agenda-filter-btn' + (movementFilter === 'all' ? ' active' : ''),
          onclick: () => { movementFilter = 'all'; render(false); }
        }, 'All'),
        h('button', {
          type: 'button',
          class: 'agenda-filter-btn' + (movementFilter === 'surge_new' ? ' active' : ''),
          onclick: () => { movementFilter = 'surge_new'; render(false); }
        }, 'Surging & New'),
        h('button', {
          type: 'button',
          class: 'agenda-filter-btn' + (movementFilter === 'pickup' ? ' active' : ''),
          onclick: () => { movementFilter = 'pickup'; render(false); }
        }, 'Intl Pickups')
      )
    );
  }

  function render(animate = true) {
    const d = current;
    results.classList.toggle('still', !animate);
    T.queue.length = 0;
    const q = ($('#q').value || '').trim().toLowerCase();
    const updated = new Date(d.generated_at);
    const ageH = (Date.now() - updated) / 3.6e6;
    const detectedPeriod = (d && d.period) || (d && d.days === 1 ? '24h' : '7d');
    if (period.querySelector(`option[value="${detectedPeriod}"]`)) {
      period.value = detectedPeriod;
    }
    const periodLabel = (period.options[period.selectedIndex] ? period.options[period.selectedIndex].text : (detectedPeriod === '24h' ? 'Last 24 hours' : 'Last 7 days')).toLowerCase();
    const cutoff = periodCutoff(detectedPeriod);
    const windowStories = cutoff ? d.stories.filter((s) => storyRecency(s) >= cutoff) : d.stories;
    let stories = q ? windowStories.filter((s) => matchStory(s, q)) : windowStories;
    if (movementFilter === 'surge_new') {
      stories = stories.filter((s) => s.delta && (s.delta.state === 'surging' || s.delta.state === 'new'));
    } else if (movementFilter === 'pickup') {
      stories = stories.filter((s) => s.delta && s.delta.scope_shift);
    }
    const isFiltered = Boolean(q || movementFilter !== 'all' || windowStories.length !== d.stories.length);
    const count = (id) => (isFiltered ? stories.filter((s) => s.category === id).length : d.totals[id]);
    const noOutside = windowStories.every((s) => !s.by_scope.abroad_local && !s.by_scope.international);
    const byTopic = (id) => stories.filter((s) => s.category === id);
    const totalStories = isFiltered ? stories.length : Object.values(d.totals).reduce((a, b) => a + b, 0);

    const tabs = tabBar(
      [['all', 'All topics', totalStories], ...TOPICS.map((t) => [t.id, t.name, count(t.id), topicVar(t.id)])],
      openTopic,
      (id) => choose(id),
      'Topic',
      'Filter by topic');

    const body = [];
    const staleEmptyMsg = (!q && movementFilter === 'all' && windowStories.length === 0 && d.stories.length > 0)
      ? `No stories in the ${periodLabel} — this snapshot was last updated ${fmtTime.format(updated)}${ageH > STALE_HOURS ? ` (${Math.round(ageH / 24)}d old)` : ''}. Run "python run.py" to collect fresh news.`
      : null;
    if (openTopic === 'all') {
      const order = TOPICS.map((t) => t.id).filter((id) => byTopic(id).length)
        .sort((a, b) => (a === 'other') - (b === 'other') || byTopic(b)[0].score - byTopic(a)[0].score);
      if (order.length) {
        order.forEach((id) => body.push(drawer(id, byTopic(id), count(id), PER_TOPIC_IN_OVERVIEW + (extra[id] || 0))));
      } else {
        body.push(h('p', { class: 'state quiet', text: staleEmptyMsg || (q ? `No stories match "${q}" here.` : `No stories found for ${country.options[country.selectedIndex] ? country.options[country.selectedIndex].text : 'this desk'} in this time period.`) }));
      }
    } else if (byTopic(openTopic).length) {
      const topicStories = byTopic(openTopic);
      const isAll = Boolean(extra[openTopic + '_all']);
      const currentLimit = isAll || topicStories.length <= TOPIC_PAGE_CHUNK ? 0 : Math.min(topicStories.length, TOPIC_PAGE_CHUNK + (extra[openTopic] || 0));
      body.push(drawer(openTopic, topicStories, count(openTopic), currentLimit));
    } else {
      body.push(h('p', { class: 'state', text: staleEmptyMsg || (q ? `No stories match "${q}" here.` : `No ${topicName(openTopic).toLowerCase()} stories in this period.`) }));
    }

    const side = [alerts(), trends(), reddit(), social()].filter(Boolean);

    results.replaceChildren(...[
      fallbackNotice && h('p', { class: 'notice quiet', text: fallbackNotice }),
      h('p', { class: 'result-line' }, h('b', { text: country.options[country.selectedIndex].text }),
        ` · ${periodLabel} · ${plural(totalStories, 'story', 'stories')} found · updated ${fmtTime.format(updated)}${ageH > STALE_HOURS ? ` (${Math.round(ageH / 24)}d old)` : ''} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← All countries overview', onclick: () => openCountry('home') })),
      noOutside && h('p', { class: 'notice quiet', text: `No coverage from ${(index.countries.find((x) => x.id === country.value) || {}).abroad_label || 'outlets abroad'} or from international outlets has been collected for this period yet, so the "not in domestic press" check cannot run.` }),
      watchbar(q),
      agendaBar(d),
      tabs,
      side.length
        ? h('div', { class: 'country-layout' },
            h('div', { class: 'country-main' }, ...body),
            h('aside', { class: 'country-side', 'aria-label': 'Country signals' }, ...side))
        : h('div', { class: 'country-main' }, ...body),
      h('div', { id: 'trans', class: 'trans' }),
    ].filter(Boolean));
    paintTranslationBar();
    translatePending();
  }

  function choose(id) {
    openTopic = id;
    topic.value = id;
    setHash(hashFor(id));
    render(false);
    if (id !== 'all') results.scrollIntoView({ block: 'start' });
  }

  async function research() {
    const slip = $('#slip');
    if (slip) {
      slip.hidden = activeTab !== 'country' && activeTab !== 'home';
      slip.classList.toggle('slip-home', activeTab === 'home');
    }
    fillPeriods();
    if (activeTab === 'country' && country.value) lastCountry = country.value;
    if ($('#nav-home')) $('#nav-home').setAttribute('aria-current', activeTab === 'home' ? 'page' : 'false');
    if ($('#nav-country')) $('#nav-country').setAttribute('aria-current', activeTab === 'country' ? 'page' : 'false');
    if ($('#nav-relations')) $('#nav-relations').setAttribute('aria-current', activeTab === 'relations' ? 'page' : 'false');
    if ($('#nav-alerts')) $('#nav-alerts').setAttribute('aria-current', activeTab === 'alerts' ? 'page' : 'false');
    if ($('#nav-disasters')) $('#nav-disasters').setAttribute('aria-current', activeTab === 'disasters' ? 'page' : 'false');
    if ($('#nav-violence')) $('#nav-violence').setAttribute('aria-current', activeTab === 'violence' ? 'page' : 'false');
    if ($('#brief')) {
      if (activeTab === 'home' || activeTab === 'relations') {
        $('#brief').href = 'brief.html';
      } else if (activeTab === 'alerts' || activeTab === 'disasters' || activeTab === 'violence') {
        $('#brief').href = monitorCountry !== 'all' ? `brief.html#${monitorCountry}` : 'brief.html';
      } else {
        $('#brief').href = `brief.html#${country.value}`;
      }
    }
    if (activeTab === 'home') {
      setHash(hashFor('all'));
      renderHome();
      useLanguage('multi');
      return;
    }
    if (activeTab === 'relations') {
      useLanguage('multi');
      setHash(hashFor('all'));
      renderRelations();
      return;
    }
    if (activeTab === 'alerts') {
      useLanguage('en');
      setHash(hashFor('all'));
      renderAlerts();
      return;
    }
    if (activeTab === 'disasters' || activeTab === 'violence') {
      setHash(hashFor('all'));
      renderEventMonitor(activeTab);
      useLanguage('multi');
      return;
    }
    const c = index.countries.find((x) => x.id === country.value) || index.countries[0];
    const targetFile = `${c.id}-${period.value}.json`;
    useLanguage(c.language);
    openTopic = topic.value;
    setHash(hashFor(topic.value)); extra = {};
    results.replaceChildren(h('p', { class: 'state', text: 'Loading…' }));
    try {
      current = await load(targetFile);
      fallbackNotice = null;
      render();
    } catch {
      try {
        const requestedLabel = period.options[period.selectedIndex] ? period.options[period.selectedIndex].text : '24-hour';
        current = await load(`${c.id}-7d.json`);
        if (period.querySelector('option[value="7d"]')) {
          period.value = '7d';
        }
        fallbackNotice = `No separate ${requestedLabel} snapshot was found for ${c.name}. Showing the last 7 days instead.`;
        render();
      } catch {
        results.replaceChildren(h('p', { class: 'state error',
          text: 'Could not load the results for this choice. Keep the "data" folder next to this page, and run the collector if it is missing.' }));
      }
    }
  }

  // ---------- start ----------
  if (!index) {
    results.replaceChildren(h('p', { class: 'state error', text: 'No data found. Run "python run.py" once, then reload this page.' }));
    return;
  }
  fillCountrySelect(lastCountry || index.countries[0].id);
  setupCountryCombobox();
  fillTopics('all');
  if ($('#alert-count')) { const n = allCrisisAlerts().length; if (n) $('#alert-count').textContent = `[${n}]`; }
  readHash();
  $('#home-link').addEventListener('click', (e) => { e.preventDefault(); openCountry('home'); });
  if ($('#nav-home')) $('#nav-home').addEventListener('click', (e) => { e.preventDefault(); activeTab = 'home'; openCountry('home'); });
  if ($('#nav-country')) $('#nav-country').addEventListener('click', (e) => { e.preventDefault(); activeTab = 'country'; openCountry(lastCountry || index.countries[0].id); });
  if ($('#nav-relations')) $('#nav-relations').addEventListener('click', (e) => { e.preventDefault(); activeTab = 'relations'; openCountry('relations'); });
  if ($('#nav-alerts')) $('#nav-alerts').addEventListener('click', (e) => { e.preventDefault(); activeTab = 'alerts'; openCountry('alerts'); });
  if ($('#nav-disasters')) $('#nav-disasters').addEventListener('click', (e) => { e.preventDefault(); openSubType = 'all'; activeTab = 'disasters'; openCountry('disasters'); });
  if ($('#nav-violence')) $('#nav-violence').addEventListener('click', (e) => { e.preventDefault(); openSubType = 'all'; activeTab = 'violence'; openCountry('violence'); });
  $('#slip').addEventListener('submit', (e) => { e.preventDefault(); research(); });
  country.addEventListener('change', () => {
    openCountry(country.value);
  });
  period.addEventListener('change', research);
  topic.addEventListener('change', research);
  $('#q').addEventListener('input', () => {
    setHash(hashFor(openTopic));
    if (activeTab === 'home') renderHome();
    else if (activeTab === 'relations') renderRelations();
    else if (activeTab === 'alerts') renderAlerts();
    else if (activeTab === 'disasters' || activeTab === 'violence') renderEventMonitor(activeTab);
    else if (current) render(false);
  });
  const totop = $('#totop');
  addEventListener('scroll', () => { totop.hidden = scrollY < 800; }, { passive: true });
  totop.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));
  window.addEventListener('hashchange', () => { readHash(); research(); });
  research();
})();
