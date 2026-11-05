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

  const index = window.ARGOS_INDEX;
  const country = $('#country'), period = $('#period'), topic = $('#topic'), results = $('#results');
  let current = null;   // the loaded data file
  let openTopic = 'all';
  let openRegion = 'all';
  let openSubType = 'all';
  let extra = {};   // extra stories revealed per topic in the overview ("Show more")
  const GLOBAL_VIEWS = new Set(['home', 'alerts', 'disasters', 'violence', 'relations']);

  const REGIONS = [
    'North America', 'Western Europe', 'Central Europe', 'Eastern Europe', 'Balkans',
    'South Caucasus', 'Middle East & Mediterranean', 'Central Asia', 'South Asia',
    'East Asia', 'Southeast Asia', 'Oceania', 'Sub-Saharan Africa', 'South America', 'Caribbean'
  ];
  const COUNTRY_REGION = {
    canada: 'North America', united_states: 'North America',
    finland: 'Western Europe', france: 'Western Europe', germany: 'Western Europe', italy: 'Western Europe',
    netherlands: 'Western Europe', spain: 'Western Europe', sweden: 'Western Europe', switzerland: 'Western Europe', united_kingdom: 'Western Europe',
    czechia: 'Central Europe', hungary: 'Central Europe', poland: 'Central Europe', slovakia: 'Central Europe',
    belarus: 'Eastern Europe', moldova: 'Eastern Europe', russia: 'Eastern Europe', ukraine: 'Eastern Europe',
    bosnia: 'Balkans', kosovo: 'Balkans', serbia: 'Balkans',
    armenia: 'South Caucasus', azerbaijan: 'South Caucasus', georgia: 'South Caucasus',
    egypt: 'Middle East & Mediterranean', iran: 'Middle East & Mediterranean', israel: 'Middle East & Mediterranean',
    lebanon: 'Middle East & Mediterranean', morocco: 'Middle East & Mediterranean',
    qatar: 'Middle East & Mediterranean', saudi_arabia: 'Middle East & Mediterranean', turkey: 'Middle East & Mediterranean',
    united_arab_emirates: 'Middle East & Mediterranean',
    kazakhstan: 'Central Asia', kyrgyzstan: 'Central Asia', uzbekistan: 'Central Asia',
    bangladesh: 'South Asia', india: 'South Asia', pakistan: 'South Asia',
    china: 'East Asia', japan: 'East Asia', north_korea: 'East Asia', south_korea: 'East Asia', taiwan: 'East Asia',
    cambodia: 'Southeast Asia', indonesia: 'Southeast Asia', laos: 'Southeast Asia', malaysia: 'Southeast Asia', myanmar: 'Southeast Asia',
    philippines: 'Southeast Asia', singapore: 'Southeast Asia', thailand: 'Southeast Asia', vietnam: 'Southeast Asia',
    australia: 'Oceania', pacific_islands: 'Oceania',
    ethiopia: 'Sub-Saharan Africa', dr_congo: 'Sub-Saharan Africa', kenya: 'Sub-Saharan Africa', nigeria: 'Sub-Saharan Africa', south_africa: 'Sub-Saharan Africa', west_africa: 'Sub-Saharan Africa',
    argentina: 'South America', brazil: 'South America', chile: 'South America', colombia: 'South America', mexico: 'South America', venezuela: 'South America',
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
    ['14d', 'Past 14 days'],
    ['30d', 'Past 30 days'],
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
  }
  function regionTabs(countFn, onChoose) {
    const active = REGIONS.filter((r) => countFn(r) > 0);
    if (active.length < 2) return null;
    return h('ul', { class: 'tabs', role: 'list', 'aria-label': 'Filter by region' },
      [['all', 'All regions'], ...active.map((r) => [r, r])].map(([id, label]) =>
        h('li', null, h('button', { type: 'button', class: 'tab',
          'aria-pressed': String(openRegion === id),
          onclick: () => { openRegion = id; onChoose(); } }, label,
          h('span', { class: 'n', text: String(countFn(id)) })))));
  }
  const ALL_PERIODS = [
    ['24h', 'Last 24 hours'],
    ['7d', 'Last 7 days'],
    ['14d', 'Last 14 days'],
    ['30d', 'Last 30 days'],
  ];

  function fillPeriods() {
    fillSelect(period, ALL_PERIODS, period.value || '7d');
    period.disabled = topic.disabled = activeTab !== 'country';
  }
  function fillTopics(value) {
    fillSelect(topic, [['all', 'All topics'], ...TOPICS.map((t) => [t.id, t.name])], value);
  }

  let lastCountry = index && index.countries[0] ? index.countries[0].id : '';
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
        monitorPeriod = t;
        try { $('#q').value = q ? decodeURIComponent(q) : ''; } catch {}
      } else {
        try { $('#q').value = t ? decodeURIComponent(t) : ''; } catch {}
      }
    } else if (c === 'home' || !c) {
      activeTab = 'home';
      country.value = 'all';
      try { $('#q').value = p ? decodeURIComponent(p) : ''; } catch {}
    } else {
      activeTab = 'country';
      const cid = c === 'country' ? (lastCountry || index.countries[0].id) : (index.countries.some((x) => x.id === c) ? c : index.countries[0].id);
      country.value = cid;
      lastCountry = cid;
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
    } else if (cid === 'alerts' || cid === 'disasters' || cid === 'violence') {
      activeTab = cid;
    } else if (cid === 'relations') {
      activeTab = 'relations';
    } else {
      activeTab = 'country';
      if (cid && index.countries.some((x) => x.id === cid)) {
        country.value = cid;
        lastCountry = cid;
      }
    }
    fillPeriods();
    research();
    scrollTo({ top: 0, behavior: 'smooth' });
  }

  function story(s, opts) {
    const sc = scopes(s.country || country.value);
    const present = sc.filter(([id]) => s.by_scope[id]);
    const single = present.length === 1 ? present[0][1] : '';
    const outlets = plural(s.independent_sources, 'independent outlet', 'independent outlets');
    const clip = h('article', { class: 'clip' + (opts.lead ? ' lead' : ''), style: `--i:${opts.i}` });

    const headLink = h('a', { href: safeUrl(s.headline.url), target: '_blank', rel: 'noopener', lang: s.headline.language, text: s.headline.title });
    const headOrig = h('p', { class: 'orig', hidden: true, title: 'Original headline' });
    track(headLink, s.headline.title, s.headline.language, headOrig);
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
          x.source !== s.headline.source && h('footer', null, h('a', { class: 'stamp indigo', href: safeUrl(x.url), target: '_blank', rel: 'noopener', text: x.source })));
      })),
      h('div', { class: 'slipline' },
        s.country_name && h('button', { type: 'button', class: 'stamp country-tag', title: `Open ${s.country_name} monitor`, text: s.country_name, onclick: () => openCountry(s.country) }),
        s.disaster_type && h('span', { class: 'stamp teal', text: s.disaster_type }),
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
        trend(s) && trend(s)[0] !== 'Quiet' && h('span', { class: 'stamp indigo', title: trend(s)[2], text: trend(s)[0] }),
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
        const a = h('a', { class: 't', href: safeUrl(r.url), target: '_blank', rel: 'noopener', lang: r.language, text: r.title });
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
          h('span', null, h('a', { href: safeUrl(r.url), target: '_blank', rel: 'noopener', text: r.title }), ` (${plural(r.articles, 'article', 'articles')}, ${r.source}) `))),
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
    const sec = h('section', { class: 'drawer', style: topicVar(id), 'aria-labelledby': `d-${id}` },
      h('div', { class: 'drawer-head' },
        h('h2', { id: `d-${id}`, text: topicName(id) }),
        h('span', { class: 'count', text: `Top ${shown.length} of ${total} stories` })),
      h('div', { class: 'grid' }, shown.map((s, i) => story(s, { lead: i === 0, i }))),
    );
    if (limit && stories.length > limit) {
      sec.append(
        h('button', { type: 'button', class: 'more', onclick: () => { extra[id] = (extra[id] || 0) + 8; render(false); }, text: `Show ${Math.min(8, stories.length - limit)} more` }),
        h('button', { type: 'button', class: 'more', onclick: () => choose(id), text: `Open all ${topicName(id)}` }));
    }
    return sec;
  }

  const fold = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/ł/g, 'l').replace(/ı/g, 'i');
  const trText = (t) => (t ? `${t} ${T.byText.get(t) || ''}` : '');
  const storyText = (s) => fold([
    s.country_name || '',
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
        const a = h('a', { href: safeUrl(x.url), target: '_blank', rel: 'noopener', lang: cLang, text: x.title });
        const origEl = h('span', { class: 'orig', hidden: true });
        track(a, x.title, cLang, origEl);
        return h('li', null,
          x.sub && h('span', { class: 'stamp indigo', text: `r/${x.sub}` }),
          x.tag && h('span', { class: 'stamp', text: x.tag }),
          a, origEl);
      })),
      h('p', { class: 'byline', text: `Desk-relevant posts across ${r.subreddit}. Unverified.` }));
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
  const isHotAlert = (i) => /^(Red|Orange)$/.test(i.level || '') || /Level [34]/.test(i.title);
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
        h('a', { href: safeUrl(item.url), target: '_blank', rel: 'noopener', text: item.title }),
        item.summary && h('p', { class: 'byline', text: item.summary })))));
  }

  function renderAlerts() {
    const c = getCrisis();
    const filterCountry = monitorCountry !== 'all' ? monitorCountry : null;
    const cutoff = periodCutoff(monitorPeriod);
    const all = allCrisisAlerts().filter((i) => {
      if (filterCountry && i.cid !== filterCountry) return false;
      if (cutoff && i.date && new Date(i.date).getTime() < cutoff) return false;
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
        h('b', { text: filterCountry ? `Official alerts · ${countryName}` : 'Active crisis & official travel alerts' }),
        ` · ${periodLabel} · ${plural(all.length, 'alert', 'alerts')}${c ? ` · checked ${fmtTime.format(new Date(c.generated_at))}` : ''} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
      all.length
        ? h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null, ['Country', 'Region', 'Source', 'Alert / Advisory & Details', 'Date'].map((x) => h('th', { text: x })))),
            h('tbody', null, all.map((i) => h('tr', null,
              h('td', null, index.countries.some((x) => x.id === i.cid)
                ? h('button', { type: 'button', class: 'stamp country-tag', text: i.cname, onclick: () => { monitorCountry = i.cid; setHash(hashFor('all')); renderAlerts(); } })
                : h('span', { class: 'stamp', text: i.cname })),
              h('td', { class: 'meta', text: i.region }),
              h('td', null, h('span', { class: 'stamp ' + (isHotAlert(i) ? 'red' : 'indigo'), text: i.kind })),
              h('td', null,
                h('a', { href: safeUrl(i.url), target: '_blank', rel: 'noopener', text: i.title }),
                i.summary && h('p', { class: 'byline', text: i.summary })),
              h('td', { class: 'typed', text: i.date ? fmtDay.format(new Date(i.date)) : '—' }))))))
        : h('p', { class: 'state', text: filterCountry ? `No active official alerts for ${countryName}.` : 'No matching alerts.' }),
      h('p', { class: 'fine', text: 'Sources: Global Disaster Alert and Coordination System (GDACS), US Geological Survey (USGS M4.5+ earthquakes), NASA Earth Observatory (EONET), International Crisis Group, UK Foreign, Commonwealth & Development Office (FCDO), and US Department of State elevated travel advisories (Levels 2–4).' }),
    ].filter(Boolean));
  }

  // ---------- Disasters & Conflict/Security Monitors ----------
  const DISASTER_RULES = [
    ['Storm & Cyclone', /\b(typhoon|cyclone|hurricane|tropical storm|tornado|gale|sieu bao|ap thap nhiet doi|loc xoay|con bao|taufan|badai|bagyo|พายุ|မုန်တိုင်း|vihar|orkan|burza|tufao|ciclone|firtina|kasirga)\b/],
    ['Flood & Landslide', /\b(flood|floods|flooding|flash flood|landslide|mudslide|inundation|lu lut|ngap lut|ngap sau|sat lo|trieu cuong|banjir|longsor|baha|guho|น้ำท่วม|ดินถล่ม|ရေကြီး|arviz|powodz|poplava|heyelan|enchente|deslizamento)/],
    ['Earthquake & Volcano', /\b(earthquake|tremor|seismic|tsunami|volcano|volcanic|eruption|dong dat|nui lua|song than|gempa|gunung berapi|lindol|bulkan|แผ่นดินไหว|ငလျင်|foldrenges|trzesienie ziemi|zemljotres|deprem|yanardag|terremoto|zelzele)/],
    ['Wildfire & Drought', /\b(wildfire|forest fire|bushfire|drought|heatwave|chay rung|han han|kebakaran hutan|kekeringan|ไฟป่า|ภัยแล้ง|erdotuz|aszaly|pozar lasu|susa|orman yangini|kuraklik|incendio florestal|seca\b)/],
  ];

  function tagEventStory(s) {
    const th = (s.themes || []).join(' ').toLowerCase();
    if (th.includes('sport') || th.includes('culture')) return s;
    const text = fold([s.headline.title, T.byText.get(s.headline.title) || '', ...(s.sources || []).slice(0, 4).map((r) => r.title)].join(' '));
    const dType = s.disaster_type || (DISASTER_RULES.find(([, re]) => re.test(text)) || [])[0] || null;
    return { ...s, disaster_type: dType };
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
      const tagged = isDis
        ? tagEventStory({ ...s, country: s.country || cid, country_name: s.country_name || cname, region: s.region || region || getRegion(s.country || cid) })
        : { ...s, country: s.country || cid, country_name: s.country_name || cname, region: s.region || region || getRegion(s.country || cid) };
      const keep = isDis ? Boolean(tagged.disaster_type) : (tagged.category === 'defence_security' || (tagged.themes || []).includes('Security and defence'));
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
      if (cutoff && i.date && new Date(i.date).getTime() < cutoff) return false;
      const hay = fold(`${i.cname} ${i.region} ${i.kind} ${i.title} ${i.summary || ''}`);
      if (isDis) return /^(GDACS|USGS|NASA EONET)$/.test(i.kind) || /\b(disaster|earthquake|flood|typhoon|cyclone|volcano|wildfire)\b/.test(hay);
      return /travel|crisis group/i.test(i.kind) || /\b(terror|unrest|conflict|armed|violence|violent|kidnap|crime|martial|security|war)\b/.test(hay);
    });
    allOfficial.sort((a, b) => new Date(b.date || 0).getTime() - new Date(a.date || 0).getTime());

    if (isDis && openSubType !== 'all' && !DISASTER_RULES.some(([label]) => label === openSubType)) openSubType = 'all';
    const stories = isDis && openSubType !== 'all' ? allStories.filter((s) => s.disaster_type === openSubType) : allStories;
    const subTabs = isDis
      ? h('ul', { class: 'tabs', role: 'list', 'aria-label': 'Filter by event type' },
          [['all', 'All types', allStories.length], ...DISASTER_RULES.map(([label]) => [label, label, allStories.filter((s) => s.disaster_type === label).length])].map(([id, label, n]) =>
            h('li', null, h('button', { type: 'button', class: 'tab',
              'aria-pressed': String(openSubType === id),
              onclick: () => { openSubType = id; renderEventMonitor(mode); } }, label,
              h('span', { class: 'n', text: String(n) })))))
      : null;

    const countryName = filterCountry ? prettyName(filterCountry) : null;
    const periodLabel = (MONITOR_PERIODS.find(([v]) => v === monitorPeriod) || [])[1] || 'Past 7 days';
    const titleText = filterCountry
      ? (isDis ? `Disasters & Severe Weather · ${countryName}` : `Conflict & Security · ${countryName}`)
      : (isDis ? 'Natural Disasters & Severe Weather Monitor' : 'Conflict & Security Monitor (Official Advisories & Press)');

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
        ` · ${periodLabel} · ${plural(allOfficial.length, isDis ? 'official sensor alert' : 'official advisory & conflict report', isDis ? 'official sensor alerts' : 'official advisories & conflict reports')} · ${plural(stories.length, isDis ? 'reported disaster cluster' : 'reported defence & security cluster', isDis ? 'reported disaster clusters' : 'reported defence & security clusters')} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
      subTabs,
      allOfficial.length > 0 && h('section', { class: 'drawer' },
        h('div', { class: 'drawer-head' },
          h('h2', { text: isDis ? 'Official satellite & seismic sensor alerts' : 'Official conflict, terrorism & unrest advisories' }),
          h('span', { class: 'count', text: isDis ? 'GDACS · USGS · NASA EONET' : 'US State Dept · UK FCDO · Crisis Group' })),
        h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null, ['Country', 'Region', 'Source', 'Event / Advisory & Details', 'Date'].map((x) => h('th', { text: x })))),
            h('tbody', null, allOfficial.map((i) => h('tr', null,
              h('td', null, h('button', { type: 'button', class: 'stamp country-tag', text: i.cname, onclick: () => { monitorCountry = i.cid; setHash(hashFor('all')); renderEventMonitor(mode); } })),
              h('td', { class: 'meta', text: i.region }),
              h('td', null, h('span', { class: 'stamp ' + (isHotAlert(i) ? 'red' : 'indigo'), text: i.kind })),
              h('td', null,
                h('a', { href: safeUrl(i.url), target: '_blank', rel: 'noopener', text: i.title }),
                i.summary && h('p', { class: 'byline', text: i.summary })),
              h('td', { class: 'typed', text: i.date ? fmtDay.format(new Date(i.date)) : '—' }))))))),
      stories.length > 0
        ? homeSection(
            isDis ? 'Reported disaster & severe weather clusters (most recent first)' : 'Reported defence & security story clusters (most recent first)',
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
    { id: 'laos', name: 'Laos', terms: ['laos', 'lao', 'vientiane', 'lào', 'ລາວ'] },
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

  function getCountryName(id) {
    const c = index.countries.find((x) => x.id === id);
    if (c) return c.name;
    const p = COMMON_PARTNERS.find((x) => x.id === id);
    if (p) return p.name;
    return id ? id.charAt(0).toUpperCase() + id.slice(1) : '';
  }

  function getCountryTerms(id) {
    const c = index.countries.find((x) => x.id === id);
    if (c) {
      const list = [fold(c.name), fold(c.id), ...(c.mentions || []).map(fold)];
      return [...new Set(list.filter((x) => x && x.length > 2))];
    }
    const p = COMMON_PARTNERS.find((x) => x.id === id);
    if (p) {
      const list = [fold(p.name), fold(p.id), ...p.terms.map(fold)];
      return [...new Set(list.filter((x) => x && x.length > 2))];
    }
    if (id) {
      return [fold(id)];
    }
    return [];
  }

  async function loadCountryStories(cid, per) {
    const c = index.countries.find((x) => x.id === cid);
    if (!c) return [];
    const p = c.periods.find((x) => x.id === per) || c.periods.find((x) => x.id === '30d') || c.periods.find((x) => x.id === '7d') || c.periods[0];
    if (!p) return [];
    try {
      const d = await load(p.file);
      return (d && d.stories) || [];
    } catch {
      return [];
    }
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

    // Deduplicate stories by url / title
    const seen = new Set();
    const candidateStories = [];
    for (const s of pool) {
      const key = s.url || (s.title + (s.country || ''));
      if (!seen.has(key)) {
        seen.add(key);
        candidateStories.push(s);
      }
    }

    // Matching: story must involve EVERY selected country
    const termsMap = new Map(selectedCountries.map((cid) => [cid, getCountryTerms(cid)]));
    const storyInvolvesCountry = (s, cid) => {
      if (s.country === cid) return true;
      const terms = termsMap.get(cid) || [];
      const txt = storyText(s);
      return terms.some((t) => t && txt.includes(t));
    };

    const matchedStories = candidateStories.filter((s) =>
      selectedCountries.every((cid) => storyInvolvesCountry(s, cid))
    );

    // Sort by recency
    matchedStories.sort((a, b) => new Date(b.date || 0).getTime() - new Date(a.date || 0).getTime());

    loadingState.remove();
    results.replaceChildren(
      h('p', { class: 'result-line' },
        h('b', { text: `Joint & Multilateral Affairs · ${titleStr}` }),
        ` · ${plural(matchedStories.length, 'story', 'stories')} found · ${relPeriod === '24h' ? 'Last 24 hours' : 'Last 7 days'} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
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
    const allDesks = [...(hm.desks || [])].map((d) => ({ ...d, region: d.region || getRegion(d.id) })).sort((a, b) => b.stories_7d - a.stories_7d);
    if (openRegion !== 'all' && !allDesks.some((d) => d.region === openRegion)) openRegion = 'all';
    const inReg = (x) => openRegion === 'all' || (x.region || getRegion(x.country || x.id)) === openRegion;
    const filter = (arr, limit) => (arr || [])
      .filter((s) => inReg(s) && (!q || matchStory(s, q)))
      .slice(0, limit);
    const c = getCrisis();
    const allAlerts = allCrisisAlerts().filter(inReg);
    const pool = [...(hm.most_reported || []), ...(hm.growing || [])]
      .filter((s, i, a) => inReg(s) && a.findIndex((x) => x.id === s.id) === i);
    const desks = allDesks.filter(inReg);
    const tabs = regionTabs((r) => r === 'all' ? allDesks.length : allDesks.filter((d) => d.region === r).length, renderHome);

    results.replaceChildren(...[
      h('p', { class: 'result-line' },
        h('b', { text: openRegion === 'all' ? 'Overview across all monitored countries' : `Regional Desk · ${openRegion}` }),
        ` · ${plural(desks.length, 'country', 'countries')} · updated ${fmtTime.format(new Date(hm.generated_at))}`),
      watchbar(q, pool),
      tabs,
      allAlerts.length > 0 && h('div', { class: 'crisis-strip', role: 'region', 'aria-label': 'Active crisis alerts' },
        h('span', { class: 'stamp red', text: `${plural(allAlerts.length, 'active alert', 'active alerts')}` }),
        h('span', { text: `${allAlerts[0].cname} — ${allAlerts[0].summary || allAlerts[0].title}` }),
        h('button', { type: 'button', class: 'desk-link', text: `All ${allAlerts.length} alerts →`, onclick: () => openCountry('alerts') })),
      homeSection('Most reported (last 7 days)', 'Ranked by independent outlet count', filter(hm.most_reported, openRegion === 'all' ? 8 : 6)),
      homeSection('Fastest growing (last 24 hours)', 'Most new coverage in the last 24 hours', filter(hm.growing, 6)),
      h('section', { class: 'drawer' },
        h('div', { class: 'drawer-head' },
          h('h2', { text: 'Monitored countries directory' }),
          h('span', { class: 'count', text: `${desks.length} active packs` })),
        h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null,
              h('th', { text: 'Country' }),
              h('th', { text: 'Region' }),
              h('th', { text: '24h' }),
              h('th', { text: '7d' }),
              h('th', { text: 'Alerts' }),
              h('th', { text: 'Lead story (7d)' }))),
            h('tbody', null, desks.map((d) => {
              const nAlerts = (c && c.countries && c.countries[d.id] || []).length;
              return h('tr', null,
                h('td', null, h('button', { type: 'button', class: 'desk-link', text: `${d.name} →`, onclick: () => openCountry(d.id) })),
                h('td', { class: 'meta', text: d.region }),
                h('td', { class: 'typed', text: String(d.stories_24h) }),
                h('td', { class: 'typed', text: String(d.stories_7d) }),
                h('td', null, nAlerts ? h('span', { class: 'stamp red', text: String(nAlerts) }) : h('span', { class: 'meta', text: '—' })),
                h('td', null, d.lead ? (() => {
                  const cl = (index.countries.find((x) => x.id === d.id) || {}).language || 'en';
                  const a = h('a', { href: safeUrl(d.lead.url), target: '_blank', rel: 'noopener', lang: cl, text: d.lead.title });
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

  function render(animate = true) {
    const d = current;
    results.classList.toggle('still', !animate);
    T.queue.length = 0;
    const q = ($('#q').value || '').trim().toLowerCase();
    const stories = q ? d.stories.filter((s) => matchStory(s, q)) : d.stories;
    const count = (id) => (q ? stories.filter((s) => s.category === id).length : d.totals[id]);
    const noOutside = d.stories.every((s) => !s.by_scope.abroad_local && !s.by_scope.international);
    const byTopic = (id) => stories.filter((s) => s.category === id);
    const totalStories = q ? stories.length : Object.values(d.totals).reduce((a, b) => a + b, 0);
    const updated = new Date(d.generated_at);
    const ageH = (Date.now() - updated) / 3.6e6;
    const periodLabel = period.options[period.selectedIndex].text.toLowerCase();

    const tabs = h('ul', { class: 'tabs', role: 'list' },
      [['all', 'All topics'], ...TOPICS.map((t) => [t.id, t.name])].map(([id, label]) =>
        h('li', null, h('button', { type: 'button', class: 'tab', style: id === 'all' ? '' : topicVar(id),
          'aria-pressed': String(openTopic === id), onclick: () => choose(id) }, label,
          h('span', { class: 'n', text: String(id === 'all' ? totalStories : count(id)) })))));

    const body = [];
    if (openTopic === 'all') {
      const order = TOPICS.map((t) => t.id).filter((id) => byTopic(id).length)
        .sort((a, b) => (a === 'other') - (b === 'other') || byTopic(b)[0].score - byTopic(a)[0].score);
      order.forEach((id) => body.push(drawer(id, byTopic(id), count(id), PER_TOPIC_IN_OVERVIEW + (extra[id] || 0))));
    } else if (byTopic(openTopic).length) {
      body.push(drawer(openTopic, byTopic(openTopic), count(openTopic), 0));
    } else {
      body.push(h('p', { class: 'state', text: q ? `No stories match "${q}" here.` : `No ${topicName(openTopic).toLowerCase()} stories in this period.` }));
    }

    const side = [alerts(), trends(), reddit()].filter(Boolean);

    results.replaceChildren(...[
      h('p', { class: 'result-line' }, h('b', { text: country.options[country.selectedIndex].text }),
        ` · ${periodLabel} · ${plural(totalStories, 'story', 'stories')} found · updated ${fmtTime.format(updated)}${ageH > STALE_HOURS ? ` (${Math.round(ageH / 24)}d old)` : ''} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← All countries overview', onclick: () => openCountry('home') })),
      noOutside && h('p', { class: 'notice quiet', text: `No coverage from ${(index.countries.find((x) => x.id === country.value) || {}).abroad_label || 'outlets abroad'} or from international outlets has been collected for this period yet, so the "not in domestic press" check cannot run.` }),
      watchbar(q),
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
    if (slip) slip.hidden = activeTab !== 'country';
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
      render();
    } catch {
      try {
        current = await load(`${c.id}-7d.json`);
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
