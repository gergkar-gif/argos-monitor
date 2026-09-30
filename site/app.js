/* Argos Monitor page: reads the data files the pipeline wrote and renders the clippings. No framework. */
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
  const SCOPES = [
    ['domestic', 'domestic outlets'],
    ['abroad_vi', 'Vietnamese-language outlets abroad'],
    ['international', 'international outlets'],
  ];

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
    const c = index.countries.find((x) => x.id === country.value);
    fillSelect(period, c.periods.map((p) => [p.id, p.label]), period.value || '7d');
  }
  function fillTopics(value) {
    fillSelect(topic, [['all', 'All topics'], ...TOPICS.map((t) => [t.id, t.name])], value);
  }

  function readHash() {
    const [c, p, t] = location.hash.replace(/^#/, '').split('/');
    if (c && index.countries.some((x) => x.id === c)) country.value = c;
    fillPeriods();
    if (p && [...period.options].some((o) => o.value === p)) period.value = p;
    if (t && (t === 'all' || TOPICS.some((x) => x.id === t))) topic.value = t;
  }

  // ---------- English, translated by the reader's own browser (decision D11) ----------
  // Nothing is stored or written by this app: the browser's built-in translator makes the English on the
  // reader's device. The original text stays on the page (muted) and is what the link and quotes rest on.
  // Keep the choice in the address so a link can be shared. Some browsers refuse this for pages opened from a
  // folder or a preview frame, so failing is harmless.
  function setHash(value) {
    if (location.protocol === 'file:') return;
    try { history.replaceState(null, '', value); } catch { /* not allowed here: ignore */ }
  }

  // English only by default; the original stays one click away so a translation can always be checked.
  function setShowOriginal(on) {
    document.body.classList.toggle('show-orig', on);
    try { localStorage.setItem('argos.showOriginal', on ? '1' : '0'); } catch { /* storage not available: ignore */ }
  }
  try { if (localStorage.getItem('argos.showOriginal') === '1') document.body.classList.add('show-orig'); } catch { /* ignore */ }

  const T = { state: 'checking', translator: null, cache: new Map(), queue: [], running: false };
  const withTimeout = (p, ms) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error('timeout')), ms))]);

  function track(el, text, lang, origEl) {
    if (lang === 'en') return;                      // already English
    T.queue.push({ el, text, origEl });
  }
  async function translatePending() {
    if (T.state !== 'ready' || T.running) return;
    T.running = true;
    while (T.queue.length) {
      const it = T.queue.shift();
      if (!it.el.isConnected) continue;
      try {
        let en = T.cache.get(it.text);
        if (en == null) { en = await T.translator.translate(it.text); T.cache.set(it.text, en); }
        it.el.textContent = en;
        it.el.lang = 'en';
        it.origEl.textContent = it.text;
        it.origEl.lang = 'vi';
        it.origEl.hidden = false;
      } catch { /* keep the original text as it is */ }
    }
    T.running = false;
  }
  async function startTranslator(button) {
    T.translator = await Translator.create({
      sourceLanguage: 'vi', targetLanguage: 'en',
      monitor(m) { m.addEventListener('downloadprogress', (e) => { if (button) button.textContent = `Downloading English… ${Math.round(e.loaded * 100)}%`; }); },
    });
    T.state = 'ready';
  }
  async function initTranslator() {
    if (typeof Translator === 'undefined') { T.state = 'none'; return; }
    try {
      const a = await withTimeout(Translator.availability({ sourceLanguage: 'vi', targetLanguage: 'en' }), 4000);
      if (a === 'available') await startTranslator();
      else if (a === 'downloadable' || a === 'downloading') T.state = 'offer';
      else T.state = 'none';
    } catch { T.state = 'none'; }
  }
  function paintTranslationBar() {
    const bar = $('#trans');
    if (!bar) return;
    if (T.state === 'ready') {
      const on = document.body.classList.contains('show-orig');
      const toggle = h('button', { type: 'button', class: 'more', 'aria-pressed': String(on), text: on ? 'Hide original Vietnamese' : 'Show original Vietnamese' });
      toggle.addEventListener('click', () => { setShowOriginal(!document.body.classList.contains('show-orig')); paintTranslationBar(); });
      bar.replaceChildren(
        h('p', { class: 'notice quiet', text: 'English lines are machine translations made by your browser and can be wrong. The original Vietnamese is hidden; every headline links to the original article.' }),
        toggle);
    } else if (T.state === 'offer') {
      const btn = h('button', { type: 'button', class: 'more', text: 'Show English (one-time download of a small language pack)' });
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        try { await startTranslator(btn); } catch { T.state = 'none'; }
        paintTranslationBar();
        translatePending();
      });
      bar.replaceChildren(btn);
    } else if (T.state === 'none') {
      bar.replaceChildren(h('p', { class: 'notice quiet', text: 'Your browser cannot translate on its own device here, so headlines show in Vietnamese. Use the browser\'s Translate feature (Chrome or Edge on a computer work best).' }));
    } else {
      bar.replaceChildren();
    }
  }

  // ---------- rendering ----------
  function story(s, opts) {
    const first = s.sources[0];
    const present = SCOPES.filter(([id]) => s.by_scope[id]);
    const single = present.length === 1 ? present[0][1] : '';
    const outlets = plural(s.independent_sources, 'independent outlet', 'independent outlets');
    const clip = h('article', { class: 'clip' + (opts.lead ? ' lead' : ''), style: `--i:${opts.i}` });

    const headLink = h('a', { href: safeUrl(s.headline.url), target: '_blank', rel: 'noopener', lang: s.headline.language, text: s.headline.title });
    const headOrig = h('p', { class: 'orig', hidden: true, title: 'Original headline' });
    track(headLink, s.headline.title, s.headline.language, headOrig);

    clip.append(
      h('div', null,
        h('h3', { class: 'headline' }, headLink),
        headOrig,
        h('p', { class: 'byline', text: `${s.headline.source}, ${fmtDay.format(new Date(s.last_seen))}` }),
      ),
      h('div', { class: 'slipline' },
        h('span', { class: 'stamp ' + (s.evidence === 'OFFICIAL' ? 'red' : 'indigo'),
          title: s.evidence === 'OFFICIAL' ? 'A government or Party outlet is among the sources. Officially stated, not independently verified.' : 'Reported by one or more outlets.',
          text: s.evidence === 'OFFICIAL' ? 'Official' : 'Reported' }),
        s.abroad_only && h('span', { class: 'stamp teal', title: 'No outlet inside the country covered it.', text: 'Not in domestic press' }),
        h('span', null, h('strong', { text: outlets }), ` · ${plural(s.articles, 'article', 'articles')}`, single && ` · all ${single}`),
      ),
      SCOPES.filter(([id]) => s.by_scope[id]).length > 1 && h('div', { class: 'cover', 'aria-label': 'Where the coverage comes from' },
        SCOPES.filter(([id]) => s.by_scope[id]).map(([id, label]) => h('span', null, h('b', { text: String(s.by_scope[id]) }), ` ${s.by_scope[id] === 1 ? 'article' : 'articles'} from ${label}`))),
    );

    const shown = opts.lead ? s.excerpts : s.excerpts.slice(0, 1);
    if (shown.length) {
      clip.append(h('div', { class: 'strips' }, shown.map((x) => {
        const main = h('p', { lang: 'vi', text: x.text });
        const orig = h('p', { class: 'orig', hidden: true, title: 'Original quote' });
        track(main, x.text, 'vi', orig);
        return h('blockquote', { class: 'strip' }, main, orig,
          h('footer', null, h('a', { class: 'stamp indigo', href: safeUrl(x.url), target: '_blank', rel: 'noopener', text: x.source })));
      })));
    }

    const rest = s.sources;
    const lateItems = [];   // source-list titles are translated only when the list is opened
    const details = h('details', null,
      h('summary', { text: `All sources (${plural(s.articles, 'article', 'articles')})` }),
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
      sec.append(h('button', { type: 'button', class: 'more', onclick: () => choose(id), text: `More in ${topicName(id)}` }));
    }
    return sec;
  }

  function render(animate = true) {
    const d = current;
    results.classList.toggle('still', !animate);
    T.queue.length = 0;    // items from the previous render are gone
    const noOutside = d.stories.every((s) => !s.by_scope.abroad_vi && !s.by_scope.international);
    const byTopic = (id) => d.stories.filter((s) => s.category === id);
    const totalStories = Object.values(d.totals).reduce((a, b) => a + b, 0);
    const updated = new Date(d.generated_at);
    const ageH = (Date.now() - updated) / 3.6e6;
    const periodLabel = period.options[period.selectedIndex].text.toLowerCase();

    const tabs = h('ul', { class: 'tabs', role: 'list' },
      [['all', 'All topics'], ...TOPICS.map((t) => [t.id, t.name])].map(([id, label]) =>
        h('li', null, h('button', { type: 'button', class: 'tab', style: id === 'all' ? '' : topicVar(id),
          'aria-pressed': String(openTopic === id), onclick: () => choose(id) }, label,
          h('span', { class: 'n', text: String(id === 'all' ? totalStories : d.totals[id]) })))));

    const body = [];
    if (openTopic === 'all') {
      const order = TOPICS.map((t) => t.id).filter((id) => byTopic(id).length)
        .sort((a, b) => (a === 'other') - (b === 'other') || byTopic(b)[0].score - byTopic(a)[0].score);
      order.forEach((id) => body.push(drawer(id, byTopic(id), d.totals[id], PER_TOPIC_IN_OVERVIEW)));
    } else if (byTopic(openTopic).length) {
      body.push(drawer(openTopic, byTopic(openTopic), d.totals[openTopic], 0));
    } else {
      body.push(h('p', { class: 'state', text: `No ${topicName(openTopic).toLowerCase()} stories in this period.` }));
    }

    results.replaceChildren(...[
      h('p', { class: 'result-line' }, h('b', { text: country.options[country.selectedIndex].text }),
        ` · ${periodLabel} · ${plural(totalStories, 'story', 'stories')} found · updated ${fmtTime.format(updated)}`),
      noOutside && h('p', { class: 'notice quiet', text: 'No coverage from Vietnamese-language outlets abroad or from international outlets has been collected for this period yet, so the "not in domestic press" check cannot run.' }),
      ageH > STALE_HOURS && h('p', { class: 'notice', text: `This collection is ${Math.round(ageH)} hours old. Run the collector to refresh it.` }),
      h('div', { id: 'trans', class: 'trans' }),
      tabs,
      ...body,
    ].filter(Boolean));
    paintTranslationBar();
    translatePending();
  }

  function choose(id) {
    openTopic = id;
    topic.value = id;
    setHash(`#${country.value}/${period.value}/${id}`);
    render(false);
    if (id !== 'all') results.scrollIntoView({ block: 'start' });
  }

  async function research() {
    const c = index.countries.find((x) => x.id === country.value);
    const p = c.periods.find((x) => x.id === period.value);
    openTopic = topic.value;
    setHash(`#${country.value}/${period.value}/${topic.value}`);
    results.replaceChildren(h('p', { class: 'state', text: 'Gathering the clippings…' }));
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
  fillSelect(country, index.countries.map((c) => [c.id, c.name]));
  fillTopics('all');
  readHash();
  $('#slip').addEventListener('submit', (e) => { e.preventDefault(); research(); });
  country.addEventListener('change', fillPeriods);
  window.addEventListener('hashchange', () => { readHash(); research(); });
  research();
  initTranslator().then(() => { paintTranslationBar(); translatePending(); });
})();
