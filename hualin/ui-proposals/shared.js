// Injects the app bar + proposal nav into every proposal page.
(function () {
  const PAGES = [
    ['chat.html', '★ Chat (main UI)'],
    ['index.html', 'Overview'],
    ['1-case-queue.html', '1 · Case Queue'],
    ['2-intake-safety.html', '2 · Intake + Safety Gate'],
    ['3-pipeline-tracker.html', '3 · Pipeline Tracker'],
    ['4-evidence-room.html', '4 · Evidence Room'],
    ['5-rights-relief.html', '5 · Rights, Relief & Tract'],
    ['6-brief-chat.html', '6 · Brief + Copilot Chat'],
  ];
  const here = location.pathname.split('/').pop() || 'index.html';
  const bar = document.createElement('div');
  bar.innerHTML = `
    <header class="appbar">
      <span class="logo">🏠 ShelterWise</span>
      <span class="metro">📍 San Francisco, CA · 42 tracts</span>
      <span class="sample-tag">SAMPLE DATA</span>
      <span class="sp"></span>
      <span class="user">Maria R. · Paralegal · Bay Legal Aid</span>
    </header>
    <nav class="propnav" aria-label="UI proposals">
      ${PAGES.map(([h, t]) => `<a href="${h}" class="${h === here ? 'on' : ''}">${t}</a>`).join('')}
    </nav>`;
  document.body.prepend(...bar.children);
})();

function toast(html, ms = 3500) {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; t.setAttribute('role', 'status'); document.body.append(t); }
  t.innerHTML = html; t.classList.add('show');
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), ms);
}
