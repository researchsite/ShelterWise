// Injects the ShelterWise app bar at the top of the page.
(function () {
  const bar = document.createElement('div');
  bar.innerHTML = `
    <header class="appbar">
      <span class="logo">🏠 ShelterWise</span>
      <span class="metro">📍 San Francisco, CA · 42 tracts</span>
      <span class="sample-tag">SAMPLE DATA</span>
      <span class="sp"></span>
      <span class="user">Maria R. · Paralegal · Bay Legal Aid</span>
    </header>`;
  document.body.prepend(...bar.children);
})();

function toast(html, ms = 3500) {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; t.setAttribute('role', 'status'); document.body.append(t); }
  t.innerHTML = html; t.classList.add('show');
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), ms);
}
