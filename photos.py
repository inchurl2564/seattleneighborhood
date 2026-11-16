"""Which neighborhood photo and Wikipedia intro to show, shared by the app (make_page.py) and the guides (make_guides.py).

A photo is shown only when it has a license that allows commercial use with credit (CC BY, CC BY-SA, CC0, public domain),
was not removed after review (photo_vetoed) or held for review (photo_hold), and the article it came from is about
this neighborhood rather than a larger area around it.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WIKI = {}
_wp = os.path.join(HERE, 'wiki.json')
if os.path.exists(_wp): WIKI = json.load(open(_wp))
OK_LICENSES = ('cc by', 'cc-by', 'cc0', 'public domain', 'pd', 'unsplash')
CARD_DIR = 'img/card'          # small copies for result cards (600px wide)

# Articles under another name that describe exactly this neighborhood (not a larger area around it)
SAME_PLACE = {'Central Business District|Seattle', 'Harrison/Denny-Blaine|Seattle', 'Holly Park|Seattle'}


def wiki_for(p):
    w = WIKI.get(f"{p['name']}|{p['city']}")
    return w if w and not w.get('error') else None


def broader_area(p, w):
    """Name of the larger area when the matched article covers more than this neighborhood, else None."""
    key = f"{p['name']}|{p['city']}"
    base = re.sub(r',.*$', '', w['title'])
    simple = lambda t: re.sub(r'[^a-z]', '', t.lower())
    if key in SAME_PLACE or simple(p['name'].split('/')[0]) in simple(base): return None
    return base


def photo_for(p):
    """The photo entry and its credit for a neighborhood, or None."""
    w = wiki_for(p)
    if not w or not w.get('photo_file') or w.get('photo_vetoed') or w.get('photo_hold'): return None
    cr = w.get('credit') or {}
    if not (cr.get('license') or '').lower().startswith(OK_LICENSES) or broader_area(p, w): return None
    if not os.path.exists(os.path.join(HERE, 'img', w['photo_file'])): return None
    return {'file': w['photo_file'], 'h': w.get('photo_h', 675), 'by': cr.get('artist') or 'Unknown author',
            'lic': cr.get('license', ''), 'lic_url': cr.get('license_url', ''), 'page': cr.get('file_page', ''),
            'src': 'Unsplash' if 'unsplash' in (cr.get('license') or '').lower() else 'Wikimedia Commons'}


def make_card_copy(fname):
    """Write a 600px-wide copy of a photo for result cards (skipped when it already exists)."""
    out = os.path.join(HERE, CARD_DIR, fname)
    if os.path.exists(out): return
    from PIL import Image
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im = Image.open(os.path.join(HERE, 'img', fname)).convert('RGB')
    if im.width > 600: im = im.resize((600, round(im.height * 600 / im.width)), Image.LANCZOS)
    im.save(out, 'JPEG', quality=72, optimize=True, progressive=True)
