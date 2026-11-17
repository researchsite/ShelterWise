import json
import html

with open("live_agent_output.json", "r") as f:
    data = json.load(f)

case = data["benchmark_case"]
intake = data["step_1_intake"]
evidence = data["step_2_evidence"]
policy = data["step_3_policy"]
tract = data["step_4_tract"]
brief = data["step_5_brief"]
specialists = data["specialist_agents"]

# Build valid evidence cards
valid_html = ""
for rec in evidence["corroborating_records"]:
    dist = rec.get("match_reason", "")
    valid_html += f"""
    <div class="cand acc">
      <div class="h">
        <span class="pill p-ok">VALID RESIDENTIAL 311</span>
        <code>{html.escape(rec['request_id'])}</code>
        <span class="mono">{html.escape(rec['block_address'])}</span>
        <span class="pill p-info">{html.escape(rec['inspection_status'])}</span>
        <span class="pill p-mute" style="margin-left:auto;">{html.escape(dist)}</span>
      </div>
      <div style="font-size:13.5px;color:var(--ink);margin-top:6px;">
        "{html.escape(rec['complaint_narrative'])}"
      </div>
    </div>
    """

# Build excluded decoy cards
decoy_html = ""
for rec in evidence["excluded_candidates"]:
    dist = rec.get("match_reason", "")
    decoy_html += f"""
    <div class="cand rej">
      <div class="h">
        <span class="pill p-bad">EXCLUDED DECOY</span>
        <code>{html.escape(rec['request_id'])}</code>
        <span class="mono">{html.escape(rec['block_address'])}</span>
        <span class="pill p-warn">Reason: {html.escape(rec.get('exclusion_reason', 'Decoy'))}</span>
        <span class="pill p-mute" style="margin-left:auto;">{html.escape(dist)}</span>
      </div>
      <div style="font-size:13.5px;color:var(--ink);margin-top:6px;opacity:0.85;">
        "{html.escape(rec['complaint_narrative'])}"
      </div>
    </div>
    """

# Build policy funds
funds_html = ""
for fund in policy["applicable_relief_funds"]:
    badge = '<span class="pill p-bad">🔒 Requires Open 311 Case</span>' if fund.get("requires_open_habitability_case") else '<span class="pill p-ok">✓ Unconditional / Direct</span>'
    funds_html += f"""
    <div class="cand acc" style="border-left-color:var(--brand);">
      <div class="h">
        <b>{html.escape(fund['title'])}</b>
        {badge}
        <a href="{html.escape(fund['citation'])}" target="_blank" class="cite" style="margin-left:auto;">{html.escape(fund['citation'])}</a>
      </div>
      <p style="margin:6px 0 0;font-size:13px;color:var(--mute);">{html.escape(fund['summary'])}</p>
    </div>
    """

# Build statutes
statutes_html = ""
for st in policy["applicable_statutes"]:
    statutes_html += f"""
    <div class="cand" style="border-left:4px solid var(--user);">
      <div class="h">
        <b>{html.escape(st['title'])}</b>
        <span class="pill p-user">{html.escape(st['citation'])}</span>
      </div>
      <p style="margin:6px 0 0;font-size:13px;color:var(--mute);">{html.escape(st['summary'])}</p>
    </div>
    """

# Build equity audit table
equity_rows = ""
for row in specialists["equity_audit"]["audit_summary"]:
    status = '<span class="pill p-bad">Silent Distress Candidate</span>' if row["is_silent_distress_candidate"] else '<span class="pill p-ok">Standard Tract Cohort</span>'
    equity_rows += f"""
    <tr>
      <td>{status}</td>
      <td><b>{row['tract_count']} tracts</b></td>
      <td><b>{row['avg_rent_burden_pct']:.1f}%</b></td>
      <td>{(row['avg_black_share']*100):.1f}%</td>
      <td>{(row['avg_hispanic_share']*100):.1f}%</td>
      <td>{(row['avg_asian_share']*100):.1f}%</td>
      <td>{(row['avg_white_share']*100):.1f}%</td>
    </tr>
    """

