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
  // Where coverage comes from; the middle label is the country's own ("Vietnamese-language outlets abroad").
  function scopes() {
    const c = index.countries.find((x) => x.id === country.value);
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
    const c = index.countries.find((x) => x.id === country.value);
    fillSelect(period, c.periods.map((p) => [p.id, p.label]), period.value || '7d');
  }
  function fillTopics(value) {
    fillSelect(topic, [['all', 'All topics'], ...TOPICS.map((t) => [t.id, t.name])], value);
  }

  const hashFor = (t) => `#${country.value}/${period.value}/${t}` + ($('#q').value.trim() ? `/${encodeURIComponent($('#q').value.trim())}` : '');
  function readHash() {
    const [c, p, t, q] = location.hash.replace(/^#/, '').split('/');
    try { $('#q').value = q ? decodeURIComponent(q) : ''; } catch { /* bad link text: ignore */ }
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

  const T = { lang: 'en', state: 'checking', translator: null, cache: new Map(), queue: [], running: false };
  const withTimeout = (p, ms) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error('timeout')), ms))]);

  function track(el, text, lang, origEl) {
    if (lang === 'en' || lang !== T.lang) return;   // already English, or not the language the translator is set up for
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
        it.origEl.lang = T.lang;
        it.origEl.hidden = false;
      } catch { /* keep the original text as it is */ }
    }
    T.running = false;
  }
  async function startTranslator(button) {
    T.translator = await Translator.create({
      sourceLanguage: T.lang, targetLanguage: 'en',
      monitor(m) { m.addEventListener('downloadprogress', (e) => { if (button) button.textContent = `Downloading English… ${Math.round(e.loaded * 100)}%`; }); },
    });
    T.state = 'ready';
  }
  function useLanguage(lang) {
    if (lang === T.lang) return;
    T.lang = lang; T.state = 'checking'; T.translator = null;
    initTranslator().then(() => { paintTranslationBar(); translatePending(); });
  }
  async function initTranslator() {
    if (T.lang === 'en') { T.state = 'none'; return; }
    if (typeof Translator === 'undefined') { T.state = 'none'; return; }
    try {
      const a = await withTimeout(Translator.availability({ sourceLanguage: T.lang, targetLanguage: 'en' }), 4000);
      if (a === 'available') await startTranslator();
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
  // New, growing or quiet, judged from when its articles were published (the last 24 hours against the whole story).
  function trend(s) {
    if (s.last_24h == null || s.articles < 2) return null;
    if (s.last_24h === s.articles) return ['New', 'indigo', 'Every article is from the last 24 hours.'];
    if (s.last_24h >= 3 && s.last_24h * 2 >= s.articles) return ['Growing', 'indigo', 'Half or more of the articles are from the last 24 hours.'];
    if (s.last_24h === 0) return ['Quiet', 'indigo', 'No new articles in the last 24 hours.'];
    return null;
  }

  function story(s, opts) {
    const first = s.sources[0];
    const present = scopes().filter(([id]) => s.by_scope[id]);
    const single = present.length === 1 ? present[0][1] : '';
    const outlets = plural(s.independent_sources, 'independent outlet', 'independent outlets');
    const clip = h('article', { class: 'clip' + (opts.lead ? ' lead' : ''), style: `--i:${opts.i}` });

    const headLink = h('a', { href: safeUrl(s.headline.url), target: '_blank', rel: 'noopener', lang: s.headline.language, text: s.headline.title });
    const headOrig = h('p', { class: 'orig', hidden: true, title: 'Original headline' });
    track(headLink, s.headline.title, s.headline.language, headOrig);

    clip.append(...[
      h('div', null,
        h('h3', { class: 'headline' }, headLink),
        headOrig,
        h('p', { class: 'byline', text: `${s.headline.source}, ${fmtDay.format(new Date(s.last_seen))}` }),
      ),
      h('div', { class: 'slipline' },
        h('span', { class: 'stamp ' + (s.evidence === 'OFFICIAL' ? 'red' : 'indigo'),
          title: s.evidence === 'OFFICIAL' ? 'A government or Party outlet is among the sources. Officially stated, not independently verified.' : 'Reported by one or more outlets.',
          text: s.evidence === 'OFFICIAL' ? 'Official' : 'Reported' }),
        trend(s) && h('span', { class: 'stamp ' + trend(s)[1], title: trend(s)[2], text: trend(s)[0] }),
        s.abroad_only && h('span', { class: 'stamp teal', title: 'No outlet inside the country covered it.', text: 'Not in domestic press' }),
        (s.themes || []).length > 0 && h('span', { class: 'themes', title: 'Why this story ranks where it does', text: s.themes.join(' · ') }),
        h('span', null, h('strong', { text: outlets }), ` · ${plural(s.articles, 'article', 'articles')}`, single && ` · all ${single}`),
      ),
      scopes().filter(([id]) => s.by_scope[id]).length > 1 && h('div', { class: 'cover', 'aria-label': 'Where the coverage comes from' },
        scopes().filter(([id]) => s.by_scope[id]).map(([id, label]) => h('span', null, h('b', { text: String(s.by_scope[id]) }), ` ${s.by_scope[id] === 1 ? 'article' : 'articles'} from ${label}`))),
    ].filter(Boolean));   // a missing optional row must not be appended as the text "false"

    const shown = opts.lead ? s.excerpts : s.excerpts.slice(0, 1);
    if (shown.length) {
      clip.append(h('div', { class: 'strips' }, shown.map((x) => {
        const main = h('p', { lang: T.lang, text: x.text });
        const orig = h('p', { class: 'orig', hidden: true, title: 'Original quote' });
        track(main, x.text, T.lang, orig);
        return h('blockquote', { class: 'strip' }, main, orig,
          h('footer', null, h('a', { class: 'stamp indigo', href: safeUrl(x.url), target: '_blank', rel: 'noopener', text: x.source })));
      })));
    }

    if (s.first && s.articles > 2) {
      const max = Math.max(...s.per_day.map((d) => d[1]));
      clip.append(h('div', { class: 'timeline' },
        h('span', { class: 'bars', 'aria-hidden': 'true' }, s.per_day.map(([day, n]) =>
          h('i', { style: `height:${Math.max(15, Math.round(100 * n / max))}%`, title: `${fmtDay.format(new Date(day))}: ${plural(n, 'article', 'articles')}` }))),
        h('span', { text: `First seen in ${s.first.source}, ${fmtTime.format(new Date(s.first.at))}. ${plural(s.per_day.length, 'day', 'days')} of coverage.` })));
    }
    if ((s.related || []).length) {
      clip.append(h('p', { class: 'byline related' }, 'May be the same event: ', s.related.map((r) =>
        h('span', null, h('a', { href: safeUrl(r.url), target: '_blank', rel: 'noopener', text: r.title }), ` (${plural(r.articles, 'article', 'articles')}, ${r.source}) `))));
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
      sec.append(
        h('button', { type: 'button', class: 'more', onclick: () => { extra[id] = (extra[id] || 0) + 8; render(false); }, text: `Show ${Math.min(8, stories.length - limit)} more` }),
        h('button', { type: 'button', class: 'more', onclick: () => choose(id), text: `Open all ${topicName(id)}` }));
    }
    return sec;
  }

  const storyText = (s) => [s.headline.title, ...s.sources.map((r) => r.title + ' ' + r.source), ...s.excerpts.map((x) => x.text)].join(' ').toLowerCase();

  // What people search for (Google Trends): how many collected stories mention each term, one click to read them.
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

  // Top posts of the day on the country's subreddit; hidden when Reddit did not answer.
  function reddit() {
    const r = (window.ARGOS_REDDIT && (window.ARGOS_REDDIT.countries || (window.ARGOS_REDDIT.reddit || {}).countries) || {})[country.value];
    if (!r || !r.posts.length) return null;
    return h('section', { class: 'alerts', 'aria-label': 'On Reddit' },
      h('h2', { text: `On Reddit today, r/${r.subreddit}` }),
      h('ul', null, r.posts.map((x) => h('li', null, h('a', { href: safeUrl(x.url), target: '_blank', rel: 'noopener', text: x.title })))),
      h('p', { class: 'byline', text: 'Top posts of the day. What people discuss, not verified news.' }));
  }

  // Watchlist: words the reader follows, kept in this browser only. Each chip shows how many stories mention it here.
  const watched = () => { try { return JSON.parse(localStorage.getItem('argos.watch') || '[]'); } catch { return []; } };
  function setWatched(list) {
    try { localStorage.setItem('argos.watch', JSON.stringify(list)); } catch { /* storage not available: ignore */ }
    render(false);
  }
  function watchbar(q) {
    const list = watched();
    if (!list.length && !q) return null;
    return h('div', { class: 'watch' },
      h('span', { class: 'meta', text: 'Watching' }),
      list.map((w) => h('span', { class: 'chip' },
        h('button', { type: 'button', class: 'more', title: 'Show these stories',
          text: `${w} (${current.stories.filter((s) => storyText(s).includes(w)).length})`,
          onclick: () => { $('#q').value = w; setHash(hashFor(openTopic)); render(false); } }),
        h('button', { type: 'button', class: 'x', 'aria-label': `Stop watching ${w}`, text: '×', onclick: () => setWatched(list.filter((x) => x !== w)) }))),
      q && !list.includes(q) && h('button', { type: 'button', class: 'more', text: `Watch "${q}"`, onclick: () => setWatched([...list, q]) }));
  }

  // Official alerts from free feeds (GDACS, USGS, travel advice): each line is the feed's own title, linked to it.
  function alerts() {
    const raw = window.ARGOS_CRISIS; const c = raw && (raw.countries ? raw : raw.crisis);
    if (!c) return null;
    const items = c.countries[country.value] || [];
    const hot = (i) => /^(Red|Orange)$/.test(i.level || '') || /Level [34]/.test(i.title);
    return h('section', { class: 'alerts', 'aria-label': 'Official alerts' },
      h('h2', { text: 'Official alerts' }),
      items.length
        ? h('ul', null, items.map((i) => h('li', null,
          h('span', { class: 'stamp ' + (hot(i) ? 'red' : 'indigo'), text: i.kind }),
          h('a', { href: safeUrl(i.url), target: '_blank', rel: 'noopener', text: i.title }),
          i.date && h('span', { class: 'meta', text: fmtDay.format(new Date(i.date)) }))))
        : h('p', { class: 'byline', text: 'No disaster alerts in the last 7 days.' }),
      h('p', { class: 'byline', text: `GDACS, USGS, UK and US travel advice. Checked ${fmtTime.format(new Date(c.generated_at))}.` }));
  }

  function render(animate = true) {
    const d = current;
    results.classList.toggle('still', !animate);
    T.queue.length = 0;    // items from the previous render are gone
    const q = ($('#q').value || '').trim().toLowerCase();   // search narrows the loaded stories in the browser
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
        ` · ${periodLabel} · ${plural(totalStories, 'story', 'stories')} found · updated ${fmtTime.format(updated)}`),
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
  fillSelect(country, index.countries.map((c) => [c.id, c.name]));
  fillTopics('all');
  readHash();
  $('#slip').addEventListener('submit', (e) => { e.preventDefault(); research(); });
  // Choosing a country, period or topic searches straight away; the Research button stays for habit.
  country.addEventListener('change', () => { fillPeriods(); research(); });
  period.addEventListener('change', research);
  topic.addEventListener('change', research);
  $('#q').addEventListener('input', () => { setHash(hashFor(openTopic)); if (current) render(false); });
  const totop = $('#totop');
  addEventListener('scroll', () => { totop.hidden = scrollY < 800; }, { passive: true });
  totop.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));
  window.addEventListener('hashchange', () => { readHash(); research(); });
  research();     // also sets up the translator for the country's language
})();
