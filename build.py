"""Build neighborhood dataset for the Seattle-area neighborhood finder.

Inputs: ../raw (downloaded public data). Output: ../site/data.json
"""
import json, re, zipfile, io, math, datetime, collections, os
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import shape, Point
from shapely.validation import make_valid

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw') + '/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')
CRS = 32610  # UTM 10N, meters
MI = 1609.344
CITIES = ['Seattle', 'Bellevue', 'Kirkland', 'Redmond', 'Issaquah', 'Sammamish', 'Mercer Island']

def gj(path):
    d = json.load(open(RAW + path))
    rows = []
    for f in d['features']:
        g = f['geometry']
        if g is None: continue
        geom = make_valid(shape(g))
        rows.append({**f['properties'], 'geometry': geom})
    return gpd.GeoDataFrame(rows, geometry='geometry', crs=4326)

# ---------------- city boundaries ----------------
places = gpd.read_file('zip://' + RAW + 'places.zip')
places = places[places.NAME.isin(CITIES)][['NAME', 'geometry']].to_crs(CRS)
city_geom = dict(zip(places.NAME, places.geometry))

# ---------------- neighborhoods ----------------
parts = []
sea = gj('nhoods.geojson'); sea['name'] = sea.S_HOOD; sea['district'] = sea.L_HOOD; sea['city'] = 'Seattle'
parts.append(sea[['name', 'district', 'city', 'geometry']])
for f, col, city in [('bel_nh.geojson', 'Neighborhood', 'Bellevue'), ('kir_nh.geojson', 'Neighborhood', 'Kirkland'),
                     ('red_nh.geojson', 'NAME', 'Redmond'), ('iss_nh.geojson', 'Name', 'Issaquah')]:
    g = gj(f); g['name'] = g[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    if city == 'Issaquah': g['name'] = g.name.str.title()
    g['district'] = None; g['city'] = city
    parts.append(g[['name', 'district', 'city', 'geometry']])
nh = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=4326).to_crs(CRS)
nh = nh.dissolve(by=['city', 'name'], as_index=False, aggfunc={'district': 'first'})

# Sammamish has no published neighborhood map: group its census tracts around well-known area names.
tracts = gpd.read_file('zip://' + RAW + 'tracts.zip')
tracts = tracts[tracts.COUNTYFP == '033'][['GEOID', 'geometry']].to_crs(CRS)
def tract_areas(city, anchors):
    anc = gpd.GeoSeries([Point(v) for v in anchors.values()], crs=4326).to_crs(CRS)
    t_s = gpd.overlay(tracts, gpd.GeoDataFrame(geometry=[city_geom[city]], crs=CRS), how='intersection')
    t_s = t_s[t_s.area > 50_000]
    t_s['name'] = [list(anchors)[int(np.argmin([g.representative_point().distance(a) for a in anc]))] for g in t_s.geometry]
    ts = t_s.dissolve(by='name', as_index=False)[['name', 'geometry']]
    ts['city'] = city; ts['district'] = None; ts['approx'] = True
    return ts
samm_ts = tract_areas('Sammamish', {  # approximate area centers (lon, lat)
    'Inglewood / North Sammamish': (-122.060, 47.640), 'Sahalee / Northeast': (-122.020, 47.640),
    'Lake Sammamish Shore (West)': (-122.070, 47.600), 'Pine Lake / Town Center': (-122.040, 47.590),
    'Beaver Lake / East': (-121.995, 47.595), 'Klahanie / Southeast': (-122.005, 47.565),
})
# Mercer Island: one area per census tract, named by position on the island.
mi_ts = tract_areas('Mercer Island', {
    'North End (West)': (-122.253, 47.591), 'North End (Central)': (-122.234, 47.583),
    'North End (East)': (-122.216, 47.581), 'Town Center / Mid-Island': (-122.221, 47.567),
    'Mid-Island South': (-122.222, 47.550), 'South End': (-122.232, 47.529),
})
nh['approx'] = False
nh = gpd.GeoDataFrame(pd.concat([nh, samm_ts, mi_ts], ignore_index=True), crs=CRS)
# Clip to city limits so annexation leftovers / water don't count.
nh['geometry'] = [g.intersection(city_geom[c].buffer(30)) for g, c in zip(nh.geometry, nh.city)]
nh = nh[nh.area > 100_000].reset_index(drop=True)

# ---------------- population base: EPA block groups (pop + jobs + walkability) ----------------
bg = gpd.read_file('zip://' + RAW + 'bg.zip')
bg = bg[bg.COUNTYFP == '033'][['GEOID', 'geometry']].to_crs(CRS)
walk = pd.DataFrame([f['properties'] for f in json.load(open(RAW + 'walk.json'))['features']])
walk['GEOID'] = walk.GEOID20.astype(str)
bg = bg.merge(walk[['GEOID', 'NatWalkInd']], on='GEOID', how='left')
bgp = pd.read_csv(RAW + 'acs_bg_b01003.dat', sep='|', dtype=str)
bgp['GEOID'] = bgp.GEO_ID.str[-12:]
bg = bg.merge(bgp[['GEOID']].assign(TotPop=pd.to_numeric(bgp.B01003_E001)), on='GEOID', how='left')
print('BG pop missing', bg.TotPop.isna().sum(), 'walk missing', bg.NatWalkInd.isna().sum())
# jobs (for daytime population) from EPA table
bg['tract'] = bg.GEOID.str[:11]
bg['bg_area'] = bg.area

# overlay neighborhoods x block groups => population-weighted pieces
nh['nid'] = range(len(nh))
pieces = gpd.overlay(nh[['nid', 'geometry']], bg, how='intersection')
pieces['w'] = pieces.area / pieces.bg_area * pieces.TotPop.fillna(0)
pop = pieces.groupby('nid').w.sum()
nh['pop'] = nh.nid.map(pop).fillna(0).round()
print(nh[nh['pop'] < 1000][['city','name','pop']].to_string())
nh = nh[(nh['pop'] >= 600) & ~nh.name.str.contains('Open Space|State Park')].copy()
print('neighborhoods', len(nh), nh.groupby('city').size().to_dict())