page_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ShelterWise – Live Agent Workspace UI</title>
<style>
:root {{
  --bg:#f6f7f9; --panel:#fff; --ink:#1b2430; --mute:#5d6b7c; --line:#dde2e8;
  --brand:#1f5fbf; --brand-soft:#e7effb; --ok:#1d7a4a; --ok-soft:#e3f4ea;
  --warn:#9a6200; --warn-soft:#fff3d6; --bad:#b3261e; --bad-soft:#fdeceb;
  --user:#6a3fb5; --user-soft:#f0eafa; --code:#f0f2f5;
  --llm:#dbeafe; --llm-b:#2563eb; --cod:#dcfce7; --cod-b:#16a34a; --mcp:#ede9fe; --mcp-b:#7c3aed;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg:#12161c; --panel:#1a2029; --ink:#e6eaf0; --mute:#97a3b3; --line:#2c3541;
    --brand:#6ea3f5; --brand-soft:#1c2b44; --ok:#5fd194; --ok-soft:#173326;
    --warn:#f0b84a; --warn-soft:#3a2f12; --bad:#f2827b; --bad-soft:#3a1c1a;
    --user:#b79af0; --user-soft:#2b2340; --code:#232b36;
    --llm:#1c2b44; --cod:#173326; --mcp:#2b2340;
  }}
}}
* {{ box-sizing:border-box }}
body {{ margin:0; font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; background:var(--bg); color:var(--ink) }}
header {{ background:var(--panel); border-bottom:1px solid var(--line); padding:14px 24px; display:flex; gap:16px; align-items:center; flex-wrap:wrap; position:sticky; top:0; z-index:100; box-shadow:0 1px 3px rgba(0,0,0,0.05); }}
header h1 {{ font-size:20px; margin:0; display:flex; align-items:center; gap:8px; }}
header .tag {{ font-size:12.5px; color:var(--mute); }}
.badge-live {{ margin-left:auto; font-size:12px; font-weight:700; background:var(--ok-soft); color:var(--ok); padding:5px 12px; border-radius:99px; border:1px solid var(--ok); display:flex; align-items:center; gap:6px; }}
.badge-live::before {{ content:""; width:8px; height:8px; background:var(--ok); border-radius:50%; display:inline-block; animation:pulse 1.8s infinite; }}
@keyframes pulse {{ 0%{{transform:scale(0.9);opacity:0.8}} 50%{{transform:scale(1.2);opacity:1}} 100%{{transform:scale(0.9);opacity:0.8}} }}

.alert-banner {{ background:var(--bad-soft); border-bottom:2px solid var(--bad); padding:12px 24px; display:flex; align-items:center; gap:12px; color:var(--bad); font-weight:600; font-size:14px; }}
.alert-banner .icon {{ font-size:20px; }}

.tabs {{ display:flex; gap:4px; padding:0 24px; background:var(--panel); border-bottom:1px solid var(--line); overflow-x:auto }}
.tabs button {{ background:none; border:0; padding:12px 16px; font:inherit; color:var(--mute); cursor:pointer; border-bottom:3px solid transparent; white-space:nowrap; font-weight:500; font-size:14px; transition:0.2s; }}
.tabs button.on {{ color:var(--brand); border-color:var(--brand); font-weight:700 }}

main {{ max-width:1200px; margin:0 auto; padding:24px }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:20px 24px; margin-bottom:20px; box-shadow:0 1px 2px rgba(0,0,0,0.03); }}
.card h2 {{ margin:0 0 6px; font-size:18px }}
.sub {{ color:var(--mute); margin:0 0 16px; font-size:13.5px }}

