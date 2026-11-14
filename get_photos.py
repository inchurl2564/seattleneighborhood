"""Download the approved Wikimedia Commons photos listed in wiki.json into img/ for the neighborhood guides.

Only photos with a Creative Commons Attribution (CC BY / CC BY-SA), CC0 or public-domain license are used,
because those allow commercial use with credit. Each guide shows the author, license and a link back.
Adds photo_file and photo_h to wiki.json entries that were downloaded.
"""
import json, os, re, struct, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WIKI = os.path.join(HERE, 'wiki.json')
IMG = os.path.join(HERE, 'img')
UA = {'User-Agent': 'neighborhood-guide-builder/1.0 (open-data research tool)'}
OK = ('cc by', 'cc-by', 'cc0', 'public domain', 'pd')


def jpeg_size(b):
    """Return (width, height) of a JPEG from its bytes, or None."""
    i = 2
    while i < len(b):
        if b[i] != 0xFF: return None
        marker = b[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack('>HH', b[i + 5:i + 9]); return w, h
        i += 2 + struct.unpack('>H', b[i + 2:i + 4])[0]
    return None


def slug(key):
    name, city = key.split('|')
    return re.sub(r'[^a-z0-9]+', '-', f'{name} {city}'.lower()).strip('-')


if __name__ == '__main__':
    wiki = json.load(open(WIKI)); os.makedirs(IMG, exist_ok=True)
    got = 0
    for key, w in wiki.items():
        cr = (w or {}).get('credit') or {}
        if not w or w.get('error') or not cr.get('thumb_1200'): continue
        if not (cr.get('license') or '').lower().startswith(OK): continue
        existing = [x for x in (slug(key) + '.jpg', slug(key) + '.png') if os.path.exists(os.path.join(IMG, x))]
        fname = existing[0] if existing else None
        if not fname:
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(urllib.request.Request(cr['thumb_1200'], headers=UA), timeout=60) as r:
                        data = r.read()
                    break
                except urllib.error.HTTPError as e:
                    time.sleep(min(30, int(e.headers.get('Retry-After') or 10)) if e.code == 429 else 3); data = None
                except Exception:
                    time.sleep(3); data = None
            if not data or not (data[:2] == b'\xff\xd8' or data[:8] == b'\x89PNG\r\n\x1a\n'): continue
            fname = slug(key) + ('.jpg' if data[:2] == b'\xff\xd8' else '.png')
            open(os.path.join(IMG, fname), 'wb').write(data); time.sleep(0.5)
        raw = open(os.path.join(IMG, fname), 'rb').read()
        size = jpeg_size(raw) if raw[:2] == b'\xff\xd8' else struct.unpack('>II', raw[16:24])
        w['photo_file'] = fname
        w['photo_h'] = round(1200 * size[1] / size[0]) if size else 800
        got += 1
    json.dump(wiki, open(WIKI, 'w'), indent=1)
    print('photos ready:', got)
