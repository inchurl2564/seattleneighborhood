"""Build the finished site: puts data.json into template.html and writes index.html (a complete web page)."""
import os
here = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(here, 'template.html')).read()
d = open(os.path.join(here, 'data.json')).read().replace('</', '<\\/')
import json
cfg_path = os.path.join(here, 'config.json')
agent = json.load(open(cfg_path)).get('agent') if os.path.exists(cfg_path) else None
# neighborhood photos for result cards and detail pages (id -> file, size and credit); card-size copies are made here
from photos import photo_for, make_card_copy
photos = {}
for f in json.loads(open(os.path.join(here, 'data.json')).read())['neighborhoods']['features']:
    ph = photo_for(f['properties'])
    if ph:
        make_card_copy(ph['file']); photos[f['properties']['id']] = ph
t = t.replace('/*PHOTOS*/{}', json.dumps(photos, separators=(',', ':')).replace('</', '<\\/'))
page = t.replace('/*DATA*/', d).replace('/*AGENT*/null', json.dumps(agent).replace('</', '<\\/') if agent else 'null')
split = page.index('<div class="wrap">')
head, body = page[:split], page[split:]
html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<meta name="description" content="Find the right Seattle-area neighborhood: rank 155 neighborhoods in Seattle, Bellevue, Mercer Island, '
        'Kirkland, Redmond, Issaquah and Sammamish by schools, safety, prices, commute, parks and more, using public data.">\n'
        + head + '\n</head>\n<body>\n' + body + '\n</body>\n</html>\n')
open(os.path.join(here, 'index.html'), 'w').write(html)
print('wrote index.html', len(html) // 1024, 'KB')