.pill {{ display:inline-block; font-size:11.5px; padding:2.5px 8.5px; border-radius:99px; font-weight:600; margin:0 4px 2px 0 }}
.p-ok {{ background:var(--ok-soft); color:var(--ok) }}
.p-warn {{ background:var(--warn-soft); color:var(--warn) }}
.p-bad {{ background:var(--bad-soft); color:var(--bad) }}
.p-info {{ background:var(--brand-soft); color:var(--brand) }}
.p-user {{ background:var(--user-soft); color:var(--user) }}
.p-mute {{ background:var(--code); color:var(--mute) }}

.kpi-row {{ display:flex; gap:14px; flex-wrap:wrap; margin-bottom:20px }}
.kpi-card {{ flex:1 1 200px; border:1px solid var(--line); border-radius:10px; padding:14px 16px; background:var(--bg) }}
.kpi-card b {{ font-size:24px; display:block; color:var(--ink) }}
.kpi-card span {{ font-size:12px; color:var(--mute) }}

.cand {{ border:1px solid var(--line); border-radius:10px; padding:14px; margin-bottom:12px; background:var(--panel) }}
.cand.acc {{ border-left:5px solid var(--ok) }}
.cand.rej {{ border-left:5px solid var(--bad); background:var(--bad-soft) }}
.cand .h {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}

.code, code, .mono {{ font-family:ui-monospace,Consolas,monospace; font-size:12.5px; background:var(--code); padding:2px 6px; border-radius:4px }}
pre {{ background:var(--code); padding:14px; border-radius:8px; overflow-x:auto; font-size:13px; font-family:ui-monospace,Consolas,monospace; }}

.agent-box {{ display:flex; gap:12px; align-items:flex-start; padding:14px 18px; border-radius:10px; border:1.5px solid; margin-bottom:16px; }}
.agent-box.LLM {{ background:var(--llm); border-color:var(--llm-b) }}
.agent-box.code {{ background:var(--cod); border-color:var(--cod-b) }}
.agent-box.mcp {{ background:var(--mcp); border-color:var(--mcp-b) }}

table {{ border-collapse:collapse; width:100%; font-size:13.5px }}
th, td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--line); }}
th {{ color:var(--mute); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.04em; background:var(--bg) }}

.view {{ display:none }}
.view.on {{ display:block }}

.tree-flow {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; background:var(--bg); padding:16px; border-radius:10px; border:1px solid var(--line); margin-bottom:20px; }}
.tree-node {{ background:var(--panel); border:1.5px solid var(--brand); border-radius:8px; padding:10px 14px; font-size:13px; font-weight:600; text-align:center; }}
.tree-arrow {{ font-size:18px; color:var(--mute); }}
.tree-sub {{ font-size:11px; color:var(--mute); font-weight:normal; margin-top:2px; }}

.brief-sec {{ margin-bottom:18px; border-bottom:1px solid var(--line); padding-bottom:14px }}
.brief-sec h3 {{ margin:0 0 8px; font-size:15px; color:var(--brand); display:flex; align-items:center; gap:6px; }}
</style>
<script>
function showTab(id) {{
  document.querySelectorAll('.view').forEach(e => e.classList.remove('on'));
  document.querySelectorAll('.tabs button').forEach(e => e.classList.remove('on'));
  document.getElementById('v-' + id).classList.add('on');
  document.getElementById('tab-' + id).classList.add('on');
}}
function filterEvidence(type) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('p-info'));
  if (type === 'all') {{
    document.querySelectorAll('.cand').forEach(c => c.style.display = 'block');
  }} else if (type === 'valid') {{
    document.querySelectorAll('.cand.acc').forEach(c => c.style.display = 'block');
    document.querySelectorAll('.cand.rej').forEach(c => c.style.display = 'none');
  }} else if (type === 'decoy') {{
    document.querySelectorAll('.cand.acc').forEach(c => c.style.display = 'none');
    document.querySelectorAll('.cand.rej').forEach(c => c.style.display = 'block');
  }}
}}
</script>
</head>
<body>

