/**
 * Google Stitch Design System: Component Logic & Helpers (components.js)
 * Project: ShelterWise — Housing Stability & Habitability Defense Navigator
 */

window.StitchComponents = {
  /**
   * Toggle Trauma-Informed Distress Mode
   */
  toggleDistressMode: function() {
    const isDistress = document.body.classList.toggle('distress-mode');
    const btn = document.getElementById('distress-toggle-btn');
    if (btn) {
      btn.innerHTML = isDistress ? '⚡ Standard Mode' : '🚨 Distress Mode (High Contrast)';
      btn.classList.toggle('active', isDistress);
    }
    const banner = document.getElementById('stitch-distress-banner');
    if (banner) {
      banner.style.display = isDistress ? 'flex' : 'none';
    }
  },

  /**
   * Render Statutory 35-Day Repair Clock (Cal. Civ. Code § 1942.4)
   * @param {number} daysElapsed 
   */
  renderHabitabilityClock: function(daysElapsed = 42) {
    const isExpired = daysElapsed >= 35;
    const overDays = daysElapsed - 35;
    const percent = Math.min(100, Math.round((daysElapsed / 35) * 100));
    const dialColor = isExpired ? 'var(--stitch-alert-crimson)' : 'var(--stitch-relief-green)';
    
    return `
      <div class="stitch-clock-dial ${isExpired ? 'clock-expired' : ''}">
        <div class="stitch-clock-circle" style="background: conic-gradient(${dialColor} ${percent}%, var(--stitch-surface-subtle) 0);">
          <div class="stitch-clock-inner" style="color: ${dialColor};">
            ${daysElapsed}d
          </div>
        </div>
        <div class="stitch-clock-meta">
          <h4>${isExpired ? '⚠️ Landlord Repair Clock Expired' : '⏱️ 35-Day Statutory Window'}</h4>
          <p>
            ${isExpired 
              ? `Day ${daysElapsed} of 35 days. Landlord exceeded legal repair limit by <strong>${overDays} days</strong>. Eviction action is barred under <em>Cal. Civ. Code § 1942.4</em>.`
              : `Day ${daysElapsed} of 35 statutory window. Landlord has ${35 - daysElapsed} days remaining to complete certified repairs.`}
          </p>
        </div>
      </div>
    `;
  },

  /**
   * Render Interactive Relief Funding Meter
   * @param {number} rentArrears 
   * @param {number} erap 
   * @param {number} meda 
   */
  renderReliefFundingMeter: function(rentArrears = 4200, erap = 3500, meda = 700) {
    const totalGrants = erap + meda;
    const remaining = Math.max(0, rentArrears - totalGrants);
    const coveragePercent = Math.min(100, Math.round((totalGrants / rentArrears) * 100));
    
    return `
      <div class="stitch-relief-meter">
        <div class="stitch-relief-calc">
          <span>Past Rent Due: $${rentArrears.toLocaleString()}</span>
          <span>−</span>
          <span>SF ERAP: $${erap.toLocaleString()}</span>
          <span>−</span>
          <span>MEDA: $${meda.toLocaleString()}</span>
          <span>=</span>
          <span style="color: var(--stitch-relief-green);">Remaining: $${remaining.toFixed(2)} (${coveragePercent}% Covered!)</span>
        </div>
        <div class="stitch-relief-bar-bg">
          <div class="stitch-relief-bar-fill" style="width: ${coveragePercent}%;"></div>
        </div>
      </div>
    `;
  },

  /**
   * Render Decoy Rejection Card (The False Lead Filter)
   * @param {string} title 
   * @param {string} address 
   * @param {string} reason 
   */
  renderDecoyCard: function(title, address, reason) {
    return `
      <div class="stitch-decoy-card">
        <div class="stitch-decoy-title">
          <span>🚫 ${title}</span>
          <span class="stitch-badge stitch-badge-danger">Filtered Lead</span>
        </div>
        <div style="font-size: 11.5px; color: var(--stitch-ink-muted); margin-bottom: 4px;">${address}</div>
        <p class="stitch-decoy-desc"><strong>Why excluded:</strong> ${reason}</p>
      </div>
    `;
  },

  /**
   * Render Proximity Radar
   * @param {number} distanceMeters 
   * @param {number} transitMinutes 
   */
  renderProximityRadar: function(distanceMeters = 12, transitMinutes = 22) {
    return `
      <div class="stitch-proximity-radar">
        <div class="stitch-radar-icon">📍</div>
        <div class="stitch-radar-meta">
          <h5>${distanceMeters} Meters from Residence</h5>
          <p>Verified City Hall citation on same block · ${transitMinutes} min to SF Superior Court via MUNI 31</p>
        </div>
      </div>
    `;
  },

  /**
   * Switch Top-Level Navigation Tab
   * @param {string} tabId 
   */
  switchTab: function(tabId) {
    document.querySelectorAll('.stitch-nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.stitch-tab-view').forEach(v => v.style.display = 'none');

    const activeBtn = document.querySelector(`[data-tab="${tabId}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    const activeView = document.getElementById(`tab-view-${tabId}`);
    if (activeView) activeView.style.display = 'block';

    if (tabId === 'map' && window.map) {
      setTimeout(() => window.map.invalidateSize(), 200);
    }
  }
};