def pw_mean(values_by_key, key='tract'):
    """Population-weighted mean over pieces of a per-tract (or per-bg) value."""
    p = pieces.copy(); p['v'] = p[key].map(values_by_key)
    p = p[p.v.notna() & (p.w > 0)]
    return p.groupby('nid').apply(lambda d: np.average(d.v, weights=d.w), include_groups=False)

wg = gj('walk_geo.geojson').to_crs(CRS)
wg['dens'] = wg.TotPop.fillna(0) / wg.area + 1e-6
wp = gpd.overlay(nh[['nid', 'geometry']], wg[['NatWalkInd', 'dens', 'geometry']], how='intersection')
wp['w'] = wp.area * wp.dens
nh['walk'] = nh.nid.map(wp[wp.NatWalkInd.notna()].groupby('nid').apply(lambda d: np.average(d.NatWalkInd, weights=d.w), include_groups=False))

# ---------------- ACS tract data ----------------
ACS_YEAR = open(RAW + 'acs_year').read().strip()
def acs(table):
    d = pd.read_csv(RAW + f'acs_{table}.dat', sep='|', dtype=str)
    d['tract'] = d.GEO_ID.str[-11:]
    return d.set_index('tract')
def num(s): return pd.to_numeric(s, errors='coerce').where(lambda x: x >= 0)
a = pd.DataFrame(index=acs('b01003').index)
a['income'] = num(acs('b19013').B19013_E001)
a['homevalue'] = num(acs('b25077').B25077_E001)
a['median_age'] = num(acs('b01002').B01002_E001)
e = acs('b15003'); tot = num(e.B15003_E001)
a['pct_bachelors'] = sum(num(e[f'B15003_E0{i}']) for i in (22, 23, 24, 25)) / tot * 100
a['pct_grad'] = sum(num(e[f'B15003_E0{i}']) for i in (23, 24, 25)) / tot * 100
h = acs('b11005'); a['pct_hh_kids'] = num(h.B11005_E002) / num(h.B11005_E001) * 100
t = acs('b25003'); a['pct_owner'] = num(t.B25003_E002) / num(t.B25003_E001) * 100
c = acs('b08301'); wk = num(c.B08301_E001)
a['pct_transit_commute'] = num(c.B08301_E010) / wk * 100
a['pct_wfh'] = num(c.B08301_E021) / wk * 100
for col in a.columns:
    nh[col] = nh.nid.map(pw_mean(a[col].dropna().to_dict()))

# ---------------- Zillow home values by ZIP ----------------
zcols = pd.read_csv(RAW + 'zhvi.csv', nrows=0).columns
latest = zcols[-1]
z = pd.read_csv(RAW + 'zhvi.csv', usecols=['RegionName', 'State', latest, zcols[-13]], dtype={'RegionName': str})
z = z[z.State == 'WA']; z['zip'] = z.RegionName.str.zfill(5)
zcta = gpd.read_file('zip://' + RAW + 'zcta.zip', bbox=(-122.5, 47.4, -121.8, 47.8)).to_crs(CRS)
zcta = zcta.rename(columns={'ZCTA5CE20': 'zip'})[['zip', 'geometry']]
zp = gpd.overlay(pieces[['nid', 'w', 'tract', 'geometry']].assign(pa=pieces.area), zcta, how='intersection')
zp['w2'] = zp.w * zp.area / zp.pa
# Within-ZIP adjustment: scale the ZIP's Zillow value by the tract's Census home value relative to the ZIP average.
zp['hv'] = zp.tract.map(a.homevalue)
zh = zp[zp.hv.notna() & (zp.w2 > 0)].groupby('zip').apply(lambda d: np.average(d.hv, weights=d.w2), include_groups=False)
zp['adj'] = (zp.hv / zp.zip.map(zh)).clip(0.65, 1.5).fillna(1.0)
zv = dict(zip(z.zip, z[latest])); zv_prev = dict(zip(z.zip, z[zcols[-13]]))
zp['v'] = zp.zip.map(zv) * zp.adj; zp['v0'] = zp.zip.map(zv_prev) * zp.adj
zp = zp[zp.v.notna() & (zp.w2 > 0)]
nh['price'] = nh.nid.map(zp.groupby('nid').apply(lambda d: np.average(d.v, weights=d.w2), include_groups=False))
nh['price_prev'] = nh.nid.map(zp.groupby('nid').apply(lambda d: np.average(d.v0, weights=d.w2), include_groups=False))
nh['zips'] = nh.nid.map(zp.groupby('nid').zip.apply(lambda s: sorted(set(s))))
nh['price'] = nh.price.fillna(nh.homevalue)
print('ZHVI month', latest)

# ---------------- Crime ----------------
fbi = json.load(open(RAW + 'fbi_city.json'))
FBI_YEAR = fbi.pop('_year', 2025)
CRIME_FROM = datetime.date.fromisoformat(open(RAW + 'crime_from').read().strip()) if os.path.exists(RAW + 'crime_from') else datetime.date(2025, 11, 1)
# EPA block-group jobs for daytime population
walk_full = json.load(open(RAW + 'walk.json'))
# (TotEmp not fetched in walk.json; fall back to residents only)
def city_point_rates(points, city):
    """Return weighted (3x violent + property) incidents per neighborhood, scaled to the city's FBI rate."""
    sub = nh[nh.city == city]
    j = gpd.sjoin(points, sub[['nid', 'geometry']], predicate='within')
    cnt = j.groupby(['nid', 'kind']).size().unstack(fill_value=0)
    v = cnt.get('violent', 0); p = cnt.get('property', 0)
    loc_rate = (3 * v + p).reindex(sub.nid).fillna(0) / sub.set_index('nid')['pop']
    city_loc = (3 * v + p).sum() / sub['pop'].sum()
    f = fbi[city]; city_fbi = (3 * f['violent-crime']['rate_per_100k'] + f['property-crime']['rate_per_100k']) / 100  # per 1000
    return (loc_rate / city_loc * city_fbi), cnt.reindex(sub.nid).fillna(0)