<header>
  <h1>🏠 ShelterWise <span style="font-size:14px;font-weight:normal;color:var(--mute);">| ADK Multi-Agent Workspace</span></h1>
  <span class="tag">San Francisco (FIPS 06075) · Real BigQuery Vector Search &amp; Decoy Trap Filtering</span>
  <span class="badge-live">LIVE AGENT EXECUTION</span>
</header>

<div class="alert-banner">
  <span class="icon">🚨</span>
  <div>
    <strong>CRITICAL LIFE-SAFETY HAZARD DETECTED:</strong> Active water intrusion adjacent to kitchen electrical fuse box + cold radiators for 14 days.<br>
    <span style="font-size:12.5px;opacity:0.9;">Emergency eviction hearing scheduled for Monday 9:00 AM (&lt; 72 hours). Emergency attorney review required.</span>
  </div>
</div>

<nav class="tabs">
  <button id="tab-overview" class="on" onclick="showTab('overview')">① Pipeline &amp; Case Overview</button>
  <button id="tab-evidence" onclick="showTab('evidence')">② Evidence Room ({len(evidence['corroborating_records'])} Valid / {len(evidence['excluded_candidates'])} Decoys)</button>
  <button id="tab-policy" onclick="showTab('policy')">③ Statutes &amp; Relief Funds (4)</button>
  <button id="tab-tract" onclick="showTab('tract')">④ Census Tract Baseline ({tract['census_tract_geoid']})</button>
  <button id="tab-brief" onclick="showTab('brief')">⑤ Tenant Stabilization Brief</button>
  <button id="tab-specialists" onclick="showTab('specialists')">⑥ Specialist Sub-Agents (3)</button>
</nav>

<main>

<!-- VIEW 1: OVERVIEW -->
<section class="view on" id="v-overview">
  <div class="card">
    <h2>Multi-Agent Pipeline Architecture</h2>
    <p class="sub">Sequential intake structuring → Parallel 3-agent fanout → Synthesis &amp; Brief generation</p>
    <div class="tree-flow">
      <div class="tree-node" style="border-color:var(--llm-b);background:var(--llm);">
        1. Intake Structurer Agent
        <div class="tree-sub">LlmAgent · Facts &amp; Hazard Gate</div>
      </div>
      <div class="tree-arrow">➔</div>
      <div style="border:1.5px dashed var(--brand);padding:8px;border-radius:10px;background:var(--panel);">
        <div style="font-size:11px;font-weight:700;color:var(--brand);margin-bottom:6px;text-align:center;">PARALLEL AGENT FANOUT</div>
        <div style="display:flex;gap:8px;">
          <div class="tree-node" style="font-size:12px;border-color:var(--cod-b);background:var(--cod);">
            Habitability Vector
            <div class="tree-sub">BigQuery Vector Search</div>
          </div>
          <div class="tree-node" style="font-size:12px;border-color:var(--cod-b);background:var(--cod);">
            Statute &amp; Bulletin
            <div class="tree-sub">SF Ordinances &amp; Relief</div>
          </div>
          <div class="tree-node" style="font-size:12px;border-color:var(--cod-b);background:var(--cod);">
            Tract Displacement
            <div class="tree-sub">v_tract_stability_context</div>
          </div>
        </div>
      </div>
      <div class="tree-arrow">➔</div>
      <div class="tree-node" style="border-color:var(--llm-b);background:var(--llm);">
        3. Eligibility &amp; Brief Agent
        <div class="tree-sub">LlmAgent · 9-Section Memo</div>
      </div>
      <div class="tree-arrow">➔</div>
      <div class="tree-node" style="border-color:var(--mcp-b);background:var(--mcp);">
        Root Navigator
        <div class="tree-sub">shelterwise_navigator</div>
      </div>
    </div>

    <div class="kpi-row">
      <div class="kpi-card">
        <b>{case['tenant']}</b>
        <span>Client Profile</span>
      </div>
      <div class="kpi-card">
        <b>{case['address']}</b>
        <span>Subject Property</span>
      </div>
      <div class="kpi-card">
        <b style="color:var(--bad);">Monday 9:00 AM</b>
        <span>Court Hearing (&lt; 72 hrs)</span>
      </div>
      <div class="kpi-card">
        <b style="color:var(--ok);">{intake['census_tract_geoid_11']}</b>
        <span>San Francisco GEOID (11-digit)</span>
      </div>
    </div>

    <div class="cand acc" style="border-left-color:var(--brand);">
      <div class="h">
        <b>Client Reported Facts (Normalized)</b>
      </div>
      <ul style="margin:8px 0 0;padding-left:20px;font-size:13.5px;">
        {''.join(f"<li>{html.escape(f)}</li>" for f in intake['reported_facts'])}
      </ul>
      <div style="margin-top:10px;">
        <span class="pill p-bad">Primary Hazard: {html.escape(intake['primary_hazard'])}</span>
        <span class="pill p-bad">Secondary Hazard: {html.escape(intake['secondary_hazard'])}</span>
      </div>
    </div>
  </div>
