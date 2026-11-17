# Regenerate geo_sf.js from repo data:  python tools/build_geo.py ../../data geo_sf.js   (needs pyarrow)
import json, struct, sys
import pyarrow.parquet as pq
data_dir, out = sys.argv[1], sys.argv[2]

def wkb_polys(b):
    """Decode WKB (Polygon/MultiPolygon/GeometryCollection) -> GeoJSON polygonal geometry, 5 dp."""
    def geom(buf, off):
        le = buf[off] == 1; e = '<' if le else '>'
        (t,) = struct.unpack_from(e+'I', buf, off+1); off += 5; t &= 0xff
        if t == 3:
            (nr,) = struct.unpack_from(e+'I', buf, off); off += 4; rings = []
            for _ in range(nr):
                (n,) = struct.unpack_from(e+'I', buf, off); off += 4
                pts = struct.unpack_from(e+'%dd' % (2*n), buf, off); off += 16*n
                rings.append([[round(pts[i],5), round(pts[i+1],5)] for i in range(0, 2*n, 2)])
            return [rings], off
        if t in (6, 7):
            (n,) = struct.unpack_from(e+'I', buf, off); off += 4; polys = []
            for _ in range(n):
                ps, off = geom(buf, off); polys += ps
            return polys, off
        if t == 1: return [], off + 16
        if t == 2:
            (n,) = struct.unpack_from(e+'I', buf, off); return [], off + 4 + 16*n
        raise ValueError(t)
    polys, _ = geom(b, 0)
    return {"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1 else {"type": "MultiPolygon", "coordinates": polys}

acs = [r for r in pq.read_table(f'{data_dir}/acs_tract_housing_tenure.parquet').to_pylist() if r['metro_area'] == 'San Francisco']
fil = [r for r in pq.read_table(f'{data_dir}/court_eviction_filings.parquet').to_pylist() if r['metro_area'] == 'San Francisco']
c311 = [r for r in pq.read_table(f'{data_dir}/municipal_311_housing_complaints.parquet').to_pylist() if r['metro_area'] == 'San Francisco']
g = lambda x: str(x).zfill(11)

filings = {}
for r in fil:
    k = g(r['census_tract_geoid'])
    filings[k] = filings.get(k, 0) + r['nonpayment_filings_count'] + r['holdover_or_no_fault_filings_count']

def is_open(r):
    return r['property_type'] == 'Residential' and r['closed_date'] is None and not str(r['inspection_status']).lower().startswith('closed')
open_cnt = {}
for r in c311:
    if is_open(r): open_cnt[g(r['census_tract_geoid'])] = open_cnt.get(g(r['census_tract_geoid']), 0) + 1

tracts = []
for r in acs:   # NOTE: audit_* columns intentionally NOT exported
    k = g(r['census_tract_geoid'])
    burden = round(100 * r['renter_hh_rent_50_pct_plus_count'] / r['renter_occupied_units'], 1) if r['renter_occupied_units'] else 0
    oc = open_cnt.get(k, 0)
    tracts.append({"type": "Feature", "geometry": wkb_polys(r['tract_geom']), "properties": {
        "geoid": k, "severe_burden_pct": burden, "annual_filings_modeled": filings.get(k, 0),
        "open_residential_311": oc, "silent_distress": oc <= 1 and burden >= 20,
        "renter_units": r['renter_occupied_units'], "lat": round(r['latitude'], 5), "lng": round(r['longitude'], 5)}})

pts = []
for r in c311:
    pts.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(r['longitude'], 5), round(r['latitude'], 5)]},
        "properties": {"request_id": r['request_id'], "block": r['block_address'].split(',')[0], "type": r['raw_complaint_type'],
            "property_type": r['property_type'], "status": r['inspection_status'], "open_residential": is_open(r),
            "created": str(r['created_date'])[:10], "geoid": g(r['census_tract_geoid'])}})

with open(out, 'w') as f:
    f.write('// Generated from data/*.parquet (San Francisco). audit_* columns intentionally excluded.\n')
    f.write('window.SF_TRACTS = ' + json.dumps({"type": "FeatureCollection", "features": tracts}, separators=(',', ':')) + ';\n')
    f.write('window.SF_311 = ' + json.dumps({"type": "FeatureCollection", "features": pts}, separators=(',', ':')) + ';\n')
sd = [t['properties']['geoid'] for t in tracts if t['properties']['silent_distress']]
print('tracts', len(tracts), 'points', len(pts), 'open_res', sum(p['properties']['open_residential'] for p in pts), 'silent', len(sd))
print([ (p['properties']['request_id'],p['geometry']['coordinates']) for p in pts if p['properties']['request_id'] in ('SF-202665182','DECOY-SANF-01','DECOY-SANF-04','DECOY-SANF-07')])
t=[t for t in tracts if t['properties']['geoid']=='06075016300'][0]['properties']; print(t)