sc = pd.read_csv(RAW + 'sea_crime.csv', dtype=str)
sc = sc[~sc.latitude.isin(['REDACTED']) & sc.latitude.notna()]
sc['lat'] = pd.to_numeric(sc.latitude, errors='coerce'); sc['lon'] = pd.to_numeric(sc.longitude, errors='coerce')
sc = sc[(sc.lat > 47) & (sc.lon < -121)]
sc['kind'] = sc.nibrs_crime_against_category.map({'PERSON': 'violent', 'PROPERTY': 'property'})
sc = sc[sc.kind.notna()]
sea_pts = gpd.GeoDataFrame(sc[['kind']], geometry=gpd.points_from_xy(sc.lon, sc.lat), crs=4326).to_crs(CRS)

bc = gj('bel_crime.geojson') if False else None
bdat = json.load(open(RAW + 'bel_crime.geojson'))['features']
bdf = pd.DataFrame([f['properties'] for f in bdat])
PERSON = re.compile(r'ASSAULT|ROBBERY|HOMICIDE|RAPE|SEX|INTIMIDATION|KIDNAP|FONDLING|SODOMY', re.I)
PROP = re.compile(r'LARCENY|BURGLARY|VEHICLE THEFT|VANDALISM|ARSON|FRAUD|STOLEN|THEFT|EMBEZZ|COUNTERFEIT|EXTORTION', re.I)
bdf['kind'] = np.where(bdf.LEGEND.str.contains(PERSON, na=False), 'violent', np.where(bdf.LEGEND.str.contains(PROP, na=False), 'property', None))
bdf = bdf[bdf.kind.notna() & bdf.LATITUDE.notna()]
bel_pts = gpd.GeoDataFrame(bdf[['kind']], geometry=gpd.points_from_xy(bdf.LONGITUDE.astype(float), bdf.LATITUDE.astype(float)), crs=4326).to_crs(CRS)

nh['crime_index'] = np.nan; nh['crime_level'] = 'city'
for city, pts in [('Seattle', sea_pts), ('Bellevue', bel_pts)]:
    r, _ = city_point_rates(pts, city)
    m = nh.city == city
    nh.loc[m, 'crime_index'] = nh.loc[m, 'nid'].map(r).values
    nh.loc[m, 'crime_level'] = 'neighborhood'
for city in ['Kirkland', 'Redmond', 'Issaquah', 'Sammamish', 'Mercer Island']:
    f = fbi[city]
    nh.loc[nh.city == city, 'crime_index'] = (3 * f['violent-crime']['rate_per_100k'] + f['property-crime']['rate_per_100k']) / 100
city_crime = {c: {'violent_per_100k': fbi[c]['violent-crime']['rate_per_100k'], 'property_per_100k': fbi[c]['property-crime']['rate_per_100k']} for c in CITIES}

# ---------------- Transit (GTFS weekday departures) ----------------
def gtfs_departures(zpath):
    zf = zipfile.ZipFile(RAW + zpath)
    rd = lambda n, **k: pd.read_csv(zf.open(n), dtype=str, **k)
    stops = rd('stops.txt'); trips = rd('trips.txt', usecols=['trip_id', 'service_id', 'route_id'])
    routes = rd('routes.txt', usecols=['route_id', 'route_type'])
    names = zf.namelist()
    # choose a Wednesday inside the feed
    cal = rd('calendar.txt') if 'calendar.txt' in names else None
    cd = rd('calendar_dates.txt') if 'calendar_dates.txt' in names else None
    today = datetime.date.today()
    if cal is not None and len(cal):
        start = max(pd.to_datetime(cal.start_date).min().date(), today - datetime.timedelta(days=60))
        d = start + datetime.timedelta(days=(2 - start.weekday()) % 7)
        if d < today: d = today
    else:
        dates = pd.to_datetime(cd.date).dt.date; d = min(x for x in dates if x.weekday() == 2 and x >= today)
    ds = d.strftime('%Y%m%d'); active = set()
    if cal is not None:
        active = set(cal[(cal.wednesday == '1') & (cal.start_date <= ds) & (cal.end_date >= ds)].service_id)
    if cd is not None:
        x = cd[cd.date == ds]
        active |= set(x[x.exception_type == '1'].service_id); active -= set(x[x.exception_type == '2'].service_id)
    trips = trips[trips.service_id.isin(active)].merge(routes, on='route_id')
    st = rd('stop_times.txt', usecols=['trip_id', 'stop_id'])
    st = st[st.trip_id.isin(set(trips.trip_id))].merge(trips[['trip_id', 'route_type']], on='trip_id')
    dep = st.groupby('stop_id').size().rename('deps')
    rail = set(st[st.route_type.isin(['0', '1', '2'])].stop_id)
    s = stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']].copy()
    s = s.merge(dep, left_on='stop_id', right_index=True)
    s['rail'] = s.stop_id.isin(rail)
    print(zpath, 'service day', ds, 'stops', len(s), 'rail stops', s.rail.sum())
    return s
stops = pd.concat([gtfs_departures('metro.zip'), gtfs_departures('st.zip')])
# Exclude streetcar from "rail" label only if desired; Link/Sounder/streetcar all count as rail here.
stops_g = gpd.GeoDataFrame(stops, geometry=gpd.points_from_xy(stops.stop_lon.astype(float), stops.stop_lat.astype(float)), crs=4326).to_crs(CRS)
buf = nh[['nid', 'geometry']].copy(); buf['geometry'] = buf.buffer(400)
j = gpd.sjoin(stops_g, buf, predicate='within')
deps = j.groupby('nid').deps.sum()
nh['transit_deps_per_sqmi'] = nh.nid.map(deps).fillna(0) / (buf.set_index('nid').area / MI**2).reindex(nh.nid).values
rail_st = stops_g[stops_g.rail].copy()
rail_st['station'] = rail_st.stop_name.str.replace(r'\s*-\s*(Bay|Platform).*$', '', regex=True)
pts = nh.geometry.representative_point()
nh['rail_mi'] = [rail_st.distance(p).min() / MI for p in pts]
bus_st = stops_g[~stops_g.rail]
nh['bus_mi'] = [bus_st.distance(p).min() / MI for p in pts]
nh['bus_name'] = [bus_st.stop_name.iloc[int(np.argmin(bus_st.distance(p).values))] for p in pts]
nh['rail_name'] = [rail_st.station.iloc[int(np.argmin(rail_st.distance(p).values))] for p in pts]