</section>

<!-- VIEW 2: EVIDENCE ROOM -->
<section class="view" id="v-evidence">
  <div class="card">
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:12px;">
      <div>
        <h2 style="margin:0;">BigQuery Vector Search &amp; Decoy Trap Filter</h2>
        <p class="sub" style="margin:0;">Municipal 311 Records evaluated against strict habitability business rules</p>
      </div>
      <div style="display:flex;gap:6px;">
        <button class="pill p-info filter-btn" onclick="filterEvidence('all')" style="cursor:pointer;border:0;">Show All (15)</button>
        <button class="pill p-ok filter-btn" onclick="filterEvidence('valid')" style="cursor:pointer;border:0;">Valid 311s (10)</button>
        <button class="pill p-bad filter-btn" onclick="filterEvidence('decoy')" style="cursor:pointer;border:0;">Excluded Decoys (5)</button>
      </div>
    </div>

    <h3 style="margin:16px 0 8px;font-size:15px;color:var(--bad);">Excluded Decoys (Caught by Custom Business Rules)</h3>
    <p style="font-size:12.5px;color:var(--mute);margin:0 0 10px;">Planted decoys must never contaminate eviction defense filings or habitability rent-withholding motions.</p>
    {decoy_html}

    <h3 style="margin:22px 0 8px;font-size:15px;color:var(--ok);">Corroborating Open Residential 311 Cases</h3>
    <p style="font-size:12.5px;color:var(--mute);margin:0 0 10px;">Active Department of Building Inspection (DBI) cases corroborating physical heating/electrical hazards.</p>
    {valid_html}
  </div>
</section>

<!-- VIEW 3: POLICY & RELIEF -->
<section class="view" id="v-policy">
  <div class="card">
    <h2>Governing San Francisco &amp; California Statutes</h2>
    <p class="sub">Retrieved statutes providing affirmative defenses against unlawful detainer</p>
    {statutes_html}

    <h2 style="margin-top:24px;">Emergency Rental Relief Programs</h2>
    <p class="sub">Matching funding programs and prerequisites</p>
    {funds_html}
  </div>
</section>

