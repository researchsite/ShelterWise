// Injects the ShelterWise app bar at the top of the page.
(function () {
  document.documentElement.dataset.theme = 'courthouse';
  localStorage.setItem('sw-theme', 'courthouse');
  const bar = document.createElement('div');
  bar.innerHTML = `
    <header class="appbar">
      <span class="logo">🏠 ShelterWise</span>
      <span class="metro">📍 San Francisco, CA</span>
      <span class="sp"></span>
      <span class="user">⚖️ Legal Aid Advocate · Eviction Defense Portal</span>
    </header>`;
  document.body.prepend(...bar.children);
})();

function toast(html, ms = 3500) {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; t.setAttribute('role', 'status'); document.body.append(t); }
  t.innerHTML = html; t.classList.add('show');
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), ms);
}
