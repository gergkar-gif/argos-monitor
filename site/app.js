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
  let extra = {};   // extra stories revealed per topic in the overview ("Show more")

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
  function fillPeriods() {
    const c = index.countries.find((x) => x.id === country.value) || index.countries[0];
    fillSelect(period, c.periods.map((p) => [p.id, p.label]), period.value || '7d');
    period.disabled = topic.disabled = country.value === 'home' || country.value === 'alerts';
  }
  function fillTopics(value) {
    fillSelect(topic, [['all', 'All topics'], ...TOPICS.map((t) => [t.id, t.name])], value);
  }

  const hashFor = (t) => (country.value === 'home' || country.value === 'alerts'
    ? `#${country.value}` + ($('#q').value.trim() ? `///${encodeURIComponent($('#q').value.trim())}` : '')
    : `#${country.value}/${period.value}/${t}` + ($('#q').value.trim() ? `/${encodeURIComponent($('#q').value.trim())}` : ''));
  function readHash() {
    const [c, p, t, q] = location.hash.replace(/^#/, '').split('/');
    try { $('#q').value = q ? decodeURIComponent(q) : ''; } catch { /* bad link text: ignore */ }
    country.value = c === 'alerts' ? 'alerts' : (c && index.countries.some((x) => x.id === c) ? c : 'home');
    fillPeriods();
    if (p && [...period.options].some((o) => o.value === p)) period.value = p;
    if (t && (t === 'all' || TOPICS.some((x) => x.id === t))) topic.value = t;
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

  const T = { lang: 'en', state: 'checking', translators: new Map(), cache: new Map(), queue: [], running: false };
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
        it.el.textContent = en;
        it.el.lang = 'en';
        it.origEl.textContent = it.text;
        it.origEl.lang = it.lang;
        it.origEl.hidden = false;
      } catch { /* keep the original text as it is */ }
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
    } else if (T.state === 'none') {
      bar.replaceChildren(h('p', { class: 'notice quiet', text: 'Your browser cannot translate on its own device here, so headlines show in the original language. Use the browser\'s Translate feature (Chrome or Edge on a computer work best).' }));
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
    country.value = cid;
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
        h('ul', { class: 'sources' }, rest.map((r) => {
          const a = h('a', { class: 't', href: safeUrl(r.url), target: '_blank', rel: 'noopener', lang: r.language, text: r.title });
          const o = h('span', { class: 'orig', hidden: true, title: 'Original headline' });
          lateItems.push([a, r.title, r.language, o]);
          return h('li', null, a, o,
          h('span', { class: 'meta' },
            h('span', { class: 'stamp indigo', text: r.source }),
            r.published && h('span', { text: fmtTime.format(new Date(r.published)) }),
            r.copy && h('span', { text: 'reprint, counted once' })));
        })),
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

  const storyText = (s) => [s.country_name || '', s.headline.title, ...(s.sources || []).map((r) => r.title + ' ' + r.source), ...(s.excerpts || []).map((x) => x.text)].join(' ').toLowerCase();

  function trends() {
    const tr = (window.ARGOS_TRENDS && (window.ARGOS_TRENDS.countries || (window.ARGOS_TRENDS.trends || {}).countries) || {})[country.value];
    if (!tr || !tr.length) return null;
    return h('section', { class: 'alerts', 'aria-label': 'Trending searches' },
      h('h2', { text: 'Trending searches' }),
      h('ul', null, tr.map((x) => {
        const n = current.stories.filter((s) => storyText(s).includes(x.term.toLowerCase())).length;
        return h('li', null,
          h('span', { text: x.term }),
          x.traffic && h('span', { class: 'meta', text: `${x.traffic} searches` }),
          n ? h('button', { type: 'button', class: 'more', text: `${plural(n, 'story', 'stories')} here`,
            onclick: () => { $('#q').value = x.term; setHash(hashFor(openTopic)); render(false); results.scrollIntoView({ block: 'start' }); } })
            : h('span', { class: 'meta', text: 'no matching story' }),
          x.url && h('a', { href: safeUrl(x.url), target: '_blank', rel: 'noopener', text: x.source || 'news' }));
      })),
      h('p', { class: 'byline', text: 'Google Trends, top searches in the country right now. Matching is by exact words in our headlines and quotes.' }));
  }

  function reddit() {
    const r = (window.ARGOS_REDDIT && (window.ARGOS_REDDIT.countries || (window.ARGOS_REDDIT.reddit || {}).countries) || {})[country.value];
    if (!r || !r.posts.length) return null;
    const label = r.subreddit.startsWith('r/') ? r.subreddit : `r/${r.subreddit}`;
    return h('section', { class: 'alerts', 'aria-label': 'On Reddit' },
      h('h2', { text: `On Reddit today · ${label}` }),
      h('ul', null, r.posts.map((x) => h('li', null,
        x.sub && h('span', { class: 'stamp indigo', text: `r/${x.sub}` }),
        h('a', { href: safeUrl(x.url), target: '_blank', rel: 'noopener', text: x.title })))),
      h('p', { class: 'byline', text: 'Top posts of the day across these communities. What people discuss, not verified news.' }));
  }

  const watched = () => { try { return JSON.parse(localStorage.getItem('argos.watch') || '[]'); } catch { return []; } };
  function setWatched(list) {
    try { localStorage.setItem('argos.watch', JSON.stringify(list)); } catch { /* storage not available: ignore */ }
    country.value === 'home' ? renderHome() : render(false);
  }
  function watchbar(q, pool = current ? current.stories : []) {
    const list = watched();
    if (!list.length && !q) return null;
    return h('div', { class: 'watch' },
      h('span', { class: 'meta', text: 'Watching' }),
      list.map((w) => h('span', { class: 'chip' },
        h('button', { type: 'button', class: 'more', title: 'Show these stories',
          text: `${w} (${pool.filter((s) => storyText(s).includes(w)).length})`,
          onclick: () => { $('#q').value = w; setHash(hashFor(openTopic)); country.value === 'home' ? renderHome() : render(false); } }),
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
        const cname = (index.countries.find((x) => x.id === cid) || {}).name || cid;
        for (const item of list) out.push({ ...item, cid, cname });
      }
    }
    return out.sort((a, b) => isHotAlert(b) - isHotAlert(a));
  }

  function alerts() {
    const c = getCrisis();
    if (!c) return null;
    const items = c.countries[country.value] || [];
    if (!items.length) return null;
    const first = items[0];
    return h('div', { class: 'crisis-strip', role: 'region', 'aria-label': 'Official alerts' },
      h('span', { class: 'stamp ' + (items.some(isHotAlert) ? 'red' : 'indigo'), text: `${plural(items.length, 'official alert', 'official alerts')}` }),
      h('span', { class: 'stamp indigo', text: first.kind }),
      h('a', { href: safeUrl(first.url), target: '_blank', rel: 'noopener', text: first.title }),
      first.summary && h('span', { class: 'meta', text: `— ${first.summary}` }),
      items.length > 1 && h('button', { type: 'button', class: 'desk-link', text: `+${items.length - 1} more →`, onclick: () => openCountry('alerts') }));
  }

  function renderAlerts() {
    const c = getCrisis();
    const q = ($('#q').value || '').trim().toLowerCase();
    const items = allCrisisAlerts().filter((i) => !q || `${i.cname} ${i.kind} ${i.title} ${i.summary || ''}`.toLowerCase().includes(q));
    results.replaceChildren(
      h('p', { class: 'result-line' },
        h('b', { text: 'Active crisis & official travel alerts' }),
        ` · ${plural(items.length, 'alert', 'alerts')}${c ? ` · checked ${fmtTime.format(new Date(c.generated_at))}` : ''} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← Back to Overview', onclick: () => openCountry('home') })),
      items.length
        ? h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null, ['Country', 'Source', 'Alert / Advisory & Details', 'Date'].map((x) => h('th', { text: x })))),
            h('tbody', null, items.map((i) => h('tr', null,
              h('td', null, h('button', { type: 'button', class: 'stamp country-tag', text: i.cname, onclick: () => openCountry(i.cid) })),
              h('td', null, h('span', { class: 'stamp ' + (isHotAlert(i) ? 'red' : 'indigo'), text: i.kind })),
              h('td', null,
                h('a', { href: safeUrl(i.url), target: '_blank', rel: 'noopener', text: i.title }),
                i.summary && h('p', { class: 'byline', text: i.summary })),
              h('td', { class: 'typed', text: i.date ? fmtDay.format(new Date(i.date)) : '—' }))))))
        : h('p', { class: 'state', text: 'No matching alerts.' }),
      h('p', { class: 'fine', text: 'Sources: Global Disaster Alert and Coordination System (GDACS), US Geological Survey (USGS M4.5+ earthquakes), UK Foreign, Commonwealth & Development Office (FCDO updates within 30 days), and US Department of State elevated travel advisories (Levels 2–4).' }));
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
    const filter = (arr) => (q ? (arr || []).filter((s) => storyText(s).includes(q)) : (arr || []));
    const c = getCrisis();
    const allAlerts = allCrisisAlerts();
    const pool = [...(hm.most_reported || []), ...(hm.abroad_only || []), ...(hm.growing || [])]
      .filter((s, i, a) => a.findIndex((x) => x.id === s.id) === i);

    const desks = [...(hm.desks || [])].sort((a, b) => b.stories_7d - a.stories_7d);

    results.replaceChildren(...[
      h('p', { class: 'result-line' },
        h('b', { text: 'Overview across all monitored countries' }),
        ` · ${plural(desks.length, 'country', 'countries')} · updated ${fmtTime.format(new Date(hm.generated_at))}`),
      h('div', { id: 'trans', class: 'trans' }),
      watchbar(q, pool),
      allAlerts.length > 0 && h('div', { class: 'crisis-strip', role: 'region', 'aria-label': 'Active crisis alerts' },
        h('span', { class: 'stamp red', text: `${plural(allAlerts.length, 'active alert', 'active alerts')}` }),
        h('span', { text: `${allAlerts[0].cname} — ${allAlerts[0].summary || allAlerts[0].title}` }),
        h('button', { type: 'button', class: 'desk-link', text: `All ${allAlerts.length} alerts →`, onclick: () => openCountry('alerts') })),
      homeSection('Most reported (last 7 days)', 'Ranked by independent outlet count across all countries', filter(hm.most_reported)),
      homeSection('Fastest growing (last 24 hours)', 'Most new coverage in the last 24 hours', filter(hm.growing)),
      homeSection('Blind spots · Not in domestic press', 'Covered by international or diaspora outlets, zero domestic coverage', filter(hm.abroad_only)),
      h('section', { class: 'drawer' },
        h('div', { class: 'drawer-head' },
          h('h2', { text: 'Monitored countries directory' }),
          h('span', { class: 'count', text: `${desks.length} active packs` })),
        h('div', { class: 'desk-wrap' },
          h('table', { class: 'desk-table' },
            h('thead', null, h('tr', null,
              h('th', { text: 'Country' }),
              h('th', { text: '24h' }),
              h('th', { text: '7d' }),
              h('th', { text: 'Alerts' }),
              h('th', { text: 'Lead story (7d)' }))),
            h('tbody', null, desks.map((d) => {
              const nAlerts = (c && c.countries && c.countries[d.id] || []).length;
              return h('tr', null,
                h('td', null, h('button', { type: 'button', class: 'desk-link', text: `${d.name} →`, onclick: () => openCountry(d.id) })),
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
    const stories = q ? d.stories.filter((s) => storyText(s).includes(q)) : d.stories;
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

    results.replaceChildren(...[
      h('p', { class: 'result-line' }, h('b', { text: country.options[country.selectedIndex].text }),
        ` · ${periodLabel} · ${plural(totalStories, 'story', 'stories')} found · updated ${fmtTime.format(updated)} · `,
        h('button', { type: 'button', class: 'desk-link', text: '← All countries overview', onclick: () => openCountry('home') })),
      noOutside && h('p', { class: 'notice quiet', text: `No coverage from ${(index.countries.find((x) => x.id === country.value) || {}).abroad_label || 'outlets abroad'} or from international outlets has been collected for this period yet, so the "not in domestic press" check cannot run.` }),
      ageH > STALE_HOURS && h('p', { class: 'notice', text: `This collection is ${Math.round(ageH)} hours old. Run the collector to refresh it.` }),
      h('div', { id: 'trans', class: 'trans' }),
      watchbar(q),
      alerts(),
      trends(),
      reddit(),
      tabs,
      ...body,
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
    if ($('#nav-home')) $('#nav-home').setAttribute('aria-current', country.value === 'home' ? 'page' : 'false');
    if ($('#nav-alerts')) $('#nav-alerts').setAttribute('aria-current', country.value === 'alerts' ? 'page' : 'false');
    if (country.value === 'home') {
      $('#brief').href = 'brief.html';
      setHash(hashFor('all'));
      renderHome();
      useLanguage('multi');
      return;
    }
    if (country.value === 'alerts') {
      useLanguage('en');
      $('#brief').href = 'brief.html';
      setHash(hashFor('all'));
      renderAlerts();
      return;
    }
    const c = index.countries.find((x) => x.id === country.value);
    const p = c.periods.find((x) => x.id === period.value);
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
  fillSelect(country, [['home', 'Overview (all countries)'], ['alerts', 'Active alerts (all countries)'], ...index.countries.map((c) => [c.id, c.name])], 'home');
  fillTopics('all');
  if ($('#alert-count')) { const n = allCrisisAlerts().length; if (n) $('#alert-count').textContent = `[${n}]`; }
  readHash();
  $('#home-link').addEventListener('click', (e) => { e.preventDefault(); openCountry('home'); });
  if ($('#nav-home')) $('#nav-home').addEventListener('click', (e) => { e.preventDefault(); openCountry('home'); });
  if ($('#nav-alerts')) $('#nav-alerts').addEventListener('click', (e) => { e.preventDefault(); openCountry('alerts'); });
  $('#slip').addEventListener('submit', (e) => { e.preventDefault(); research(); });
  country.addEventListener('change', () => { fillPeriods(); research(); });
  period.addEventListener('change', research);
  topic.addEventListener('change', research);
  $('#q').addEventListener('input', () => {
    setHash(hashFor(openTopic));
    if (country.value === 'home') renderHome();
    else if (country.value === 'alerts') renderAlerts();
    else if (current) render(false);
  });
  const totop = $('#totop');
  addEventListener('scroll', () => { totop.hidden = scrollY < 800; }, { passive: true });
  totop.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));
  window.addEventListener('hashchange', () => { readHash(); research(); });
  research();
})();