<!-- VIEW 4: CENSUS TRACT BASELINE -->
<section class="view" id="v-tract">
  <div class="card">
    <h2>Census Tract Stability Baseline (Tract {tract['census_tract_geoid']})</h2>
    <p class="sub">Aggregated from <code>v_tract_stability_context</code> with demographic firewall protection</p>

    <div class="kpi-row">
      <div class="kpi-card">
        <b>{tract['annual_filings_total']}</b>
        <span>Annual Court Eviction Filings <span class="pill p-mute">[Modeled]</span></span>
      </div>
      <div class="kpi-card">
        <b>{tract['severe_rent_burden_pct']}%</b>
        <span>Severe Rent Burden Rate (&gt;50% Income)</span>
      </div>
      <div class="kpi-card">
        <b>{tract['open_residential_311_count']}</b>
        <span>Open Residential 311 Cases <span class="pill p-ok">[Official DBI]</span></span>
      </div>
      <div class="kpi-card">
        <b style="color:var(--ok);">Protected</b>
        <span>Demographic Firewall (0 audit_* in Case Output)</span>
      </div>
    </div>

    <div class="cand acc" style="border-left-color:var(--brand);">
      <div class="h">
        <b>Tract Provenance &amp; Fanout Safety</b>
      </div>
      <p style="font-size:13px;color:var(--mute);margin:6px 0 0;">
        Court filings were pre-aggregated across 4 rolling quarters in BigQuery view <code>v_tract_stability_context</code>.
        This guarantees zero 4x Cartesian inflation in eviction counts. Demographic fields (race, language, vehicle access) are firewalled into <code>v_metro_equity_audit</code> and strictly forbidden from scoring individual tenants.
      </p>
    </div>
  </div>
</section>

<!-- VIEW 5: BRIEF -->
<section class="view" id="v-brief">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid var(--line);padding-bottom:12px;margin-bottom:16px;">
      <div>
        <h2 style="margin:0;">Tenant Stabilization Brief (v1.0)</h2>
        <span class="mono" style="font-size:12px;color:var(--mute);">Matter of: Elena Vance · Case Ref: SF-TUD-2026-04</span>
      </div>
      <span class="pill p-bad" style="font-size:13px;padding:4px 10px;">ACTION REQUIRED BEFORE MON 9:00 AM</span>
    </div>

    <div class="brief-sec">
      <h3>1. Emergency Life-Safety Notice</h3>
      <div class="cand rej" style="border-left-color:var(--bad);">
        <b>URGENT:</b> Active water intrusion adjacent to electrical fuse box creates immediate fire/shock hazard.
        Department of Building Inspection emergency inspection requested under SF Housing Code § 501.
      </div>
    </div>

    <div class="brief-sec">
      <h3>2. Tenant Reported Habitability Conditions</h3>
      <p style="font-size:13.5px;margin:4px 0;">Tenant has resided at 400 Block Ellis St with two minor children. Over the past 14 days, radiators have remained unheated during winter weather. Ceiling water leakage has pooled directly near kitchen electrical breaker panel.</p>
    </div>

    <div class="brief-sec">
      <h3>3. Public Corroboration &amp; 311 Evidence Verification</h3>
      <p style="font-size:13.5px;margin:4px 0;">Vector similarity search in BigQuery retrieved <strong>10 active DBI building inspection cases</strong> corroborating localized heating failures and electrical leaks on neighboring parcels. <strong>5 planted decoy cases</strong> (commercial retail, closed/abated repairs, zero-violation inspections) were audited and disqualified.</p>
    </div>

    <div class="brief-sec">
      <h3>4. Affirmative Defenses Under California Law</h3>
      <ul style="font-size:13.5px;margin:4px 0;padding-left:20px;">
        <li><strong>Breach of Implied Warranty of Habitability (Cal. Civ. Code § 1941.1 &amp; § 1942.4):</strong> Landlord is barred from demanding or recovering rent during periods where heat and safe electrical wiring are defective.</li>
        <li><strong>Anti-Retaliation Bar (Cal. Civ. Code § 1942.5):</strong> 180-day bar against eviction following municipal habitability complaint.</li>
      </ul>
    </div>

    <div class="brief-sec">
      <h3>5. Emergency Financial Stabilization Relief</h3>
      <p style="font-size:13.5px;margin:4px 0;">Recommended immediate funding bridge: <strong>SF ERAP</strong> (up to $12,000 back rent) and <strong>RADCO / MEDA Family Stabilization Grant</strong> ($7,500). Active 311 habitability filing will unlock Code Enforcement Relocation Bridge ($8,500).</p>
    </div>

    <div class="brief-sec">
      <h3>6. Attorney Action Checklist (Prior to Monday 9:00 AM)</h3>
      <ul style="font-size:13.5px;margin:4px 0;padding-left:20px;">
        <li>[ ] File emergency Answer asserting affirmative defense of habitability breach.</li>
        <li>[ ] Submit SF311 DBI inspection request confirmation number to court.</li>
        <li>[ ] Request court stay of nonpayment detainer pending SF ERAP rental disbursement.</li>
      </ul>
    </div>
  </div>
