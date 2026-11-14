// Phone Menu button: opens/closes the top links; any link tap closes it again.
(() => {
  const bureau = document.querySelector('.bureau'), btn = document.querySelector('.navtoggle'), nav = document.getElementById('topnav');
  if (!bureau || !btn || !nav) return;
  const set = (open) => { bureau.classList.toggle('nav-open', open); btn.setAttribute('aria-expanded', String(open)); };
  btn.addEventListener('click', () => set(!bureau.classList.contains('nav-open')));
  nav.addEventListener('click', (e) => { if (e.target.closest('a')) set(false); });
})();
