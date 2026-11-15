"""Second half of the downloads: paged ArcGIS layers, FBI crime rates, OpenStreetMap amenities, and locating recorded sales."""
import datetime, json, os, sys, time, urllib.request, urllib.parse, zipfile
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcfetch
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw') + '/'
L = arcfetch.fetch
_t = datetime.date.today()
CRIME_FROM = os.environ.get('CRIME_FROM') or _t.replace(year=_t.year - 1, day=1).isoformat()
L('https://services1.arcgis.com/EYzEZbDhXZjURPbP/arcgis/rest/services/Neighborhood_Areas/FeatureServer/3', out=RAW + 'bel_nh.geojson')
L('https://maps.redmond.gov/server/rest/services/Web/RedmondDataForArcGISOnline/MapServer/11', out=RAW + 'red_nh.geojson')
L('https://apps.issaquahwa.gov/server/rest/services/SingleLayers/Neighborhoods/FeatureServer/1', out=RAW + 'iss_nh.geojson')
L('https://services3.arcgis.com/q5Jezm9AgzqyE7Q6/arcgis/rest/services/Kirkland_Capacity_Summarized_by_Neighborhood/FeatureServer/0', out=RAW + 'kir_nh.geojson')
L('https://services1.arcgis.com/EYzEZbDhXZjURPbP/arcgis/rest/services/Offenses/FeatureServer/1', f"REPORT_DATE >= DATE '{CRIME_FROM}'", out=RAW + 'bel_crime.geojson')
L('https://geodata.epa.gov/arcgis/rest/services/OA/WalkabilityIndex/MapServer/0', "STATEFP='53' AND COUNTYFP='033'", fields='GEOID20,GEOID10,NatWalkInd,TotPop', out=RAW + 'walk.json', geom=False)
L('https://geodata.epa.gov/arcgis/rest/services/OA/WalkabilityIndex/MapServer/0', "STATEFP='53' AND COUNTYFP='033'", fields='GEOID10,NatWalkInd,TotPop,Ac_Land', out=RAW + 'walk_geo.geojson')
L('https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/PARK_AREA_228/FeatureServer/0', out=RAW + 'kc_parks.geojson')
L('https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/Trails_in_King_County/FeatureServer/29', out=RAW + 'kc_trails.geojson')

# FBI Crime Data Explorer: latest full calendar year of violent and property crime rates per city
# (the FBI publishes a year's data the following fall, so try last year first and fall back a year).
# DEMO_KEY is rate-limited; set FBI_API_KEY to your own free api.data.gov key if you have one.
oris = {'Seattle': 'WASPD0000', 'Bellevue': 'WA0170200', 'Kirkland': 'WA0170800', 'Redmond': 'WA0171200', 'Issaquah': 'WA0170600', 'Sammamish': 'WA0175000', 'Mercer Island': 'WA0170900'}
key = os.environ.get('FBI_API_KEY') or 'DEMO_KEY'


def fbi_year(y):
    out = {}
    for city, ori in oris.items():
        out[city] = {}
        for off in ['violent-crime', 'property-crime']:
            d = json.load(urllib.request.urlopen(f"https://api.usa.gov/crime/fbi/cde/summarized/agency/{ori}/{off}?from=01-{y}&to=12-{y}&API_KEY={key}", timeout=60))
            r = [v for k, v in d['offenses']['rates'].items() if k.endswith('Offenses') and not k.startswith(('Washington', 'United'))]
            if not r or len(r[0]) < 12: raise ValueError(f'{city} {y}: incomplete year')
            out[city][off] = {'rate_per_100k': round(sum(r[0].values()), 1), 'months': len(r[0])}
            time.sleep(1)
    return out


for y in (_t.year - 1, _t.year - 2):
    try:
        out = fbi_year(y); out['_year'] = y; break
    except Exception as e:
        print('FBI', y, 'not complete yet:', e)
json.dump(out, open(RAW + 'fbi_city.json', 'w'), indent=1)

