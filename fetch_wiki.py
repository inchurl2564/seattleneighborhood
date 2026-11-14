"""Find each neighborhood's Wikipedia article, intro text and lead photo (with author and license).

Writes raw/wiki.json. A match must have coordinates near the neighborhood's center and a title that
contains the neighborhood name, so look-alike articles elsewhere are not used.
"""
import json, math, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'neighborhood-guide-builder/1.0 (open-data research tool)'}
API = 'https://en.wikipedia.org/w/api.php'
COMMONS = 'https://commons.wikimedia.org/w/api.php'


def get(url, params):
    q = url + '?' + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': 2})
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=60) as r:
                return json.load(r)
        except Exception as e:
            time.sleep(2 * (i + 1)); err = e
    raise err


def km(a, b):
    return 6371 * math.hypot(math.radians(a[1] - b[1]) * math.cos(math.radians(a[0])), math.radians(a[0] - b[0]))


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower().replace('&', 'and'))


def find(p):
    lat, lon = p['center'][1], p['center'][0]
    name = re.sub(r'\s*/.*$', '', p['name'])          # "Cougar Mountain / Lakemont" -> "Cougar Mountain"
    queries = [f'{name}, {p["city"]}, Washington', f'{name} {p["city"]} neighborhood', f'{name}, Washington']
    seen = set()
    for q in queries:
        res = get(API, {'action': 'query', 'list': 'search', 'srsearch': q, 'srlimit': 5})
        titles = [r['title'] for r in res['query']['search'] if r['title'] not in seen]
        seen.update(titles)
        if not titles: continue
        info = get(API, {'action': 'query', 'titles': '|'.join(titles), 'prop': 'coordinates|pageimages|extracts|info',
                         'exintro': 1, 'explaintext': 1, 'exsentences': 3, 'piprop': 'name|thumbnail', 'pithumbsize': 1200,
                         'inprop': 'url', 'redirects': 1})
        pages = {pg['title']: pg for pg in info['query'].get('pages', []) if not pg.get('missing')}
        for t in titles:
            pg = pages.get(t)
            if not pg or not pg.get('coordinates'): continue
            c = pg['coordinates'][0]
            d = km((lat, lon), (c['lat'], c['lon']))
            if d > 3.0: continue
            if norm(name) not in norm(pg['title']): continue
            return {'title': pg['title'], 'url': pg.get('fullurl'), 'km_from_center': round(d, 2),
                    'extract': (pg.get('extract') or '').strip(), 'image': pg.get('pageimage'), 'thumb': (pg.get('thumbnail') or {}).get('source')}
    return None


def image_credit(fname):
    r = get(COMMONS, {'action': 'query', 'titles': 'File:' + fname, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime'})
    pg = r['query']['pages'][0]
    if 'imageinfo' not in pg: return None
    ii = pg['imageinfo'][0]; md = ii.get('extmetadata', {})
    clean = lambda v: re.sub(r'<[^>]+>', '', (md.get(v) or {}).get('value', '')).strip()
    return {'file_page': ii.get('descriptionurl'), 'artist': clean('Artist'), 'license': clean('LicenseShortName'),
            'license_url': clean('LicenseUrl'), 'mime': ii.get('mime'), 'width': ii.get('width')}


if __name__ == '__main__':
    data = json.load(open(os.path.join(HERE, 'data.json')))
    out = {}
    for f in data['neighborhoods']['features']:
        p = f['properties']; key = f"{p['name']}|{p['city']}"
        try:
            m = find(p)
            if m and m['image'] and not m['image'].lower().endswith(('.svg', '.png')):
                m['credit'] = image_credit(m['image'])
            elif m:
                m['image'] = None   # maps and diagrams (SVG/PNG) are not neighborhood photos
            out[key] = m
        except Exception as e:
            out[key] = {'error': str(e)}
        time.sleep(0.2)
    os.makedirs(os.path.join(HERE, 'raw'), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, 'raw', 'wiki.json'), 'w'), indent=1)
    found = [k for k, v in out.items() if v and not v.get('error')]
    print('articles', len(found), 'of', len(out), '| with photo', sum(1 for k in found if out[k].get('image')))