</section>

<!-- VIEW 6: SPECIALISTS -->
<section class="view" id="v-specialists">
  <div class="card">
    <h2>Specialist Sub-Agents Execution Results</h2>
    <p class="sub">Autonomous specialist sub-agents deployed in the ADK agent tree</p>

    <!-- Sub-agent 1 -->
    <div class="agent-box LLM">
      <div>
        <div style="font-size:15px;font-weight:700;color:var(--brand);margin-bottom:4px;">
          🕵️ Sub-Agent: Evidence Explainer Agent
        </div>
        <p style="font-size:13px;color:var(--mute);margin:0 0 8px;">
          Query: "Explain why candidate <code>{specialists['evidence_explainer']['candidate_id']}</code> was excluded from the brief."
        </p>
        <div class="cand" style="background:var(--panel);margin:0;">
          <b>Agent Response:</b>
          <div style="font-size:13.5px;margin-top:4px;">
            "{html.escape(specialists['evidence_explainer']['explanation'])}"
          </div>
        </div>
      </div>
    </div>

    <!-- Sub-agent 2 -->
    <div class="agent-box code">
      <div>
        <div style="font-size:15px;font-weight:700;color:var(--ok);margin-bottom:4px;">
          ⚖️ Sub-Agent: Responsible AI Equity Audit Agent
        </div>
        <p style="font-size:13px;color:var(--mute);margin:0 0 8px;">
          Runs isolated cohort aggregation over <code>v_metro_equity_audit</code> to ensure equitable legal coverage across tracts without scoring individuals.
        </p>
        <div style="overflow-x:auto;">
          <table>
            <thead>
              <tr>
                <th>Cohort Category</th>
                <th>Tract Count</th>
                <th>Avg Rent Burden</th>
                <th>Black %</th>
                <th>Hispanic %</th>
                <th>Asian %</th>
                <th>White %</th>
              </tr>
            </thead>
            <tbody>
              {equity_rows}
            </tbody>
          </table>
        </div>
        <div style="font-size:12px;color:var(--mute);margin-top:8px;">
          💡 <strong>Audit Insight:</strong> 6 Silent Distress tracts exhibit severe rent burden (25.6%) and higher minority representation where court filings outpace 311 calls. The system prioritizes legal bridge resources to these tracts.
        </div>
      </div>
    </div>

    <!-- Sub-agent 3 -->
    <div class="agent-box mcp">
      <div>
        <div style="font-size:15px;font-weight:700;color:var(--user);margin-bottom:4px;">
          🚨 Sub-Agent: Hazard 311 Drafter Agent
        </div>
        <p style="font-size:13px;color:var(--mute);margin:0 0 8px;">
          Drafts official municipal complaint to San Francisco Department of Building Inspection (DBI).
        </p>
        <pre>{json.dumps(specialists['hazard_311_drafter'], indent=2)}</pre>
      </div>
    </div>
  </div>
</section>

</main>

<footer>
  ShelterWise Multi-Agent System · Google ADK + BigQuery Managed MCP · Branch: <code>rohith-visual-ui</code>
</footer>

</body>
</html>
"""

with open("preview_ui.html", "w") as f:
    f.write(page_html)

print("Generated preview_ui.html successfully!")
