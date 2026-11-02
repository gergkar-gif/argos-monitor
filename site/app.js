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
    'Southeast Asia', 'Central Europe', 'Balkans', 'Eastern Europe',
    'South Caucasus', 'Central Asia', 'Middle East & Mediterranean',
    'Sub-Saharan Africa', 'South America'
  ];
  const COUNTRY_REGION = {
    cambodia: 'Southeast Asia', indonesia: 'Southeast Asia', malaysia: 'Southeast Asia', myanmar: 'Southeast Asia',
    philippines: 'Southeast Asia', thailand: 'Southeast Asia', vietnam: 'Southeast Asia',
    hungary: 'Central Europe', poland: 'Central Europe', slovakia: 'Central Europe',
    bosnia: 'Balkans', kosovo: 'Balkans', serbia: 'Balkans',
    moldova: 'Eastern Europe',
    armenia: 'South Caucasus', azerbaijan: 'South Caucasus', georgia: 'South Caucasus',
    kazakhstan: 'Central Asia', kyrgyzstan: 'Central Asia', uzbekistan: 'Central Asia',
    turkey: 'Middle East & Mediterranean',
    ethiopia: 'Sub-Saharan Africa', kenya: 'Sub-Saharan Africa', nigeria: 'Sub-Saharan Africa', south_africa: 'Sub-Saharan Africa',
    argentina: 'South America', brazil: 'South America', colombia: 'South America',
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
      s.src = `data/${key}.js`;
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
  function fillCountrySelect(value) {
    const groups = new Map(REGIONS.map((r) => [r, []]));
    for (const c of index.countries) {
      const r = getRegion(c.id);
      if (!groups.has(r)) groups.set(r, []);
      groups.get(r).push(c);
    }
    country.replaceChildren(
      h('option', { value: 'all', text: 'All Countries' }),
      ...[...groups.entries()].filter(([, list]) => list.length).map(([reg, list]) =>
        h('optgroup', { label: reg }, ...list.map((c) => h('option', { value: c.id, text: c.name }))))
    );
    if (value != null) country.value = value;
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
  function fillPeriods() {
    const c = index.countries.find((x) => x.id === country.value) || index.countries[0];
    fillSelect(period, c.periods.map((p) => [p.id, p.label]), period.value || '7d');
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
    if (activeTab === 'relations') return `#relations/${relCountryA}/${relCountryB}/${relPeriod}`;
    if (activeTab === 'alerts' || activeTab === 'disasters' || activeTab === 'violence') {
      const c = country.value !== 'all' ? country.value : 'all';
      return `#${activeTab}/${c}${qPart}`;
    }
    return `#${country.value}/${period.value}/${t}${qPart}`;
  };
  function readHash() {
    const [c, p, t, q] = location.hash.replace(/^#/, '').split('/');
    if (c === 'relations') {
      activeTab = 'relations';
      country.value = 'all';
      if (p) relCountryA = p;
      if (t) relCountryB = t;
      if (q) relPeriod = q;
    } else if (c === 'alerts' || c === 'disasters' || c === 'violence') {
      activeTab = c;
      country.value = (p && index.countries.some((x) => x.id === p)) ? p : 'all';
      try { $('#q').value = t ? decodeURIComponent(t) : ''; } catch {}
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
      ? [...(hm.most_reported || []), ...(hm.growing || []), ...(hm.abroad_only || [])]
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
      country.value = 'all';
    } else if (cid === 'alerts' || cid === 'disasters' || cid === 'violence') {
      activeTab = cid;
      if (country.value !== 'all' && !index.countries.some((x) => x.id === country.value)) {
        country.value = 'all';
      }
    } else if (cid === 'relations') {
      activeTab = 'relations';
      country.value = 'all';
    } else {
      activeTab = 'country';
      country.value = cid;
      lastCountry = cid;
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
        s.violence_type && h('span', { class: 'stamp red', text: s.violence_type }),
        s.disaster_type && h('span', { class: 'stamp teal', text: s.disaster_type }),
        h('span', { text: `${s.headline.source}, ${fmtDay.format(new Date(s.last_seen))} · ${outlets}` }),
        s.evidence === 'OFFICIAL' && h('span', { class: 'stamp red', title: 'A government or Party outlet is among the sources.', text: 'Official' }),
        s.abroad_only && h('span', { class: 'stamp teal', title: 'No outlet inside the country covered it.', text: 'Not in domestic press' }),
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
        return h('li', null, a, o,
          h('span', { class: 'meta' },
            h('span', { class: 'stamp indigo', text: r.source }),
            r.sim != null && h('span', { class: 'typed', text: `${r.sim}%` }),
            r.published && h('span', { text: fmtTime.format(new Date(r.published)) }),
            r.copy && h('span', { text: 'reprint, counted once' })));
      };
      const details = h('details', null,
        h('summary', { text: `All ${s.articles} articles` }),
        present.length > 1 && h('div', { class: 'cover', 'aria-label': 'Where the coverage comes from' },
          present.map(([id, label]) => h('span', null, h('b', { text: String(s.by_scope[id]) }), ` ${s.by_scope[id] === 1 ? 'article' : 'articles'} from ${label}`))),
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
    const q = fold(($('#q').value || '').trim());
    const filterCountry = country.value !== 'all' ? country.value : null;
    const all = allCrisisAlerts().filter((i) => {
      if (filterCountry && i.cid !== filterCountry) return false;
      return !q || fold(`${i.cname} ${i.region} ${i.kind} ${i.title} ${i.summary || ''}`).includes(q);
    });
    if (openRegion !== 'all' && !all.some((i) => i.region === openRegion)) openRegion = 'all';
    const items = openRegion === 'all' ? all : all.filter((i) => i.region === openRegion);
    const tabs = filterCountry ? null : regionTabs((r) => r === 'all' ? all.length : all.filter((i) => i.region === r).length, renderAlerts);
    const countryName = filterCountry ? prettyName(filterCountry) : null;
    results.replaceChildren(...[
      h('p', { class: 'result-line' },
        h('b', { text: filterCountry ? `Official alerts · ${countryName}` : openRegion === 'all' ? 'Active crisis & official travel alerts' : `Active alerts · ${openRegion}` }),
        ` · ${plural(items.length, 'alert', 'alerts')}${c ? ` · checked ${fmtTime.format(new Date(c.generated_at))}` : ''} · `,
        filterCountry && h('button', { type: 'button', class: 'desk-link', text: `View all country alerts (${allCrisisAlerts().length})`, onclick: () => { country.value = 'all'; research(); } }),
        filterCountry && ' · ',
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      tabs,
      items.length
        ? h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null, ['Country', 'Region', 'Source', 'Alert / Advisory & Details', 'Date'].map((x) => h('th', { text: x })))),
            h('tbody', null, items.map((i) => h('tr', null,
              h('td', null, index.countries.some((x) => x.id === i.cid)
                ? h('button', { type: 'button', class: 'stamp country-tag', text: i.cname, onclick: () => openCountry(i.cid) })
                : h('span', { class: 'stamp', text: i.cname })),
              h('td', { class: 'meta', text: i.region }),
              h('td', null, h('span', { class: 'stamp ' + (isHotAlert(i) ? 'red' : 'indigo'), text: i.kind })),
              h('td', null,
                h('a', { href: safeUrl(i.url), target: '_blank', rel: 'noopener', text: i.title }),
                i.summary && h('p', { class: 'byline', text: i.summary })),
              h('td', { class: 'typed', text: i.date ? fmtDay.format(new Date(i.date)) : '—' }))))))
        : h('p', { class: 'state', text: filterCountry ? `No active official alerts for ${countryName}.` : 'No matching alerts.' }),
      h('p', { class: 'fine', text: 'Sources: Global Disaster Alert and Coordination System (GDACS), US Geological Survey (USGS M4.5+ earthquakes), NASA Earth Observatory (EONET), UK Foreign, Commonwealth & Development Office (FCDO), and US Department of State elevated travel advisories (Levels 2–4).' }),
    ].filter(Boolean));
  }

  // ---------- Disasters & Violent Events (ACLED taxonomy) Monitors ----------
  const DISASTER_RULES = [
    ['Storm & Cyclone', /\b(typhoon|cyclone|hurricane|tropical storm|tornado|gale|bao|sieu bao|ap thap nhiet doi|loc xoay|taufan|badai|bagyo|พายุ|မုန်တိုင်း|vihar|orkan|burza|tufao|ciclone|firtina|kasirga)\b/],
    ['Flood & Landslide', /\b(flood|floods|flooding|flash flood|landslide|mudslide|inundation|lu lut|ngap lut|ngap sau|sat lo|trieu cuong|banjir|longsor|baha|guho|น้ำท่วม|ดินถล่ม|ရေကြီး|arviz|powodz|poplava|heyelan|enchente|deslizamento)/],
    ['Earthquake & Volcano', /\b(earthquake|tremor|seismic|tsunami|volcano|volcanic|eruption|dong dat|nui lua|song than|gempa|gunung berapi|lindol|bulkan|แผ่นดินไหว|ငလျင်|foldrenges|trzesienie ziemi|zemljotres|deprem|yanardag|terremoto|zelzele)/],
    ['Wildfire & Drought', /\b(wildfire|forest fire|bushfire|drought|heatwave|chay rung|han han|kebakaran hutan|kekeringan|ไฟป่า|ภัยแล้ง|erdotuz|aszaly|pozar lasu|susa|orman yangini|kuraklik|incendio florestal|seca\b)/],
  ];
  const VIOLENCE_RULES = [
    ['Armed Clash & Battle', /\b(armed clash|gunbattle|firefight|insurgent|insurgency|rebel|militia|junta troops|ambush|skirmish|giao tranh|dung do|phien quan|kontak tembak|kelompok bersenjata|sagupaan|npa\b|ปะทะ|กองกำลัง|တိုက်ပွဲ|စစ်ကောင်စီ|osszecsapas|sukob|catisma|pkk\b|confronto armado|faccao|fano\b|endf\b|al-shabaab)/],
    ['Explosion & Strike', /\b(airstrike|air strike|drone strike|shelling|missile strike|artillery|mortar|ied\b|landmine|car bomb|bombing|khong kich|phao kich|ten lua|danh bom|serangan udara|rudal|ledakan bom|โจมตีทางอากาศ|ระเบิด|လေကြောင်းတိုက်ခိုက်|legicsapas|raketatamadas|robbanas|nalot|hava saldirisi|patlama|bombali)/],
    ['Terrorism & Attack', /\b(terrorist|terrorism|suicide attack|gunman|gunmen|mass shooting|shooting|massacre|hostage|assassinat|armed attack|khung bo|xa sung|teroris|terorisme|penembakan|terorista|pamamaril|ก่อการร้าย|กราดยิง|အကြမ်းဖက်|merenylet|terrortamadas|lovoldozes|zamach|teror|silahli saldiri|atentado|tiroteio|chacina)/],
    ['Protest & Riot', /\b(riot|riots|violent protest|tear gas|water cannon|clash with police|demonstration|protesters|civil unrest|bieu tinh|bao dong|unjuk rasa|kerusuhan|gas air mata|kilos-protesta|ชุมนุม|ประท้วง|ဆန္ဒပြ|tuntetes|zavargas|konnygaz|zamieszki|protest|gosteri|protesto|საპროტესტო|акция протеста)/],
  ];

  function tagEventStory(s) {
    const th = (s.themes || []).join(' ').toLowerCase();
    if (th.includes('sport') || th.includes('culture')) return s;
    const text = fold([s.headline.title, T.byText.get(s.headline.title) || '', ...(s.sources || []).slice(0, 4).map((r) => r.title)].join(' '));
    const dType = s.disaster_type || (DISASTER_RULES.find(([, re]) => re.test(text)) || [])[0] || null;
    const vType = s.violence_type || (VIOLENCE_RULES.find(([, re]) => re.test(text)) || [])[0] || null;
    return { ...s, disaster_type: dType, violence_type: vType };
  }

  let loadedAll7d = false;
  function collectEventPool(mode) {
    const hm = window.ARGOS_HOME || {};
    const seen = new Set();
    const out = [];
    const key = mode === 'disasters' ? 'disaster_type' : 'violence_type';
    const add = (s, cid, cname, region) => {
      if (!s || seen.has(s.id)) return;
      const tagged = tagEventStory({ ...s, country: s.country || cid, country_name: s.country_name || cname, region: s.region || region || getRegion(s.country || cid) });
      if (tagged[key]) { seen.add(s.id); out.push(tagged); }
    };
    const preset = mode === 'disasters' ? (hm.disasters || []) : (hm.violent_events || []);
    preset.forEach((s) => add(s));
    [...(hm.most_reported || []), ...(hm.growing || []), ...(hm.abroad_only || [])].forEach((s) => add(s));
    for (const c of index.countries) {
      const d = window.ARGOS_DATA && window.ARGOS_DATA[`${c.id}-7d`];
      if (d && d.stories) d.stories.forEach((s) => add(s, c.id, c.name, getRegion(c.id)));
    }
    if (!loadedAll7d) {
      loadedAll7d = true;
      Promise.allSettled(index.countries.map((c) => load(`${c.id}-7d.json`))).then(() => {
        if (activeTab === 'disasters' || activeTab === 'violence') renderEventMonitor(activeTab);
      });
    }
    return out.sort((a, b) => b.independent_sources - a.independent_sources || b.score - a.score);
  }

  function renderEventMonitor(mode) {
    T.queue.length = 0;
    const isDis = mode === 'disasters';
    const rules = isDis ? DISASTER_RULES : VIOLENCE_RULES;
    const key = isDis ? 'disaster_type' : 'violence_type';
    const q = ($('#q').value || '').trim();
    const qf = fold(q);
    const filterCountry = country.value !== 'all' ? country.value : null;
    const allStories = collectEventPool(mode).filter((s) => {
      if (filterCountry && s.country !== filterCountry) return false;
      return !q || matchStory(s, q);
    });
    const allOfficial = allCrisisAlerts().filter((i) => {
      if (filterCountry && i.cid !== filterCountry) return false;
      const hay = fold(`${i.cname} ${i.region} ${i.kind} ${i.title} ${i.summary || ''}`);
      if (qf && !hay.includes(qf)) return false;
      if (isDis) return /^(GDACS|USGS|NASA EONET)$/.test(i.kind) || /\b(disaster|earthquake|flood|typhoon|cyclone|volcano|wildfire)\b/.test(hay);
      return /travel/.test(i.kind.toLowerCase()) && /\b(terror|unrest|conflict|armed|violence|violent|kidnap|crime|martial|security)\b/.test(hay);
    });
    if (openRegion !== 'all' && !allStories.some((s) => s.region === openRegion) && !allOfficial.some((i) => i.region === openRegion)) openRegion = 'all';
    if (openSubType !== 'all' && !rules.some(([label]) => label === openSubType)) openSubType = 'all';
    const inReg = (x) => openRegion === 'all' || x.region === openRegion;
    const regStories = allStories.filter(inReg);
    const stories = openSubType === 'all' ? regStories : regStories.filter((s) => s[key] === openSubType);
    const official = allOfficial.filter(inReg);
    const rTabs = filterCountry ? null : regionTabs((r) => r === 'all'
      ? allStories.length + allOfficial.length
      : allStories.filter((s) => s.region === r).length + allOfficial.filter((i) => i.region === r).length,
      () => renderEventMonitor(mode));
    const subTabs = h('ul', { class: 'tabs', role: 'list', 'aria-label': 'Filter by event type' },
      [['all', 'All types', regStories.length], ...rules.map(([label]) => [label, label, regStories.filter((s) => s[key] === label).length])].map(([id, label, n]) =>
        h('li', null, h('button', { type: 'button', class: 'tab',
          'aria-pressed': String(openSubType === id),
          onclick: () => { openSubType = id; renderEventMonitor(mode); } }, label,
          h('span', { class: 'n', text: String(n) })))));

    const countryName = filterCountry ? prettyName(filterCountry) : null;
    const titleText = filterCountry
      ? (isDis ? `Disasters & Severe Weather · ${countryName}` : `Violent Events · ${countryName}`)
      : (isDis ? 'Natural Disasters & Severe Weather Monitor' : 'Violent Events & Conflict Monitor (ACLED taxonomy)');

    results.replaceChildren(...[
      h('p', { class: 'result-line' },
        h('b', { text: titleText }),
        ` · ${plural(official.length, isDis ? 'official sensor alert' : 'official security advisory', isDis ? 'official sensor alerts' : 'official security advisories')} · ${plural(stories.length, 'reported story cluster', 'reported story clusters')} · `,
        filterCountry && h('button', { type: 'button', class: 'desk-link', text: `View all country ${isDis ? 'disasters' : 'violent events'}`, onclick: () => { country.value = 'all'; research(); } }),
        filterCountry && ' · ',
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      h('div', { id: 'trans', class: 'trans' }),
      rTabs,
      subTabs,
      official.length > 0 && h('section', { class: 'drawer' },
        h('div', { class: 'drawer-head' },
          h('h2', { text: isDis ? 'Official satellite & seismic sensor alerts' : 'Official conflict, terrorism & unrest advisories' }),
          h('span', { class: 'count', text: isDis ? 'GDACS · USGS · NASA EONET' : 'US State Dept · UK FCDO' })),
        h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null, ['Country', 'Region', 'Source', 'Event / Advisory & Details', 'Date'].map((x) => h('th', { text: x })))),
            h('tbody', null, official.map((i) => h('tr', null,
              h('td', null, h('button', { type: 'button', class: 'stamp country-tag', text: i.cname, onclick: () => openCountry(i.cid) })),
              h('td', { class: 'meta', text: i.region }),
              h('td', null, h('span', { class: 'stamp ' + (isHotAlert(i) ? 'red' : 'indigo'), text: i.kind })),
              h('td', null,
                h('a', { href: safeUrl(i.url), target: '_blank', rel: 'noopener', text: i.title }),
                i.summary && h('p', { class: 'byline', text: i.summary })),
              h('td', { class: 'typed', text: i.date ? fmtDay.format(new Date(i.date)) : '—' }))))))),
      stories.length > 0
        ? homeSection(
            isDis ? 'Reported disaster & severe weather clusters (last 7 days)' : 'Reported violent & conflict event clusters (last 7 days)',
            'Ranked by independent outlet count across 248 monitored feeds',
            stories.slice(0, 24))
        : h('p', { class: 'state', text: filterCountry ? `No matching reported events for ${countryName}.` : 'No matching reported story clusters in this filter.' }),
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

  const POPULAR_PAIRS = [
    ['cambodia', 'vietnam', 'Cambodia ⇄ Vietnam'],
    ['cambodia', 'laos', 'Cambodia ⇄ Laos'],
    ['serbia', 'kosovo', 'Serbia ⇄ Kosovo'],
    ['armenia', 'azerbaijan', 'Armenia ⇄ Azerbaijan'],
    ['hungary', 'poland', 'Hungary ⇄ Poland'],
    ['malaysia', 'indonesia', 'Malaysia ⇄ Indonesia'],
    ['colombia', 'argentina', 'Colombia ⇄ Argentina'],
    ['uzbekistan', 'kazakhstan', 'Uzbekistan ⇄ Kazakhstan'],
    ['kenya', 'ethiopia', 'Kenya ⇄ Ethiopia'],
  ];

  let relCountryA = 'cambodia';
  let relCountryB = 'vietnam';
  let relPeriod = '30d';
  let relCustom = '';

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
    const nameA = getCountryName(relCountryA);
    const nameB = relCountryB === 'custom' && relCustom ? relCustom : getCountryName(relCountryB);
    const termsA = getCountryTerms(relCountryA);
    const termsB = relCountryB === 'custom' && relCustom ? [fold(relCustom)] : getCountryTerms(relCountryB);

    const isBMonitored = index.countries.some((x) => x.id === relCountryB);

    const bar = h('div', { class: 'bilateral-bar' },
      h('div', { class: 'bilateral-controls' },
        h('label', { class: 'field' },
          h('span', { text: 'Country A' }),
          h('select', {
            id: 'rel-sel-a',
            onchange: (e) => { relCountryA = e.target.value; setHash(hashFor('all')); renderRelations(); }
          }, ...REGIONS.flatMap((r) => {
            const items = index.countries.filter((c) => getRegion(c.id) === r);
            return items.length ? [h('optgroup', { label: r }, ...items.map((c) => h('option', { value: c.id, text: c.name, selected: c.id === relCountryA })))] : [];
          }))),
        h('button', {
          type: 'button', class: 'bilateral-swap', title: 'Swap Country A and B',
          onclick: () => {
            if (isBMonitored) {
              const tmp = relCountryA; relCountryA = relCountryB; relCountryB = tmp;
              setHash(hashFor('all'));
              renderRelations();
            }
          }
        }, '⇄'),
        h('label', { class: 'field' },
          h('span', { text: 'Country B / Partner' }),
          h('select', {
            id: 'rel-sel-b',
            onchange: (e) => {
              relCountryB = e.target.value;
              setHash(hashFor('all'));
              renderRelations();
            }
          },
            h('optgroup', { label: 'Popular Partners & Powers' },
              ...COMMON_PARTNERS.map((p) => h('option', { value: p.id, text: p.name, selected: p.id === relCountryB }))),
            ...REGIONS.flatMap((r) => {
              const items = index.countries.filter((c) => getRegion(c.id) === r && c.id !== relCountryA);
              return items.length ? [h('optgroup', { label: r }, ...items.map((c) => h('option', { value: c.id, text: c.name, selected: c.id === relCountryB })))] : [];
            }),
            h('optgroup', { label: 'Search' },
              h('option', { value: 'custom', text: 'Custom entity / keyword…', selected: relCountryB === 'custom' })))),
        relCountryB === 'custom' && h('label', { class: 'field' },
          h('span', { text: 'Keyword / Entity' }),
          h('input', {
            type: 'text', placeholder: 'e.g. Laos, ASEAN, IMF', value: relCustom,
            oninput: (e) => { relCustom = e.target.value.trim(); },
            onkeydown: (e) => { if (e.key === 'Enter') { e.preventDefault(); renderRelations(); } }
          })),
        relCountryB === 'custom' && h('button', {
          type: 'button', class: 'research', style: 'height: 2.15rem;',
          onclick: () => renderRelations(), text: 'Search'
        }),
        h('label', { class: 'field' },
          h('span', { text: 'Time Window' }),
          h('select', {
            id: 'rel-sel-period',
            onchange: (e) => { relPeriod = e.target.value; setHash(hashFor('all')); renderRelations(); }
          },
            [['30d', 'Last 30 days'], ['14d', 'Last 14 days'], ['7d', 'Last 7 days']].map(([v, label]) =>
              h('option', { value: v, text: label, selected: v === relPeriod })))),
      ),
      h('div', { class: 'bilateral-pairs' },
        h('span', { class: 'pair-label', text: 'Quick pairs:' }),
        ...POPULAR_PAIRS.map(([ca, cb, label]) => h('button', {
          type: 'button',
          class: 'pair-pill' + (relCountryA === ca && relCountryB === cb ? ' active' : ''),
          text: label,
          onclick: () => {
            relCountryA = ca; relCountryB = cb;
            setHash(hashFor('all'));
            renderRelations();
          }
        }))
      )
    );

    const loadingState = h('p', { class: 'state', text: `Analyzing bilateral reporting between ${nameA} and ${nameB}…` });
    results.replaceChildren(
      h('p', { class: 'result-line' },
        h('b', { text: `Bilateral & Joint Affairs · ${nameA} ⇄ ${nameB}` }),
        ` · ${relPeriod === '30d' ? 'Last 30 days' : relPeriod === '14d' ? 'Last 14 days' : 'Last 7 days'} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
      loadingState
    );

    // Fetch datasets
    const [rawA, rawB] = await Promise.all([
      loadCountryStories(relCountryA, relPeriod),
      isBMonitored ? loadCountryStories(relCountryB, relPeriod) : Promise.resolve([])
    ]);

    // Matching stories
    const matchesTerms = (s, terms) => {
      const txt = storyText(s);
      return terms.some((t) => t && txt.includes(t));
    };

    const storiesA = rawA.filter((s) => matchesTerms(s, termsB));
    const storiesB = rawB.filter((s) => matchesTerms(s, termsA));

    // Global / third-party stories from ARGOS_HOME
    const hm = window.ARGOS_HOME;
    const globalPool = hm ? [...(hm.most_reported || []), ...(hm.growing || []), ...(hm.abroad_only || [])] : [];
    const jointThirdParty = globalPool.filter((s) => {
      if (s.country === relCountryA || (isBMonitored && s.country === relCountryB)) return false;
      return matchesTerms(s, termsA) && matchesTerms(s, termsB);
    });

    const totalCount = storiesA.length + storiesB.length + jointThirdParty.length;

    const content = [];
    if (isBMonitored) {
      content.push(
        h('div', { class: 'bilateral-grid' },
          h('div', { class: 'bilateral-col' },
            h('div', { class: 'bilateral-col-head' },
              h('h2', { text: `${nameA} Media Perspective` }),
              h('span', { text: plural(storiesA.length, 'story', 'stories') })),
            storiesA.length
              ? storiesA.map((s, i) => story(s, { lead: i === 0, i }))
              : h('p', { class: 'state', text: `No stories in ${nameA} media mentioning ${nameB} in the ${relPeriod === '30d' ? 'last 30 days' : relPeriod === '14d' ? 'last 14 days' : 'last 7 days'}.` })),
          h('div', { class: 'bilateral-col' },
            h('div', { class: 'bilateral-col-head' },
              h('h2', { text: `${nameB} Media Perspective` }),
              h('span', { text: plural(storiesB.length, 'story', 'stories') })),
            storiesB.length
              ? storiesB.map((s, i) => story(s, { lead: i === 0, i }))
              : h('p', { class: 'state', text: `No stories in ${nameB} media mentioning ${nameA} in the ${relPeriod === '30d' ? 'last 30 days' : relPeriod === '14d' ? 'last 14 days' : 'last 7 days'}.` })),
        )
      );
    } else {
      content.push(
        h('section', { class: 'drawer' },
          h('div', { class: 'drawer-head' },
            h('h2', { text: `${nameA} Media Coverage of ${nameB}` }),
            h('span', { class: 'count', text: plural(storiesA.length, 'story', 'stories') })),
          storiesA.length
            ? h('div', { class: 'grid' }, storiesA.map((s, i) => story(s, { lead: i === 0, i })))
            : h('p', { class: 'state', text: `No stories in ${nameA} media mentioning "${nameB}" in the ${relPeriod === '30d' ? 'last 30 days' : relPeriod === '14d' ? 'last 14 days' : 'last 7 days'}.` }))
      );
    }

    if (jointThirdParty.length) {
      content.push(
        h('section', { class: 'drawer bilateral-joint' },
          h('div', { class: 'drawer-head' },
            h('h2', { text: `Regional & International Coverage involving both ${nameA} & ${nameB}` }),
            h('span', { class: 'count', text: plural(jointThirdParty.length, 'story', 'stories') })),
          h('div', { class: 'grid' }, jointThirdParty.map((s, i) => story(s, { lead: false, i }))))
      );
    }

    content.push(
      h('p', { class: 'fine' },
        `Cross-country intelligence monitor: cross-references domestic, diaspora, and international reporting across monitored desks to isolate bilateral agreements, diplomatic visits, territorial disputes, and trade interaction without external search engine bias.`
      )
    );

    loadingState.remove();
    results.replaceChildren(
      h('p', { class: 'result-line' },
        h('b', { text: `Bilateral & Joint Affairs · ${nameA} ⇄ ${nameB}` }),
        ` · ${plural(totalCount, 'story', 'stories')} found · ${relPeriod === '30d' ? 'Last 30 days' : relPeriod === '14d' ? 'Last 14 days' : 'Last 7 days'} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      bar,
      ...content
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
    const pool = [...(hm.most_reported || []), ...(hm.abroad_only || []), ...(hm.growing || [])]
      .filter((s, i, a) => inReg(s) && a.findIndex((x) => x.id === s.id) === i);
    const desks = allDesks.filter(inReg);
    const tabs = regionTabs((r) => r === 'all' ? allDesks.length : allDesks.filter((d) => d.region === r).length, renderHome);

    results.replaceChildren(...[
      h('p', { class: 'result-line' },
        h('b', { text: openRegion === 'all' ? 'Overview across all monitored countries' : `Regional Desk · ${openRegion}` }),
        ` · ${plural(desks.length, 'country', 'countries')} · updated ${fmtTime.format(new Date(hm.generated_at))}`),
      h('div', { id: 'trans', class: 'trans' }),
      watchbar(q, pool),
      tabs,
      allAlerts.length > 0 && h('div', { class: 'crisis-strip', role: 'region', 'aria-label': 'Active crisis alerts' },
        h('span', { class: 'stamp red', text: `${plural(allAlerts.length, 'active alert', 'active alerts')}` }),
        h('span', { text: `${allAlerts[0].cname} — ${allAlerts[0].summary || allAlerts[0].title}` }),
        h('button', { type: 'button', class: 'desk-link', text: `All ${allAlerts.length} alerts →`, onclick: () => openCountry('alerts') })),
      homeSection('Most reported (last 7 days)', 'Ranked by independent outlet count', filter(hm.most_reported, openRegion === 'all' ? 8 : 6)),
      homeSection('Fastest growing (last 24 hours)', 'Most new coverage in the last 24 hours', filter(hm.growing, 6)),
      homeSection('Blind spots · Not in domestic press', 'Covered by international or diaspora outlets, zero domestic coverage', filter(hm.abroad_only, 6)),
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
      h('div', { id: 'trans', class: 'trans' }),
      watchbar(q),
      tabs,
      side.length
        ? h('div', { class: 'country-layout' },
            h('div', { class: 'country-main' }, ...body),
            h('aside', { class: 'country-side', 'aria-label': 'Country signals' }, ...side))
        : h('div', { class: 'country-main' }, ...body),
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
    fillPeriods();
    if (activeTab === 'country' && country.value !== 'all') lastCountry = country.value;
    if ($('#nav-home')) $('#nav-home').setAttribute('aria-current', activeTab === 'home' ? 'page' : 'false');
    if ($('#nav-country')) $('#nav-country').setAttribute('aria-current', activeTab === 'country' ? 'page' : 'false');
    if ($('#nav-relations')) $('#nav-relations').setAttribute('aria-current', activeTab === 'relations' ? 'page' : 'false');
    if ($('#nav-alerts')) $('#nav-alerts').setAttribute('aria-current', activeTab === 'alerts' ? 'page' : 'false');
    if ($('#nav-disasters')) $('#nav-disasters').setAttribute('aria-current', activeTab === 'disasters' ? 'page' : 'false');
    if ($('#nav-violence')) $('#nav-violence').setAttribute('aria-current', activeTab === 'violence' ? 'page' : 'false');
    if (activeTab === 'home') {
      $('#brief').href = 'brief.html';
      setHash(hashFor('all'));
      renderHome();
      useLanguage('multi');
      return;
    }
    if (activeTab === 'relations') {
      useLanguage('multi');
      $('#brief').href = 'brief.html';
      setHash(hashFor('all'));
      renderRelations();
      return;
    }
    if (activeTab === 'alerts') {
      useLanguage('en');
      $('#brief').href = country.value !== 'all' ? `brief.html#${country.value}` : 'brief.html';
      setHash(hashFor('all'));
      renderAlerts();
      return;
    }
    if (activeTab === 'disasters' || activeTab === 'violence') {
      $('#brief').href = country.value !== 'all' ? `brief.html#${country.value}` : 'brief.html';
      setHash(hashFor('all'));
      renderEventMonitor(activeTab);
      useLanguage('multi');
      return;
    }
    const c = index.countries.find((x) => x.id === country.value) || index.countries[0];
    const p = c.periods.find((x) => x.id === period.value) || c.periods[0];
    useLanguage(c.language);
    $('#brief').href = `brief.html#${country.value}`;
    openTopic = topic.value;
    setHash(hashFor(topic.value)); extra = {};
    results.replaceChildren(h('p', { class: 'state', text: 'Loading…' }));
    try {
      current = await load(p.file);
      render();
    } catch {
      results.replaceChildren(h('p', { class: 'state error',
        text: 'Could not load the results for this choice. Keep the "data" folder next to this page, and run the collector if it is missing.' }));
    }
  }

  // ---------- start ----------
  if (!index) {
    results.replaceChildren(h('p', { class: 'state error', text: 'No data found. Run "python run.py" once, then reload this page.' }));
    return;
  }
  fillCountrySelect('all');
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
    if (activeTab === 'alerts' || activeTab === 'disasters' || activeTab === 'violence') {
      fillPeriods();
      research();
    } else if (country.value === 'all') {
      openCountry('home');
    } else {
      openCountry(country.value);
    }
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