# ---------------- Schools (OSPI proficiency at NCES locations) ----------------
cols = ['NCESSCH', 'LEAID', 'NAME', 'OPSTFIPS', 'STREET', 'CITY', 'STATE', 'ZIP', 'STFIP', 'CNTY', 'NMCNTY', 'LOCALE', 'LAT', 'LON']
nces = pd.read_csv(RAW + 'EDGE_GEOCODE_PUBLICSCH_2324/EDGE_GEOCODE_PUBLICSCH_2324.TXT', sep='|', header=None, dtype=str, encoding='latin-1')
nces = nces.iloc[:, :14]; nces.columns = cols
nces = nces[nces.CNTY == '53033']
def norm(s):
    s = s.lower().replace('&', 'and')
    s = re.sub(r'\b(school|elementary|elem|middle|high|senior|junior|jr|sr|k-8|k8|academy|international|the|of)\b', ' ', s)
    return re.sub(r'[^a-z0-9]+', '', s)
nces['key'] = nces.NAME.map(norm)
os_ = pd.read_csv(RAW + 'ospi.csv', dtype=str)
os_['tested'] = pd.to_numeric(os_.count_of_students_tested, errors='coerce')
os_['met'] = pd.to_numeric(os_.count_consistent_grade_level, errors='coerce')
os_ = os_[os_.testsubject.isin(['ELA', 'Math'])]
sch = os_.groupby(['districtcode', 'districtname', 'schoolcode', 'schoolname']).agg(tested=('tested', 'sum'), met=('met', 'sum')).reset_index()
sch = sch[sch.tested >= 60]
sch['prof'] = sch.met / sch.tested * 100
sch['key'] = sch.schoolname.map(norm)
# map OSPI district -> NCES LEAID using names that appear in exactly one district
uniq = sch.groupby('key').districtcode.nunique(); uniq = set(uniq[uniq == 1].index)
m = sch[sch.key.isin(uniq)].merge(nces[['key', 'LEAID']], on='key')
d2l = m.groupby('districtcode').LEAID.agg(lambda s: s.value_counts().index[0]).to_dict()
sch['LEAID'] = sch.districtcode.map(d2l)
sch = sch.merge(nces[['key', 'LEAID', 'LAT', 'LON', 'NAME']], on=['key', 'LEAID'], how='inner').drop_duplicates(['districtcode', 'schoolcode'])
print('schools matched', len(sch), 'of', len(os_.groupby(['districtcode', 'schoolcode'])))
sg = gpd.GeoDataFrame(sch, geometry=gpd.points_from_xy(sch.LON.astype(float), sch.LAT.astype(float)), crs=4326).to_crs(CRS)
# Level-specific scores: grades 3-5 elementary, 6-8 middle, 10-11 high school
og = pd.read_csv(RAW + 'ospi_grades.csv', dtype=str)
og = og[og.testsubject.isin(['ELA', 'Math'])]
og['g'] = og.gradelevel.astype(int)
og['level'] = np.select([og.g <= 5, og.g <= 8], ['elem', 'mid'], 'high')
og['tested'] = pd.to_numeric(og.count_of_students_tested, errors='coerce')
og['met'] = pd.to_numeric(og.count_consistent_grade_level, errors='coerce')
lv = og.groupby(['districtcode', 'schoolcode', 'level']).agg(tested=('tested', 'sum'), met=('met', 'sum')).reset_index()
lv = lv[lv.tested >= 20]; lv['lprof'] = lv.met / lv.tested * 100
lv = lv.merge(sch[['districtcode', 'schoolcode', 'schoolname', 'districtname', 'LAT', 'LON']], on=['districtcode', 'schoolcode'])
print('school-levels', lv.level.value_counts().to_dict())
LEVELS = {}
for L in ['elem', 'mid', 'high']:
    x = lv[lv.level == L].reset_index(drop=True)
    LEVELS[L] = gpd.GeoDataFrame(x, geometry=gpd.points_from_xy(x.LON.astype(float), x.LAT.astype(float)), crs=4326).to_crs(CRS)
sch_info = []; level_q = {L: [] for L in LEVELS}
for p in pts:
    info = {}
    for L, g in LEVELS.items():
        d = g.distance(p).values / MI; idx = np.argsort(d)
        near = [i for i in idx if d[i] <= 2.0][:6]
        if len(near) < 2: near = list(idx[:2])
        w = g.tested.values[near] / (0.3 + d[near])
        q = float(np.average(g.lprof.values[near], weights=w)); level_q[L].append(q)
        i0 = idx[0]
        info[L] = {'name': g.schoolname.iloc[i0], 'district': g.districtname.iloc[i0].replace(' School District', ''),
                   'prof': round(float(g.lprof.iloc[i0])), 'mi': round(float(d[i0]), 1), 'q': round(q),
                   'others': [{'name': g.schoolname.iloc[i], 'prof': round(float(g.lprof.iloc[i])), 'mi': round(float(d[i]), 1)} for i in idx[1:3]]}
    sch_info.append(info)
for L in LEVELS: nh[L + '_q'] = level_q[L]
nh['school_prof'] = nh[['elem_q', 'mid_q', 'high_q']].mean(axis=1)
nh['sch'] = sch_info
for L in LEVELS: nh[L + '_mi'] = [i[L]['mi'] for i in sch_info]
# Colleges and universities (King County points of interest)
col = gj('colleges.geojson').to_crs(CRS)
col = col[~col.NAME.str.contains('Academy of Languages|Muckleshoot', na=False)]
col['NAME'] = col.NAME.str.replace('University of Washington-HUB', 'University of Washington', regex=False)
nh['college_mi'] = [col.distance(p).min() / MI for p in pts]
nh['college_name'] = [col.NAME.iloc[int(np.argmin(col.distance(p).values))] for p in pts]

