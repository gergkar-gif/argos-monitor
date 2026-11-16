// Phone Menu button + shared alert-count badge across secondary pages.
(() => {
  const bureau = document.querySelector('.bureau'), btn = document.querySelector('.navtoggle'), nav = document.getElementById('topnav');
  if (bureau && btn && nav) {
    const set = (open) => {
      bureau.classList.toggle('nav-open', open);
      btn.setAttribute('aria-expanded', String(open));
    };
    btn.addEventListener('click', () => set(!bureau.classList.contains('nav-open')));
    nav.addEventListener('click', (e) => { if (e.target.closest('a')) set(false); });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && bureau.classList.contains('nav-open')) {
        set(false);
        btn.focus();
      }
    });
    document.addEventListener('click', (e) => {
      if (bureau.classList.contains('nav-open') && !bureau.contains(e.target)) set(false);
    });
  }

  // Populate #alert-count on static secondary pages (index.html updates it in app.js).
  const badge = document.getElementById('alert-count');
  const crisis = window.ARGOS_CRISIS;
  if (badge && !badge.textContent && crisis && crisis.countries && !window.ARGOS_HOME) {
    const seen = new Set();
    const ref = crisis.generated_at ? Math.min(Date.now(), Date.parse(crisis.generated_at) || Date.now()) : Date.now();
    const cut24 = ref - 24 * 3600 * 1000;
    let total = 0, h24 = 0;
    for (const list of Object.values(crisis.countries)) {
      for (const item of list) {
        const k = `${item.kind}|${(item.title || '').toLowerCase()}`;
        if (seen.has(k)) continue;
        seen.add(k);
        total++;
        if (item.date && Date.parse(item.date) >= cut24) h24++;
      }
    }
    const n = h24 || total;
    if (n) badge.textContent = `[${n}]`;
  }
})();
