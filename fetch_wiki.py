"""Find each neighborhood's Wikipedia article, intro text and lead photo (with author and license).

Writes wiki.json when finished; progress is saved to raw/wiki.partial.json after every neighborhood so an interrupted run can resume.
Uses Wikipedia's page-summary interface with likely article titles (it is far less rate-limited than search).
A match must have coordinates within 3 km of the neighborhood's center, so same-named places elsewhere are not used.
"""
import json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'wiki.json')
PARTIAL = os.path.join(HERE, 'raw', 'wiki.partial.json')   # progress while running (not committed)
UA = {'User-Agent': 'neighborhood-guide-builder/1.0 (open-data research tool)'}
SUMMARY = 'https://en.wikipedia.org/api/rest_v1/page/summary/'
COMMONS = 'https://commons.wikimedia.org/w/api.php'


def fetch(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code == 429:
                time.sleep(min(30, int(e.headers.get('Retry-After') or 10))); continue
            time.sleep(3)
        except Exception:
            time.sleep(3)
    return None


def km(a, b):
    return 6371 * math.hypot(math.radians(a[1] - b[1]) * math.cos(math.radians(a[0])), math.radians(a[0] - b[0]))


def candidates(p):
    """Most likely article titles first, at most three, to keep requests (and rate-limit waits) low."""
    n = re.sub(r'\s*\(.*\)$', '', p['name'].split('/')[0].strip())
    if p['city'] == 'Seattle':
        out = [f'{n}, Seattle', f'{n}, Seattle, Washington', n]
    else:
        out = [f'{n}, {p["city"]}, Washington', f'{n}, Washington', f'{n}, {p["city"]}']
    seen, uniq = set(), []
    for c in out:
        if c not in seen: seen.add(c); uniq.append(c)
    return uniq


def find(p):
    here = (p['center'][1], p['center'][0])
    for title in candidates(p):
        s = fetch(SUMMARY + urllib.parse.quote(title.replace(' ', '_'), safe=''))
        time.sleep(0.3)
        if not s or s.get('type') != 'standard' or not s.get('coordinates'): continue
        c = s['coordinates']; d = km(here, (c['lat'], c['lon']))
        if d > 3.0: continue
        img = (s.get('originalimage') or {}).get('source')
        fname = urllib.parse.unquote(img.rsplit('/', 1)[-1]) if img else None
        return {'title': s['title'], 'url': s['content_urls']['desktop']['page'], 'km_from_center': round(d, 2),
                'extract': s.get('extract', '').strip(), 'image': fname, 'thumb': (s.get('thumbnail') or {}).get('source')}
    return None


def image_credit(fname):
    q = COMMONS + '?' + urllib.parse.urlencode({'action': 'query', 'titles': 'File:' + fname, 'prop': 'imageinfo',
                                                 'iiprop': 'url|extmetadata|size|mime', 'iiurlwidth': 1200, 'format': 'json', 'formatversion': 2})
    r = fetch(q)
    if not r: return None
    pg = r['query']['pages'][0]
    if 'imageinfo' not in pg: return None
    ii = pg['imageinfo'][0]; md = ii.get('extmetadata', {})
    clean = lambda v: re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', (md.get(v) or {}).get('value', ''))).strip()
    return {'file_page': ii.get('descriptionurl'), 'artist': clean('Artist'), 'license': clean('LicenseShortName'),
            'license_url': clean('LicenseUrl'), 'mime': ii.get('mime'), 'width': ii.get('width'), 'height': ii.get('height'),
            'thumb_1200': ii.get('thumburl')}


if __name__ == '__main__':
    data = json.load(open(os.path.join(HERE, 'data.json')))
    os.makedirs(os.path.dirname(PARTIAL), exist_ok=True)
    out = json.load(open(PARTIAL)) if os.path.exists(PARTIAL) else (json.load(open(OUT)) if os.path.exists(OUT) else {})
    for f in data['neighborhoods']['features']:
        p = f['properties']; key = f"{p['name']}|{p['city']}"
        if key in out and 'error' not in (out[key] or {}): continue
        try:
            m = find(p)
            if m and m['image'] and m['image'].lower().endswith(('.jpg', '.jpeg', '.webp', '.tif', '.tiff')):
                m['credit'] = image_credit(m['image'])
            elif m:
                m['image'] = None   # maps, logos and diagrams (SVG/PNG/GIF) are not neighborhood photos
            out[key] = m
        except Exception as e:
            out[key] = {'error': str(e)}
        json.dump(out, open(PARTIAL, 'w'), indent=1)
        print(key, '->', (out[key] or {}).get('title'), flush=True)
    json.dump(out, open(OUT, 'w'), indent=1)
    found = [k for k, v in out.items() if v and not v.get('error')]
    print('articles', len(found), 'of', len(out), '| with photo', sum(1 for k in found if out[k].get('image')))