# ---------------- Everyday amenities (OpenStreetMap + King County shopping centers) ----------------
osm = json.load(open(RAW + 'osm_poi.json'))['elements']
rows = []
for e in osm:
    tg = e.get('tags', {}); lat = e.get('lat') or (e.get('center') or {}).get('lat'); lon = e.get('lon') or (e.get('center') or {}).get('lon')
    if lat is None: continue
    if tg.get('shop') in ('supermarket', 'grocery'): kind = 'grocery'
    elif tg.get('amenity') == 'restaurant': kind = 'rest'
    elif tg.get('amenity') == 'pharmacy' or tg.get('healthcare') == 'pharmacy' or tg.get('shop') == 'chemist': kind = 'pharm'
    elif tg.get('shop') in ('mall', 'department_store'): kind = 'retail'
    else: continue
    rows.append({'kind': kind, 'name': tg.get('name') or tg.get('brand') or {'grocery': 'Grocery store', 'rest': 'Restaurant', 'pharm': 'Pharmacy', 'retail': 'Store'}[kind], 'lat': lat, 'lon': lon})
for f in json.load(open(RAW + 'shopping.geojson'))['features']:
    if f['geometry']: rows.append({'kind': 'retail', 'name': f['properties']['NAME'].strip(), 'lat': f['geometry']['coordinates'][1], 'lon': f['geometry']['coordinates'][0]})
am = pd.DataFrame(rows)
am = gpd.GeoDataFrame(am, geometry=gpd.points_from_xy(am.lon, am.lat), crs=4326).to_crs(CRS)
print('amenities', am.kind.value_counts().to_dict())
for k in ['retail', 'rest', 'grocery', 'pharm']:
    g = am[am.kind == k].reset_index(drop=True)
    dists = [g.distance(p).values / MI for p in pts]
    nh[k + '_mi'] = [float(d.min()) for d in dists]
    nh[k + '_name'] = [g.name.iloc[int(np.argmin(d))] for d in dists]
    nh[k + '_1mi'] = [int((d <= 1).sum()) for d in dists]

# ---------------- Parks, green space, trails, libraries ----------------
import os
from shapely.geometry import Polygon, LineString
from shapely.ops import polygonize, unary_union
def osm_elems(f):
    p = RAW + f
    if not os.path.exists(p) or os.path.getsize(p) < 1000: return []
    try: return json.load(open(p)).get('elements', [])
    except Exception: return []
parks = []
for e in osm_elems('osm_parks_w.json') + osm_elems('osm_parks_r.json'):
    tg = e.get('tags', {}); name = tg.get('name')
    try:
        if e['type'] == 'way':
            c = [(n['lon'], n['lat']) for n in e.get('geometry', [])]
            if len(c) < 4 or c[0] != c[-1]: continue
            g = Polygon(c)
        else:
            lines = [LineString([(n['lon'], n['lat']) for n in m['geometry']]) for m in e.get('members', []) if m.get('role') in ('outer', '') and m.get('geometry')]
            polys = list(polygonize(unary_union(lines)))
            if not polys: continue
            g = unary_union(polys)
        if not g.is_valid: g = g.buffer(0)
        parks.append({'name': name or 'Small unnamed park', 'kind': tg.get('leisure'), 'geometry': g})
    except Exception: pass
# King County's parks layer (all agencies) is the main source; OpenStreetMap parks fill gaps
for f in json.load(open(RAW + 'kc_parks.geojson'))['features']:
    if f['geometry']:
        g = make_valid(shape(f['geometry']))
        parks.insert(0, {'name': (f['properties'].get('SITENAME') or 'Park').strip(), 'kind': 'kc', 'geometry': g})
pk = gpd.GeoDataFrame(parks, geometry='geometry', crs=4326).to_crs(CRS)
pk['acres'] = pk.area / 4046.86
pk = pk[pk.acres >= 0.25]
green = pk[pk.acres >= 25]
print('parks', len(pk), 'green spaces (25+ acres)', len(green))
def nearest(gdf, label='name'):
    out_d, out_n = [], []
    sidx = gdf.sindex
    for p in pts:
        d = gdf.distance(p).values; i = int(np.argmin(d))
        out_d.append(float(d[i]) / MI); out_n.append(gdf[label].iloc[i])
    return out_d, out_n
nh['park_mi'], nh['park_name'] = nearest(pk)
nh['green_mi'], nh['green_name'] = nearest(green)
# acres of park land within 1 mile of the neighborhood center
pk_union = pk.geometry.union_all() if hasattr(pk.geometry, 'union_all') else pk.geometry.unary_union
nh['park_acres_1mi'] = [p.buffer(MI).intersection(pk_union).area / 4046.86 for p in pts]
tr = []
for f in json.load(open(RAW + 'kc_trails.geojson'))['features']:
    pr = f['properties']
    if not f['geometry'] or pr.get('Surf_Type') in ('On Street Trail', 'Under Construction'): continue
    for path in f['geometry']['coordinates']:
        if len(path) >= 2: tr.append({'name': (pr.get('Trail_Name') or pr.get('SiteName') or 'Trail').strip(), 'geometry': LineString(path)})
for e in osm_elems('osm_trails.json'):
    c = [(n['lon'], n['lat']) for n in e.get('geometry', [])]
    if len(c) >= 2: tr.append({'name': e.get('tags', {}).get('name', 'Trail'), 'geometry': LineString(c)})
if tr:
    trg = gpd.GeoDataFrame(tr, geometry='geometry', crs=4326).to_crs(CRS)
    nh['trail_mi'], nh['trail_name'] = nearest(trg)
    print('trail segments', len(trg))
else:
    nh['trail_mi'], nh['trail_name'] = np.nan, None
lib = gj('libraries.geojson').to_crs(CRS)
lib['NAME'] = lib.NAME.str.strip()
nh['lib_mi'], nh['lib_name'] = nearest(lib, 'NAME')

