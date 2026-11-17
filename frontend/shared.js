// Injects the ShelterWise app bar (with theme switcher) at the top of the page.
(function () {
  const THEMES = [['courthouse', 'Courthouse'], ['civic', 'Civic'], ['original', 'Original']];
  const saved = localStorage.getItem('sw-theme') || 'courthouse';
  document.documentElement.dataset.theme = saved;
  const bar = document.createElement('div');
  bar.innerHTML = `
    <header class="appbar">
      <span class="logo">🏠 ShelterWise</span>
      <span class="metro">📍 San Francisco, CA · 42 tracts</span>
      <span class="sample-tag">SAMPLE DATA</span>
      <span class="sp"></span>
      <label class="small" style="opacity:.85">Theme
        <select id="themeSel" aria-label="Color theme">
          ${THEMES.map(([v, t]) => `<option value="${v}" ${v === saved ? 'selected' : ''}>${t}</option>`).join('')}
        </select></label>
      <span class="user">Maria R. · Paralegal · Bay Legal Aid</span>
    </header>`;
  document.body.prepend(...bar.children);
  document.getElementById('themeSel').addEventListener('change', e => {
    document.documentElement.dataset.theme = e.target.value;
    localStorage.setItem('sw-theme', e.target.value);
  });
})();

function toast(html, ms = 3500) {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; t.setAttribute('role', 'status'); document.body.append(t); }
  t.innerHTML = html; t.classList.add('show');
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), ms);
}