# OpenStreetMap: groceries, restaurants, pharmacies, malls (Overpass API; retry if the server is busy)
Q = '[out:json][timeout:180];(nwr["shop"~"^(supermarket|grocery)$"](47.48,-122.45,47.79,-121.93);nwr["amenity"="restaurant"](47.48,-122.45,47.79,-121.93);nwr["amenity"="pharmacy"](47.48,-122.45,47.79,-121.93);nwr["healthcare"="pharmacy"](47.48,-122.45,47.79,-121.93);nwr["shop"~"^(mall|department_store)$"](47.48,-122.45,47.79,-121.93););out center tags;'
B = '47.47,-122.46,47.80,-121.92'
QF = f'[out:json][timeout:180];(nwr["leisure"="fitness_centre"]({B});nwr["sport"~"yoga|pilates"]({B});nwr["leisure"="spa"]({B});nwr["amenity"="spa"]({B});nwr["beauty"~"spa"]({B});nwr["shop"="massage"]({B}););out center tags;'
for fname, q in [('osm_poi.json', Q), ('osm_fitness.json', QF), ('osm_parks_w.json', f'[out:json][timeout:240];way["leisure"~"^(park|nature_reserve)$"]({B});out geom;')]:
    for attempt in range(5):
        try:
            req = urllib.request.Request('https://overpass.kumi.systems/api/interpreter', data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'neighborhood-finder'})
            open(RAW + fname, 'wb').write(urllib.request.urlopen(req, timeout=300).read()); break
        except Exception as e:
            print('overpass retry', e); time.sleep(20 * (attempt + 1))

# King County Assessor sales: last 12 months, house/condo, warranty deed, no special reason, single-parcel deeds; locate by parcel
z = zipfile.ZipFile(RAW + 'kc_sales.zip')
d = pd.read_csv(z.open('EXTR_RPSale.csv'), usecols=['ExciseTaxNbr', 'Major', 'Minor', 'DocumentDate', 'SalePrice', 'PrincipalUse', 'SaleInstrument', 'SaleReason'], dtype=str, encoding='latin-1')
d['date'] = pd.to_datetime(d.DocumentDate, errors='coerce'); d['price'] = pd.to_numeric(d.SalePrice, errors='coerce')
end = d.date.max().normalize().replace(day=1); start = end - pd.DateOffset(years=1)
cnt = d.groupby('ExciseTaxNbr').size()
s = d[(d.date >= start) & (d.date < end) & d.PrincipalUse.isin(['6', '2']) & d.SaleInstrument.isin(['2', '3']) & (d.SaleReason == '1') & (d.price >= 200000)].copy()
s = s[s.ExciseTaxNbr.map(cnt) == 1]
s['Major'] = s.Major.str.zfill(6); s['Minor'] = s.Minor.str.zfill(4)
s['pin'] = s.Major + s.Minor; s['lookup'] = s.pin.where(s.PrincipalUse == '6', s.Major + '0000')
s = s.drop_duplicates(['pin', 'DocumentDate'])
Lq = 'https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/PARCEL_ADDRESS_PUB_AREA_3069/FeatureServer/0/query'
pins = sorted(set(s.lookup)); got = {}
for i in range(0, len(pins), 400):
    body = urllib.parse.urlencode(dict(where="PIN IN (" + ",".join(f"'{p}'" for p in pins[i:i + 400]) + ")", outFields='PIN,LAT,LON', returnGeometry='false', f='json')).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(Lq, data=body), timeout=120))
    for f in r.get('features', []): a = f['attributes']; got[a['PIN']] = (a['LAT'], a['LON'])
s['lat'] = s.lookup.map(lambda p: got.get(p, (None, None))[0]); s['lon'] = s.lookup.map(lambda p: got.get(p, (None, None))[1])
s = s[s.lat.notna()]; s['PrincipalUse'] = s.PrincipalUse.astype(int)
s[['date', 'price', 'PrincipalUse', 'lat', 'lon']].to_csv(RAW + 'kc_sales_geo.csv', index=False)
print('done')