# ---------------- Fitness & wellness (OpenStreetMap) and golf (King County) ----------------
fit = []
for e in osm_elems('osm_fitness.json'):
    tg = e.get('tags', {}); lat = e.get('lat') or (e.get('center') or {}).get('lat'); lon = e.get('lon') or (e.get('center') or {}).get('lon')
    if lat is None: continue
    sp = tg.get('sport', '')
    if 'yoga' in sp or 'pilates' in sp: kind = 'yoga'
    elif tg.get('leisure') == 'spa' or tg.get('amenity') == 'spa' or 'spa' in tg.get('beauty', '') or tg.get('shop') == 'massage': kind = 'spa'
    else: kind = 'gym'
    fit.append({'kind': kind, 'name': tg.get('name') or tg.get('brand') or {'gym': 'Gym', 'spa': 'Spa', 'yoga': 'Yoga studio'}[kind], 'lat': lat, 'lon': lon})
fg = pd.DataFrame(fit); fg = gpd.GeoDataFrame(fg, geometry=gpd.points_from_xy(fg.lon, fg.lat), crs=4326).to_crs(CRS)
print('fitness', fg.kind.value_counts().to_dict())
for k in ['gym', 'spa', 'yoga']:
    g = fg[fg.kind == k].reset_index(drop=True)
    nh[k + '_mi'], nh[k + '_name'] = nearest(g)
nh['fit_1mi'] = [int((fg.distance(p) <= MI).sum()) for p in pts]
golf_rows = [{'name': f['properties']['NAME'].strip(), 'geometry': shape(f['geometry'])} for f in json.load(open(RAW + 'golf_kc.geojson'))['features'] if f['geometry']]
for f in json.load(open(RAW + 'kc_parks.geojson'))['features']:
    nm = f['properties'].get('SITENAME') or ''
    if 'golf' in nm.lower() and 'open space' not in nm.lower() and f['geometry']: golf_rows.append({'name': nm.strip(), 'geometry': make_valid(shape(f['geometry']))})
golf = gpd.GeoDataFrame(golf_rows, geometry='geometry', crs=4326).to_crs(CRS)
nh['golf_mi'], nh['golf_name'] = nearest(golf)
print('golf features', len(golf))

# ---------------- Health care ----------------
med = gj('clinics.geojson').to_crs(CRS)
HOSP = re.compile(r'Hospital|Harborview Medical Center$|UW Medical Center - (Montlake|Northwest)|Virginia Mason Medical Center|EvergreenHealth Medical Center|Swedish Hospital', re.I)
NOT_HOSP = re.compile(r'Fairfax|Kindred|Central Hospital|Clinic', re.I)
med['NAME'] = med.NAME.str.strip()
med['is_hosp'] = med.NAME.str.contains(HOSP) & ~med.NAME.str.contains(NOT_HOSP)
hosp = med[med.is_hosp].drop_duplicates('NAME'); clin = med[~med.is_hosp]
print('hospitals', len(hosp), sorted(hosp.NAME))
nh['hosp_mi'] = [hosp.distance(p).min() / MI for p in pts]
nh['hosp_name'] = [hosp.NAME.iloc[int(np.argmin(hosp.distance(p).values))] for p in pts]
nh['clinics_2mi'] = [int((clin.distance(p) <= 2 * MI).sum()) for p in pts]
nh['clinic_mi'] = [clin.distance(p).min() / MI for p in pts]

# ---------------- Market activity ----------------
# Recorded sales (King County Assessor), last 12 months, located by parcel.
ks = pd.read_csv(RAW + 'kc_sales_geo.csv', parse_dates=['date'])
kg = gpd.GeoDataFrame(ks, geometry=gpd.points_from_xy(ks.lon, ks.lat), crs=4326).to_crs(CRS)
kg = gpd.sjoin(kg, zcta, predicate='within').drop(columns='index_right')
kj = gpd.sjoin(kg, nh[['nid', 'geometry']], predicate='within')
grp = kj.groupby('nid')
nh['sold_12m'] = nh.nid.map(grp.size()).fillna(0).astype(int)
nh['sold_condo_12m'] = nh.nid.map(kj[kj.PrincipalUse == 2].groupby('nid').size()).fillna(0).astype(int)
nh['sold_3m'] = nh.nid.map(kj[kj.date >= kj.date.max() - pd.Timedelta(days=91)].groupby('nid').size()).fillna(0).astype(int)
nh['median_sale'] = nh.nid.map(grp.price.median())
nh['sales_k'] = nh.nid.map(grp.price.apply(lambda v: sorted(int(round(x/1000)) for x in v)))
SALES_WINDOW = f"{kj.date.min():%b %Y} – {kj.date.max():%b %Y}"
# Zillow ZIP-level listings, apportioned to neighborhoods by each neighborhood's share of the ZIP's recorded sales
def zlatest(fname):
    d = pd.read_csv(RAW + fname, dtype={'RegionName': str}); d['zip'] = d.RegionName.str.zfill(5)
    d = d[d.State == 'WA']; col = d.columns[-2] if d.columns[-1] == 'zip' else d.columns[-1]
    return dict(zip(d.zip, d[col])), col
inv, MKT_MONTH = zlatest('z_Zip_invt_fs_uc_sfrcondo_sm_month.csv')
newl, _ = zlatest('z_Zip_new_listings_uc_sfrcondo_sm_month.csv')
dom, _ = zlatest('z_Zip_med_doz_pending_uc_sfrcondo_sm_month.csv')
cd = pd.read_csv(RAW + 'z_City_med_doz_pending_uc_sfrcondo_sm_month.csv'); cd = cd[(cd.State == 'WA') & (cd.CountyName == 'King County')]
city_dom = dict(zip(cd.RegionName, cd[cd.columns[-1]]))
zip_sales = kg.groupby('zip').size()
nz = kj.groupby(['nid', 'zip']).size().rename('n').reset_index()
nz['share'] = nz.n / nz.zip.map(zip_sales)
def apportion(vals):
    x = nz.assign(v=nz.zip.map(vals) * nz.share).dropna(subset=['v'])
    return x.groupby('nid').v.sum()
