/* ShelterWise map panel (Google Maps JavaScript API)
   ------------------------------------------------------------------
   Renders the `geo` field (GeoJSON FeatureCollection) carried by chat
   response blocks. Each feature's `properties.role` picks its style:
     tenant_block · corroborating · excluded · courthouse · route ·
     tract_focus · silent_distress · search_radius
   `properties.ref` links a map feature to a card in the chat
   (elements with data-ref="<ref>") for two-way highlighting.

   API key lookup order: window.SW_CONFIG.GOOGLE_MAPS_API_KEY
   (config.local.js, git-ignored) → ?gmaps_key= URL param → localStorage.
   With no key Google Maps runs in "development purposes only" mode.
-------------------------------------------------------------------*/
const SWMap = (() => {
  let map, info, base, all311, overlay, circles = [], dirRenderer, ready = false, pending = null, lastRoute = null;
  const SF = { lat: 37.7605, lng: -122.4425 };
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const BURDEN_STEPS = [[10, '#e8eef6'], [15, '#c5d4e8'], [20, '#94b0d4'], [25, '#5f86b8'], [999, '#2f5a92']]; // one hue, light→dark
  const burdenColor = v => BURDEN_STEPS.find(([t]) => v < t)[1];
  const layerState = { shade: false, pts: false };

  function key() {
    const u = new URLSearchParams(location.search).get('gmaps_key');
    if (u) localStorage.setItem('sw-gmaps-key', u);
    return (window.SW_CONFIG && window.SW_CONFIG.GOOGLE_MAPS_API_KEY) || u || localStorage.getItem('sw-gmaps-key') || '';
  }

  function load() {
    const k = key();
    document.getElementById('mapkey').hidden = !!k;
    window.__swInitMap = init;
    window.gm_authFailure = () => { const b = document.getElementById('mapkey'); b.hidden = false; b.querySelector('.msg').innerHTML = '⚠ Google rejected this API key. Check that <b>Maps JavaScript API</b> is enabled and the key allows this origin.'; };
    const s = document.createElement('script');
    s.src = `https://maps.googleapis.com/maps/api/js?${k ? 'key=' + encodeURIComponent(k) + '&' : ''}callback=__swInitMap&loading=async&v=weekly`;
    s.async = true; s.onerror = () => { document.getElementById('map').innerHTML = '<div class="mapfail">Could not load Google Maps (offline?). The chat still works.</div>'; };
    document.head.append(s);
  }

  function saveKey() {
    const v = document.getElementById('keyinp').value.trim();
    if (v) { localStorage.setItem('sw-gmaps-key', v); location.reload(); }
  }

  function init() {
    map = new google.maps.Map(document.getElementById('map'), {
      center: SF, zoom: 12, mapTypeControl: false, streetViewControl: false, fullscreenControl: true, clickableIcons: false,
      styles: [
        { featureType: 'poi', stylers: [{ visibility: 'off' }] },
        { featureType: 'transit.station', stylers: [{ visibility: 'simplified' }] },
        { elementType: 'geometry', stylers: [{ saturation: -60 }, { lightness: 8 }] },
        { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#c9d6e3' }] },
        { featureType: 'road', elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
      ],
    });
    info = new google.maps.InfoWindow();

    // base: 42 SF tracts (no demographic properties exist in this data)
    base = new google.maps.Data({ map });
    base.addGeoJson(window.SF_TRACTS);
    styleBase();
    base.addListener('click', e => openInfo(e.latLng, tractHtml(e.feature)));
    base.addListener('mouseover', e => base.overrideStyle(e.feature, { strokeWeight: 2, strokeColor: css('--brand') }));
    base.addListener('mouseout', () => base.revertStyle());

    // optional layer: all SF 311 records
    all311 = new google.maps.Data({ map: null });
    all311.addGeoJson(window.SF_311);
    all311.setStyle(f => ({
      icon: { path: google.maps.SymbolPath.CIRCLE, scale: 3.2, fillOpacity: .9, strokeWeight: .5, strokeColor: '#fff',
        fillColor: f.getProperty('open_residential') ? '#3c6e71' : '#a3a9b3' },
      title: f.getProperty('request_id'),
    }));
    all311.addListener('click', e => openInfo(e.latLng, recHtml(e.feature)));

    // per-reply overlay
    overlay = new google.maps.Data({ map });
    overlay.setStyle(styleOverlay);
    overlay.addListener('click', e => {
      const f = e.feature, r = f.getProperty('role');
      openInfo(e.latLng, ['tract_focus', 'silent_distress'].includes(r) ? tractHtml(f) : recHtml(f));
      const ref = f.getProperty('ref'); if (ref) flashCard(ref);
    });
    overlay.addListener('mouseover', e => { const ref = e.feature.getProperty('ref'); if (ref) cardHover(ref, true); });
    overlay.addListener('mouseout', e => { const ref = e.feature.getProperty('ref'); if (ref) cardHover(ref, false); });

    ready = true;
    if (pending) { show(pending); pending = null; }
  }

  function styleBase() {
    base.setStyle(f => ({
      fillColor: layerState.shade ? burdenColor(f.getProperty('severe_burden_pct')) : '#000',
      fillOpacity: layerState.shade ? .55 : 0,
      strokeColor: '#6b7a8c', strokeOpacity: .45, strokeWeight: 1, zIndex: 1,
    }));
  }

  const DIAMOND = 'M 0,-1 1,0 0,1 -1,0 z';
  function styleOverlay(f) {
    const r = f.getProperty('role'), hi = f.getProperty('_hi');
    const pt = (fill, scale, path = google.maps.SymbolPath.CIRCLE, z = 10) => ({
      icon: { path, scale: hi ? scale * 1.5 : scale, fillColor: fill, fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2 },
      title: f.getProperty('label') || f.getProperty('request_id') || '', zIndex: hi ? 99 : z,
    });
    switch (r) {
      case 'tenant_block': return pt(css('--brand'), 10, google.maps.SymbolPath.CIRCLE, 20);
      case 'corroborating': return pt(css('--ok'), 8, google.maps.SymbolPath.CIRCLE, 25);
      case 'excluded': return pt('#7b828c', 8, DIAMOND, 12);
      case 'courthouse': return pt(css('--accent'), 9, google.maps.SymbolPath.BACKWARD_CLOSED_ARROW, 18);
      case 'route': return { strokeColor: css('--brand'), strokeWeight: 4, strokeOpacity: .85, zIndex: 5 };
      case 'tract_focus': return { fillColor: css('--accent'), fillOpacity: .08, strokeColor: css('--accent'), strokeWeight: 3, zIndex: 3, clickable: true };
      case 'silent_distress': return { fillColor: css('--audit'), fillOpacity: hi ? .45 : .28, strokeColor: css('--audit'), strokeWeight: 2, zIndex: 3 };
      case 'search_radius': return { visible: false }; // drawn as google.maps.Circle
      default: return {};
    }
  }

  function show(res) {
    const feats = res.blocks.flatMap(b => (b.geo && b.geo.features) || []);
    if (!feats.length) return;                    // keep the previous map view
    if (!ready) { pending = res; return; }
    info.close();
    overlay.forEach(f => overlay.remove(f));
    circles.forEach(c => c.setMap(null)); circles = [];
    if (dirRenderer) { dirRenderer.setMap(null); dirRenderer = null; }
    overlay.addGeoJson({ type: 'FeatureCollection', features: feats });
    feats.filter(f => f.properties.role === 'search_radius').forEach(f => circles.push(new google.maps.Circle({
      map, center: { lat: f.geometry.coordinates[1], lng: f.geometry.coordinates[0] }, radius: f.properties.radius_m,
      strokeColor: css('--warn'), strokeWeight: 2, fillColor: css('--warn'), fillOpacity: .06, clickable: false })));
    const route = feats.find(f => f.properties.role === 'route');
    document.getElementById('routenote').textContent = '';
    if (route) tryTransit(route);
    fit(feats);
    legend(feats);
  }

  function fit(feats) {
    const b = new google.maps.LatLngBounds();
    const add = c => b.extend({ lat: c[1], lng: c[0] });
    const walk = c => (typeof c[0] === 'number' ? add(c) : c.forEach(walk));
    feats.forEach(f => {
      walk(f.geometry.coordinates);
      if (f.properties.radius_m) { const d = f.properties.radius_m / 111000; add([f.geometry.coordinates[0], f.geometry.coordinates[1] + d]); add([f.geometry.coordinates[0], f.geometry.coordinates[1] - d]); }
    });
    map.fitBounds(b, 60);
    google.maps.event.addListenerOnce(map, 'idle', () => { if (map.getZoom() > 16) map.setZoom(16); });
  }

  // Real transit routing when the key allows Directions; otherwise keep the straight GeoJSON line.
  function tryTransit(route) {
    const [o, d] = [route.geometry.coordinates[0], route.geometry.coordinates.at(-1)];
    const note = document.getElementById('routenote');
    note.textContent = 'Route: straight line (estimate)';
    if (!key()) return;
    new google.maps.DirectionsService().route({
      origin: { lat: o[1], lng: o[0] }, destination: { lat: d[1], lng: d[0] }, travelMode: 'TRANSIT',
      transitOptions: { arrivalTime: new Date('2026-11-23T08:45:00-08:00') },
    }, (r, status) => {
      if (status !== 'OK') { note.textContent = `Route: straight line (Directions: ${status})`; return; }
      overlay.forEach(f => { if (f.getProperty('role') === 'route') overlay.remove(f); });
      dirRenderer = new google.maps.DirectionsRenderer({ map, directions: r, suppressMarkers: true, preserveViewport: true,
        polylineOptions: { strokeColor: css('--brand'), strokeWeight: 5, strokeOpacity: .85 } });
      const leg = r.routes[0].legs[0];
      note.textContent = `Route: Google transit · ${leg.duration.text} · leave by ${leg.departure_time ? leg.departure_time.text : '—'}`;
    });
  }

  // two-way highlight
  function highlight(ref, on) {
    if (!ready) return;
    overlay.forEach(f => { if (f.getProperty('ref') === ref) { f.setProperty('_hi', on); } });
  }
  function focus(ref) {
    if (!ready) return;
    overlay.forEach(f => {
      if (f.getProperty('ref') !== ref) return;
      const g = f.getGeometry();
      if (g.getType() === 'Point') { map.panTo(g.get()); openInfo(g.get(), recHtml(f)); }
      else { const b = new google.maps.LatLngBounds(); g.forEachLatLng(p => b.extend(p)); map.fitBounds(b, 80); openInfo(b.getCenter(), tractHtml(f)); }
    });
  }
  function cardHover(ref, on) { document.querySelectorAll(`[data-ref="${ref}"]`).forEach(e => e.classList.toggle('maphi', on)); }
  function flashCard(ref) {
    const els = [...document.querySelectorAll(`[data-ref="${ref}"]`)]; const e = els.at(-1); if (!e) return;
    e.scrollIntoView({ behavior: 'smooth', block: 'center' }); e.classList.add('flash'); setTimeout(() => e.classList.remove('flash'), 1400);
  }

  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function openInfo(pos, html) { info.setContent(`<div class="iw">${html}</div>`); info.setPosition(pos); info.open({ map }); }
  function recHtml(f) {
    const p = k => f.getProperty(k), r = p('role');
    if (r === 'tenant_block') return `<b>${esc(p('label'))}</b><div class="iws">100-block centroid only. The exact address is never stored or shown.</div>`;
    if (r === 'courthouse') return `<b>⚖ ${esc(p('label'))}</b><div class="iws">SF Superior Court · hearing Mon 11/23 9:00am</div>`;
    const tag = r === 'corroborating' ? '<span class="b ok">✓ Corroborating</span>' : r === 'excluded' ? `<span class="b grey">✕ Excluded</span>` : (p('open_residential') ? '<span class="b info">Open · residential</span>' : '<span class="b grey">Closed or non-residential</span>');
    return `<b class="mono">${esc(p('request_id'))}</b> ${tag}<div class="iws">${esc(p('type'))} · ${esc(p('block'))}<br>${esc(p('property_type'))} · ${esc(p('status'))} · created ${esc(p('created'))}</div>${p('reason') ? `<div class="iws"><b>Why excluded:</b> ${esc(p('reason'))}</div>` : ''}${p('distance_m') ? `<div class="iws">${p('distance_m') >= 1000 ? (p('distance_m') / 1000).toFixed(1) + ' km' : p('distance_m') + ' m'} from tenant's block</div>` : ''}<div class="iws prov">Public: SF 311 Open Data</div>`;
  }
  function tractHtml(f) {
    const p = k => f.getProperty(k);
    return `<b>Tract <span class="mono">${esc(p('geoid'))}</span></b>${p('silent_distress') ? ' <span class="b audit">🛡 Silent distress</span>' : ''}
      <div class="iws">Severe rent burden <b>${p('severe_burden_pct')}%</b> · ${p('renter_units')?.toLocaleString?.() ?? '—'} renter units<br>
      Annual filings <b>${p('annual_filings_modeled')}</b> <span class="b grey">MODELED</span> · open residential 311s <b>${p('open_residential_311')}</b></div>
      <div class="iws prov">Context only, never an individual risk score.</div>`;
  }

  function legend(feats) {
    const roles = new Set(feats.map(f => f.properties.role));
    const L = [
      ['tenant_block', '<i class="lg dot" style="background:var(--brand)"></i>Tenant block (100-block)'],
      ['corroborating', '<i class="lg dot" style="background:var(--ok)"></i>✓ Corroborating 311'],
      ['excluded', '<i class="lg dia"></i>✕ Excluded look-alike'],
      ['courthouse', '<i class="lg dot" style="background:var(--accent)"></i>⚖ Courthouse'],
      ['route', '<i class="lg line"></i>Route'],
      ['tract_focus', '<i class="lg box" style="border-color:var(--accent)"></i>Tenant\'s tract'],
      ['silent_distress', '<i class="lg box" style="border-color:var(--audit);background:var(--audit-soft)"></i>🛡 Silent-distress tract (aggregate)'],
      ['search_radius', '<i class="lg ring"></i>400 m search radius'],
    ].filter(([r]) => roles.has(r)).map(([, h]) => `<span>${h}</span>`);
    if (layerState.pts) L.push('<span><i class="lg dot" style="background:#3c6e71"></i>Open residential 311</span><span><i class="lg dot" style="background:#a3a9b3"></i>Other 311</span>');
    if (layerState.shade) L.push(`<span class="ramp">Severe rent burden &lt;10% ${BURDEN_STEPS.map(([t, c]) => `<i style="background:${c}" title="&lt; ${t}%"></i>`).join('')} 25%+</span>`);
    document.getElementById('maplegend').innerHTML = L.join('');
  }
  function toggle(which, on) {
    layerState[which] = on;
    if (!ready) return;
    if (which === 'shade') styleBase();
    if (which === 'pts') all311.setMap(on ? map : null);
    const feats = []; overlay.forEach(f => feats.push({ properties: { role: f.getProperty('role') } }));
    legend(feats);
  }

  return { load, show, highlight, focus, toggle, saveKey };
})();
