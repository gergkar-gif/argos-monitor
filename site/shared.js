/* Shared region registry, text folding, and accessible country combobox across Argos Monitor pages. */
(() => {
  'use strict';

  const REGIONS = [
    'North America', 'Western Europe', 'Central & Southeast Europe', 'Eastern Europe',
    'South Caucasus', 'Middle East', 'Mediterranean', 'Central Asia', 'South Asia',
    'East Asia', 'Southeast Asia', 'Oceania', 'Sub-Saharan Africa', 'South America', 'Central America', 'Caribbean',
  ];

  const COUNTRY_REGION = {
    canada: 'North America', united_states: 'North America',
    belgium: 'Western Europe', denmark: 'Western Europe', finland: 'Western Europe', france: 'Western Europe', germany: 'Western Europe', ireland: 'Western Europe', italy: 'Western Europe',
    netherlands: 'Western Europe', norway: 'Western Europe', portugal: 'Western Europe', spain: 'Western Europe', sweden: 'Western Europe', switzerland: 'Western Europe', united_kingdom: 'Western Europe',
    austria: 'Central & Southeast Europe', bosnia: 'Central & Southeast Europe', croatia: 'Central & Southeast Europe', czechia: 'Central & Southeast Europe', hungary: 'Central & Southeast Europe', kosovo: 'Central & Southeast Europe', poland: 'Central & Southeast Europe', serbia: 'Central & Southeast Europe', slovakia: 'Central & Southeast Europe', slovenia: 'Central & Southeast Europe',
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

  const fold = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/ł/g, 'l').replace(/ı/g, 'i');

  function getRegion(cid, countries) {
    const match = countries && countries.find((x) => x.id === cid);
    return (match && match.region) || COUNTRY_REGION[cid] || 'Other';
  }

  function makeEl(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'text') e.textContent = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? '' : v);
    }
    e.append(...kids.flat(Infinity).filter((x) => x != null && x !== false));
    return e;
  }

  function setupCountryCombobox({
    countries,
    searchEl,
    menuEl,
    arrowEl,
    selectEl,
    includeAll = false,
    isSelected,
    getQuerySeed,
    onSelect,
    onCloseSync,
  }) {
    if (!searchEl || !menuEl || !selectEl) return;
    let highlightedIndex = -1;
    let visibleItems = [];
    const optPrefix = searchEl.id || 'cb';

    function addOption(c, reg) {
      const sel = isSelected ? isSelected(c) : c.id === selectEl.value;
      const item = makeEl('div', {
        id: `${optPrefix}-opt-${c.id}`,
        class: 'combobox-item' + (sel ? ' selected' : ''),
        role: 'option',
        'aria-selected': String(sel),
        'data-id': c.id,
        'data-name': c.name,
        onclick: () => selectCountry(c.id, c.name),
      },
        makeEl('span', { class: 'c-name', text: c.name }),
        makeEl('span', { class: 'c-region', text: reg })
      );
      menuEl.append(item);
      visibleItems.push({ el: item, id: c.id, name: c.name });
    }

    function renderMenu(query = '') {
      const q = fold(query.trim());
      visibleItems = [];
      menuEl.replaceChildren();

      if (!q || (includeAll && (q === 'all' || q === 'all countries'))) {
        if (includeAll) addOption({ id: 'all', name: 'All countries' }, 'Global');
        const groups = new Map(REGIONS.map((r) => [r, []]));
        for (const c of countries) {
          const r = c.region || getRegion(c.id, countries);
          if (!groups.has(r)) groups.set(r, []);
          groups.get(r).push(c);
        }
        for (const [reg, list] of groups.entries()) {
          if (!list.length) continue;
          menuEl.append(makeEl('div', { class: 'combobox-group-label', text: reg }));
          for (const c of list) addOption(c, reg);
        }
      } else {
        const matches = countries.filter((c) => {
          const reg = c.region || getRegion(c.id, countries);
          if (fold(c.name).includes(q) || fold(c.id).includes(q) || fold(reg).includes(q)) return true;
          return (c.mentions || []).some((m) => fold(m).includes(q));
        });
        if (!matches.length) {
          menuEl.append(makeEl('div', { class: 'combobox-empty', text: `No countries matching "${query}"` }));
        } else {
          for (const c of matches) addOption(c, c.region || getRegion(c.id, countries));
        }
      }

      highlightedIndex = visibleItems.findIndex((it) => it.id === selectEl.value);
      if (highlightedIndex === -1 && visibleItems.length) highlightedIndex = 0;
      updateHighlight();
    }

    function updateHighlight() {
      let activeId = '';
      visibleItems.forEach((it, idx) => {
        const isHi = idx === highlightedIndex;
        it.el.classList.toggle('highlighted', isHi);
        if (isHi) {
          activeId = it.el.id;
          it.el.scrollIntoView({ block: 'nearest' });
        }
      });
      if (activeId) searchEl.setAttribute('aria-activedescendant', activeId);
      else searchEl.removeAttribute('aria-activedescendant');
    }

    function selectCountry(cid, cname) {
      selectEl.value = cid;
      searchEl.value = cname;
      closeMenu();
      onSelect(cid, cname);
    }

    function openMenu() {
      const seed = getQuerySeed ? getQuerySeed() : searchEl.value;
      renderMenu(seed);
      menuEl.hidden = false;
      searchEl.setAttribute('aria-expanded', 'true');
    }

    function closeMenu() {
      menuEl.hidden = true;
      searchEl.setAttribute('aria-expanded', 'false');
      searchEl.removeAttribute('aria-activedescendant');
      highlightedIndex = -1;
    }

    searchEl.addEventListener('focus', () => {
      searchEl.select();
      openMenu();
    });

    searchEl.addEventListener('input', () => {
      openMenu();
      renderMenu(searchEl.value);
    });

    searchEl.addEventListener('keydown', (e) => {
      if (menuEl.hidden && (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter')) {
        e.preventDefault();
        openMenu();
        return;
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
        if (onCloseSync) onCloseSync();
        closeMenu();
        searchEl.blur();
      }
    });

    if (arrowEl) {
      arrowEl.addEventListener('click', (e) => {
        e.preventDefault();
        if (menuEl.hidden) {
          searchEl.focus();
          openMenu();
        } else {
          closeMenu();
        }
      });
    }

    document.addEventListener('click', (e) => {
      if (!searchEl.contains(e.target) && !menuEl.contains(e.target) && (!arrowEl || !arrowEl.contains(e.target))) {
        if (!menuEl.hidden) {
          closeMenu();
          if (onCloseSync) onCloseSync();
        }
      }
    });
  }

  window.ARGOS_SHARED = { REGIONS, COUNTRY_REGION, getRegion, fold, setupCountryCombobox };
})();