nh['for_sale'] = nh.nid.map(apportion(inv)).round()
nh['new_listings'] = nh.nid.map(apportion(newl)).round()
dz = nz.assign(v=nz.zip.map(dom)).dropna(subset=['v'])
dom_n = dz.groupby('nid').apply(lambda d: np.average(d.v, weights=d.n), include_groups=False)
nh['dom'] = nh.nid.map(dom_n)
nh['dom_level'] = np.where(nh.dom.notna(), 'zip', 'city')
nh['dom'] = nh.dom.fillna(nh.city.map(city_dom))
print('market: month', MKT_MONTH, 'sales window', SALES_WINDOW, 'dom missing', nh.dom.isna().sum())

print('dropping (almost no owner-occupied homes):', nh[nh.pct_owner < 3][['city','name','pct_owner']].values.tolist())
nh = nh[~(nh.pct_owner < 3)].copy()
# ---------------- Nearest-place coordinates for map markers ----------------
from shapely.ops import nearest_points
def near_xy(gdf, label, p):
    d = gdf.distance(p).values; i = int(np.argmin(d)); g = gdf.geometry.iloc[i]
    q = g if g.geom_type == 'Point' else nearest_points(p, g)[1]
    q4 = gpd.GeoSeries([q], crs=CRS).to_crs(4326).iloc[0]
    return [round(q4.y, 5), round(q4.x, 5), str(gdf[label].iloc[i])]
POI_SETS = {'elem': (LEVELS['elem'], 'schoolname'), 'mid': (LEVELS['mid'], 'schoolname'), 'high': (LEVELS['high'], 'schoolname'),
            'college': (col, 'NAME'), 'grocery': (am[am.kind == 'grocery'], 'name'), 'pharm': (am[am.kind == 'pharm'], 'name'),
            'park': (pk, 'name'), 'trail': (trg, 'name'), 'lib': (lib, 'NAME'), 'rail': (rail_st, 'station'), 'hosp': (hosp, 'NAME'),
            'gym': (fg[fg.kind == 'gym'], 'name'), 'golf': (golf, 'name')}
pois_all = {nid: {} for nid in nh.nid}
for key, (g, lab) in POI_SETS.items():
    g = g.reset_index(drop=True)
    for nid, p in zip(nh.nid, nh.geometry.representative_point()):
        pois_all[nid][key] = near_xy(g, lab, p)
nh['pois'] = nh.nid.map(pois_all)

# ---------------- Background map: water and highways (Census TIGER) ----------------
BBOX = (-122.46, 47.47, -121.92, 47.80)
from shapely.geometry import box
clipbox = box(*BBOX)
wt = gpd.read_file('zip://' + RAW + 'water.zip').to_crs(CRS)
wt = wt[wt.area >= 250_000].to_crs(4326)
wt['geometry'] = wt.geometry.intersection(clipbox).simplify(0.0004, preserve_topology=True)
wt = wt[~wt.geometry.is_empty]
rd = gpd.read_file('zip://' + RAW + 'prisec.zip', bbox=BBOX)
rd['geometry'] = rd.geometry.intersection(clipbox).simplify(0.0004)
rd = rd[~rd.geometry.is_empty]
print('basemap water', len(wt), 'roads', len(rd))

# ---------------- Scores (0-100 percentile across all neighborhoods) ----------------
def pct(s, higher_better=True):
    r = s.rank(pct=True, method='average')
    r = r if higher_better else 1 - r + 1 / len(s)
    return (r * 100).round().clip(0, 100)
nh['s_schools'] = pct(nh.school_prof)
nh['s_walk'] = pct(nh.walk)
nh['s_safety'] = pct(nh.crime_index, False)
nh['s_transit'] = pct(np.log1p(nh.transit_deps_per_sqmi) + np.clip(1.5 - nh.rail_mi, 0, 1.5))
nh['s_afford'] = pct(nh.price, False)
nh['s_income'] = pct(nh.income)
nh['s_health'] = pct(-(nh.hosp_mi + 0.5 * nh.clinic_mi) + 0.05 * nh.clinics_2mi)
# Errands & dining: closeness to the nearest grocery, pharmacy, restaurant and shopping, plus how many groceries/restaurants are within 1 mile
parts = [pct(nh.park_mi, False), pct(nh.green_mi, False), pct(nh.park_acres_1mi)] + ([pct(nh.trail_mi, False)] if nh.trail_mi.notna().any() else [])
nh['s_parks'] = pct(sum(parts))
nh['s_library'] = pct(nh.lib_mi, False)
nh['s_fitness'] = pct(pct(nh.gym_mi, False) + pct(nh.spa_mi, False) + pct(nh.yoga_mi, False) + 0.5 * pct(nh.fit_1mi))
nh['s_golf'] = pct(nh.golf_mi, False)
nh['s_errands'] = pct(sum(pct(nh[k + '_mi'], False) for k in ['grocery', 'pharm', 'rest', 'retail'])
                      + 0.5 * pct(nh.grocery_1mi) + 0.5 * pct(nh.rest_1mi))

# ---------------- Export ----------------
out_g = nh.to_crs(4326).copy()
out_g['geometry'] = out_g.geometry.simplify(0.00015, preserve_topology=True)
def rnd(geom):
    from shapely.geometry import mapping
    m = mapping(geom)
    def r(c):
        if isinstance(c[0], (float, int)): return [round(c[0], 5), round(c[1], 5)]
        return [r(x) for x in c]
    if m['type'] == 'GeometryCollection':
        polys = [g for g in geom.geoms if g.geom_type in ('Polygon', 'MultiPolygon')]
        from shapely.ops import unary_union
        m = mapping(unary_union(polys))
    return {'type': m['type'], 'coordinates': r(m['coordinates'])}
def rndl(geom):
    from shapely.geometry import mapping
    m = mapping(geom)
    def r(c):
        if isinstance(c[0], (float, int)): return [round(c[0], 4), round(c[1], 4)]
        return [r(x) for x in c]
    return {'type': m['type'], 'coordinates': r(m['coordinates'])}
