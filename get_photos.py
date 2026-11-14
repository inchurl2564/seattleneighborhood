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


def commons_url(fname, width):
    """Address of a Commons file on upload.wikimedia.org: the original if small, else the standard 1280px thumbnail."""
    import hashlib, urllib.parse
    name = fname.replace(' ', '_'); h = hashlib.md5(name.encode('utf-8')).hexdigest()
    q = urllib.parse.quote(name)
    if width and width <= 1280: return f'https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{q}'
    return f'https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/1280px-{q}'


def slug(key):
    name, city = key.split('|')
    return re.sub(r'[^a-z0-9]+', '-', f'{name} {city}'.lower()).strip('-')


if __name__ == '__main__':
    wiki = json.load(open(WIKI)); os.makedirs(IMG, exist_ok=True)
    # photo_vetoed: removed after review, never downloaded again
    todo = [k for k, w in wiki.items() if w and not w.get('error') and not w.get('photo_vetoed') and ((w.get('credit') or {}).get('thumb_1200'))
            and ((w['credit'].get('license') or '').lower().startswith(OK))]
    # Wikimedia throttles bursts (HTTP 429), so go slowly and come back to throttled photos on a later pass
    for rnd in range(6):
        left = [k for k in todo if not os.path.exists(os.path.join(IMG, slug(k) + '.jpg'))]
        if not left: break
        print(f'pass {rnd + 1}: {len(left)} to fetch', flush=True)
        for key in left:
            w = wiki[key]
            url = commons_url(w['image'], w['credit'].get('width') or 0)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    data = r.read()
            except urllib.error.HTTPError as e:
                print(' ', key, e.code, flush=True); time.sleep(20 if e.code == 429 else 2); continue
            except Exception as e:
                print(' ', key, e, flush=True); time.sleep(5); continue
            if not (data[:2] == b'\xff\xd8' or data[:8] == b'\x89PNG\r\n\x1a\n'): continue
            # shrink to a web-friendly JPEG (1200px wide) so guide pages load fast on phones
            from PIL import Image
            import io
            im = Image.open(io.BytesIO(data)).convert('RGB')
            if im.width > 1200: im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
            im.save(os.path.join(IMG, slug(key) + '.jpg'), 'JPEG', quality=72, optimize=True, progressive=True)
            print(' ok', key, flush=True); time.sleep(4)
    got = 0
    for key in todo:
        fname = slug(key) + '.jpg'
        if not os.path.exists(os.path.join(IMG, fname)): continue
        size = jpeg_size(open(os.path.join(IMG, fname), 'rb').read())
        wiki[key]['photo_file'] = fname
        wiki[key]['photo_h'] = round(1200 * size[1] / size[0]) if size else 800
        got += 1
    json.dump(wiki, open(WIKI, 'w'), indent=1)
    print('photos ready:', got)