def f(x, n=1):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)
feats = []
for _, r in out_g.sort_values(['city', 'name']).iterrows():
    c = r.geometry.representative_point()
    feats.append({'type': 'Feature', 'geometry': rnd(r.geometry), 'properties': {
        'id': int(r.nid), 'name': r['name'], 'district': r.district if isinstance(r.district, str) else None, 'city': r.city,
        'approx': bool(r.approx), 'center': [round(c.x, 5), round(c.y, 5)], 'pop': int(r['pop']),
        'price': f(r.price, -3), 'price_prev': f(r.price_prev, -3), 'zips': r.zips if isinstance(r.zips, list) else [],
        'income': f(r.income, -2), 'walk': f(r.walk, 1), 'crime_index': f(r.crime_index, 1), 'crime_level': r.crime_level,
        'transit_deps': f(r.transit_deps_per_sqmi, 0), 'rail_mi': f(r.rail_mi, 1), 'rail_name': r.rail_name,
        'school_prof': f(r.school_prof, 0), 'sch': r.sch, 'elem_mi': f(r.elem_mi, 1), 'mid_mi': f(r.mid_mi, 1), 'high_mi': f(r.high_mi, 1),
        'elem_q': f(r.elem_q, 0), 'mid_q': f(r.mid_q, 0), 'high_q': f(r.high_q, 0), 'college_mi': f(r.college_mi, 1), 'college_name': r.college_name,
        **{k + '_mi': f(r[k + '_mi'], 1) for k in ['retail', 'rest', 'grocery', 'pharm']}, **{k + '_name': r[k + '_name'] for k in ['retail', 'rest', 'grocery', 'pharm']},
        **{k + '_1mi': int(r[k + '_1mi']) for k in ['retail', 'rest', 'grocery', 'pharm']}, 'hosp_mi': f(r.hosp_mi, 1), 'hosp_name': r.hosp_name,
        'clinics_2mi': int(r.clinics_2mi), 'median_age': f(r.median_age, 1), 'pct_bachelors': f(r.pct_bachelors, 0), 'pct_grad': f(r.pct_grad, 0), 'bus_mi': f(r.bus_mi, 2), 'bus_name': r.bus_name,
        'park_mi': f(r.park_mi, 1), 'park_name': r.park_name, 'green_mi': f(r.green_mi, 1), 'green_name': r.green_name, 'park_acres_1mi': f(r.park_acres_1mi, 0),
        'trail_mi': f(r.trail_mi, 1), 'trail_name': r.trail_name if isinstance(r.trail_name, str) else None, 'lib_mi': f(r.lib_mi, 1), 'lib_name': r.lib_name,
        'gym_mi': f(r.gym_mi, 1), 'gym_name': r.gym_name, 'spa_mi': f(r.spa_mi, 1), 'spa_name': r.spa_name, 'yoga_mi': f(r.yoga_mi, 1), 'yoga_name': r.yoga_name,
        'fit_1mi': int(r.fit_1mi), 'golf_mi': f(r.golf_mi, 1), 'golf_name': r.golf_name,
        'pct_hh_kids': f(r.pct_hh_kids, 0), 'pct_owner': f(r.pct_owner, 0), 'pct_transit_commute': f(r.pct_transit_commute, 0),
        'pct_wfh': f(r.pct_wfh, 0),
        'sold_12m': int(r.sold_12m), 'sold_condo_12m': int(r.sold_condo_12m), 'sold_3m': int(r.sold_3m), 'median_sale': f(r.median_sale, -3),
        'sales_k': r.sales_k if isinstance(r.sales_k, list) else [], 'for_sale': f(r.for_sale, 0), 'new_listings': f(r.new_listings, 0), 'dom': f(r.dom, 0), 'dom_level': r.dom_level,
        'pois': r.pois,
        'scores': {k: int(r['s_' + k]) for k in ['schools', 'walk', 'safety', 'transit', 'afford', 'income', 'health', 'errands', 'parks', 'library', 'fitness', 'golf']},
    }})
cities_g = gpd.GeoSeries(list(city_geom.values()), crs=CRS).to_crs(4326).simplify(0.0003)
out = {
    'generated': datetime.date.today().isoformat(),
    'neighborhoods': {'type': 'FeatureCollection', 'features': feats},
    'cities': [{'name': n, 'geometry': rnd(g)} for n, g in zip(city_geom, cities_g)],
    'basemap': {'water': [{'name': re.sub(r'\bLk\b', 'Lake', re.sub(r'\bRiv\b', 'River', n)) if isinstance(n, str) else '', 'geometry': rnd(g)} for n, g in zip(wt.FULLNAME, wt.geometry) if g.geom_type in ('Polygon', 'MultiPolygon')],
                'roads': [{'name': n if isinstance(n, str) else '', 'kind': 'primary' if m == 'S1100' else 'secondary', 'geometry': rndl(g)} for n, m, g in zip(rd.FULLNAME, rd.MTFCC, rd.geometry) if g.geom_type in ('LineString', 'MultiLineString')]},
    'hospitals': [{'name': r.NAME, 'lonlat': [round(p.x, 5), round(p.y, 5)]} for r, p in zip(hosp.itertuples(), hosp.to_crs(4326).geometry)],
    'city_crime': city_crime,
    'meta': {'acs_year': f'{int(ACS_YEAR)-4}-{ACS_YEAR}', 'zhvi_month': latest[:7], 'crime_window': f'{CRIME_FROM:%b %Y} – {datetime.date.today():%b %Y} (Seattle, Bellevue points); calendar {FBI_YEAR} (FBI city rates)', 'fbi_year': FBI_YEAR, 'crime_range': f'{CRIME_FROM:%b %Y} – {datetime.date.today():%b %Y}',
             'ospi_year': '2024-25', 'market_month': MKT_MONTH[:7], 'sales_window': SALES_WINDOW, 'osm_date': f'{datetime.date.today():%b %Y}'},
}
import os; os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print('wrote', OUT, os.path.getsize(OUT) // 1024, 'KB')
print(nh[['city', 'name', 'pop', 'price', 'income', 'walk', 'crime_index', 'school_prof', 'hosp_mi', 'rail_mi']].sort_values('price').to_string(max_rows=40))
