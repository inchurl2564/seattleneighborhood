"""Generate a search-friendly guide page for every neighborhood, an index page, and a sitemap.

Reads data.json (built by build.py) and optional config.json (site address and agent details).
Writes neighborhoods/<slug>/index.html, neighborhoods/index.html, neighborhoods/style.css and sitemap.xml.
"""
import html, json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, 'data.json')))
CFG = {'site_url': 'https://inchurl2564.github.io/seattleneighborhood/'}
if os.path.exists(os.path.join(HERE, 'config.json')):
    CFG.update(json.load(open(os.path.join(HERE, 'config.json'))))
BASE = CFG['site_url'].rstrip('/') + '/'
M = DATA['meta']
P = [f['properties'] for f in DATA['neighborhoods']['features']]
N = len(P)
OUT = os.path.join(HERE, 'neighborhoods')
esc = html.escape


def slug(p):
    return re.sub(r'[^a-z0-9]+', '-', f"{p['name']} {p['city']}".lower()).strip('-')


def money(v):
    if v is None: return '—'
    if 250000 < v < 250010: return '$250K+'
    if v >= 1e6: return '$' + (f'{v / 1e6:.2f}'.rstrip('0').rstrip('.')) + 'M'
    return f'${round(v / 1000)}K'


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def rank(key, p, high_better=True):
    v = p.get(key)
    vals = [q.get(key) for q in P if q.get(key) is not None]
    if v is None: return None
    better = sum(1 for x in vals if (x > v if high_better else x < v))
    return better + 1, len(vals)


def rank_txt(key, p, words, high_better=True):
    r = rank(key, p, high_better)
    return f'{ordinal(r[0])} {words} of {r[1]}' if r else ''


def level(score, good, mid, bad):
    return good if score >= 67 else bad if score <= 33 else mid


def school_avg(p):
    v = [p[k] for k in ('elem_q', 'mid_q', 'high_q') if p.get(k) is not None]
    return sum(v) / len(v) if v else None


for p in P:
    p['slug'] = slug(p)
    p['school_avg'] = school_avg(p)
assert len({p['slug'] for p in P}) == N, 'duplicate slugs'


def nearest_neighbors(p, k=6):
    lon, lat = p['center']
    def d(q):
        return math.hypot((q['center'][0] - lon) * math.cos(math.radians(lat)), q['center'][1] - lat)
    return sorted((q for q in P if q is not p), key=d)[:k]


CSS = """:root{--bg:#f3f6f4;--surface:#fff;--surface-2:#e9efec;--line:#d3ddd8;--ink:#15211e;--muted:#5a6b66;--accent:#1d6b58;--accent-ink:#fff;--good:#1d7a4a;--bad:#b0412e;
--display:"Bricolage Grotesque","Avenir Next","Segoe UI",system-ui,sans-serif;--body:"Public Sans","Segoe UI",system-ui,-apple-system,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#0f1514;--surface:#161e1c;--surface-2:#1d2826;--line:#2c3a37;--ink:#e4ece9;--muted:#97a8a3;--accent:#5cc3a3;--accent-ink:#06201a;--good:#5fc58f;--bad:#ec7c66;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 var(--body);padding:24px max(16px,env(safe-area-inset-left,0px)) 48px}
main,header.site,footer.site{max-width:860px;margin:0 auto}
header.site{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:20px;font-size:14px}
header.site a{color:var(--accent);font-weight:600;text-decoration:none}
h1,h2{font-family:var(--display);line-height:1.2;letter-spacing:-.01em;text-wrap:balance}h1{font-size:clamp(28px,5vw,40px);margin:4px 0 6px}h2{font-size:20px;margin:28px 0 8px}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.lede{font-size:17px;color:var(--ink)}
.cta{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}
.btn{display:inline-block;background:var(--accent);color:var(--accent-ink);text-decoration:none;font-weight:600;padding:10px 16px;border-radius:8px;border:1px solid var(--accent)}
.btn.ghost{background:transparent;color:var(--accent)}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:16px 0}
.fact{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.fact b{display:block;font-family:var(--display);font-size:22px}.fact span{font-size:12.5px;color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:14px;background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}th{font-weight:600;color:var(--muted);width:42%}
tr:last-child th,tr:last-child td{border-bottom:0}
.rank{color:var(--accent);font-weight:600;font-size:13px}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;background:var(--surface-2);margin-left:6px}
.pill.g{color:var(--good)}.pill.b{color:var(--bad)}
ul.near{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}
ul.near a{display:block;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--ink);text-decoration:none}
ul.near a small{display:block;color:var(--muted)}
.agent{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:16px 18px;margin:28px 0}
.cities{columns:2 240px;column-gap:28px}.cities h2{break-before:column;margin-top:0}.cities ul{padding-left:18px;margin:0 0 18px}.cities a{color:var(--accent)}
footer.site{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}footer.site a{color:var(--accent)}
.note{font-size:13px;color:var(--muted)}
.leadform{display:grid;gap:10px;max-width:520px}.leadform label{display:grid;gap:4px;font-size:13px;font-weight:600}.leadform input,.leadform textarea{font:inherit;font-weight:400;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)}.leadform .consent{display:flex;gap:8px;font-weight:400;align-items:flex-start}.leadform button{justify-self:start;cursor:pointer;font:inherit;font-weight:600}
"""

FOOT = """<footer class="site">
<p><b>For research only.</b> Not real estate, legal, financial or tax advice. Figures are estimates from public data that may be incomplete or out of date; verify school assignments with the district, crime with local police, and listings with a licensed real estate professional.</p>
<p>Rankings never use race, color, religion, national origin, sex, disability or familial status.</p>
<p>Data: Zillow Research; King County Assessor; WA OSPI; NCES; Seattle and Bellevue police and the FBI Crime Data Explorer; US Census Bureau; US EPA; King County Metro and Sound Transit; King County and city GIS; © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors.</p>
{agent}
</footer>"""


def agent_footer():
    a = CFG.get('agent')
    if not a: return ''
    prof = f' · <a href="{esc(a["profile_url"])}">View my profile</a>' if a.get('profile_url') else ''
    return f'<p style="color:var(--ink)">Brought to you by <b>{esc(a["name"])}</b>, {esc(a["brokerage"])}{prof} · <a href="mailto:{esc(a["email"])}">{esc(a["email"])}</a></p>'


def agent_box(p):
    a = CFG.get('agent')
    if not a: return ''
    from urllib.parse import quote
    first = a.get('first_name') or a['name'].split()[0]
    intro = (f'<h2 style="margin-top:0">Thinking about {esc(p["name"])}?</h2>'
             f'<p>{esc(a["name"])}, {esc(a["brokerage"])}, can walk you through homes for sale, recent sales and what to know before you buy here.</p>')
    privacy = (f'<p class="note">Your details go only to {esc(a["name"])} at {esc(a["brokerage"])} to answer your request. They are not sold or shared.</p>')
    if a.get('formspree_id'):
        form = (f'<form action="https://formspree.io/f/{esc(a["formspree_id"])}" method="POST" class="leadform">'
                f'<input type="hidden" name="_subject" value="Question about {esc(p["name"])}, {esc(p["city"])}">'
                f'<input type="hidden" name="neighborhood" value="{esc(p["name"])}, {esc(p["city"])}">'
                '<label>Your name<input name="name" required autocomplete="name"></label>'
                '<label>Email<input name="email" type="email" required autocomplete="email"></label>'
                '<label>Phone (optional)<input name="phone" type="tel" autocomplete="tel"></label>'
                f'<label>Message<textarea name="message" rows="3">Hi {esc(first)}, I\'d like to learn more about {esc(p["name"])}.</textarea></label>'
                f'<label class="consent"><input type="checkbox" name="consent" value="yes" required> I agree to be contacted by {esc(a["name"])} of {esc(a["brokerage"])} about my home search.</label>'
                f'<button class="btn" type="submit">Ask {esc(first)} about {esc(p["name"])}</button></form>')
    else:
        subject = quote(f'Question about {p["name"]}, {p["city"]}')
        body = quote(f'Hi {first},\n\nI\'d like to learn more about {p["name"]} in {p["city"]}.\n\nName:\nPhone (optional):\nWhen I\'m hoping to buy:\n\n'
                     f'(Sent from the {p["name"]} guide on Seattle Neighborhood Match. I agree to be contacted about my home search.)')
        form = f'<div class="cta"><a class="btn" href="mailto:{esc(a["email"])}?subject={subject}&amp;body={body}">Ask {esc(first)} about {esc(p["name"])}</a></div>'
    return f'<section class="agent" aria-label="Talk to a local agent">{intro}{form}{privacy}</section>'


def page(p):
    s, sc = p['scores'], p['school_avg']
    nm, city = esc(p['name']), esc(p['city'])
    where = f"{esc(p['district'])}, {city}" if p.get('district') and p['district'] != p['name'] else city
    yoy = (p['price'] / p['price_prev'] - 1) * 100 if p.get('price') and p.get('price_prev') else None
    crime_lvl = level(s['safety'], 'lower crime than most neighborhoods in the area', 'about average crime for the area', 'higher crime than most neighborhoods in the area')
    walk_lvl = level(s['walk'], 'very walkable', 'somewhat walkable', 'mostly car-dependent')
    title = f"{p['name']}, {p['city']}: Schools, Home Prices, Crime & Commute"
    desc = (f"Living in {p['name']} ({p['city']}, WA): typical home value {money(p['price'])}, "
            f"{round(sc)}% of nearby students meet state standards, {walk_lvl}, {crime_lvl}. Compare with 155 Seattle-area neighborhoods.")
    sch_rows = ''.join(
        f"<tr><th>{lab}</th><td>{esc(p['sch'][k]['name'])}, {p['sch'][k]['mi']} mi · {p['sch'][k]['prof']}% meet standard"
        f"<br><span class='rank'>Area average {p['sch'][k]['q']}% · {rank_txt(k + '_q', p, {'elem': 'best elementary schools', 'mid': 'best middle schools', 'high': 'best high schools'}[k])}</span></td></tr>"
        for k, lab in (('elem', 'Elementary'), ('mid', 'Middle school'), ('high', 'High school')))
    near = ''.join(f'<li><a href="../{q["slug"]}/">{esc(q["name"])}<small>{esc(q["city"])} · {money(q["price"])}</small></a></li>' for q in nearest_neighbors(p))
    crime_note = (f"This is {esc(p['city'])}'s citywide rate, because {esc(p['city'])} does not publish where incidents occur."
                  if p['crime_level'] == 'city' else 'Based on mapped police incidents in this neighborhood, scaled to the city\'s FBI-reported rate. Busy commercial areas can look high because visitors are not counted as residents.')
    app = f'../../#nb-{p["id"]}'
    ld = {"@context": "https://schema.org", "@type": "Place", "name": f"{p['name']}, {p['city']}, WA",
          "geo": {"@type": "GeoCoordinates", "latitude": p['center'][1], "longitude": p['center'][0]},
          "containedInPlace": {"@type": "City", "name": f"{p['city']}, Washington"}, "url": f"{BASE}neighborhoods/{p['slug']}/"}
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}neighborhoods/{p['slug']}/">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="article">
<link rel="stylesheet" href="../style.css">
<script type="application/ld+json">{json.dumps(ld)}</script>
</head><body>
<header class="site"><a href="../../">← Seattle Neighborhood Match</a><a href="../">All neighborhoods</a></header>
<main>
<div class="eyebrow">{where}</div>
<h1>Living in {nm}</h1>
<p class="lede">{nm} is a neighborhood in {where} with about {p['pop']:,} residents. The typical home value is about <b>{money(p['price'])}</b>{f" ({yoy:+.1f}% over the past year)" if yoy is not None else ''}, and {p['sold_12m']} homes sold in the last 12 months. It is {walk_lvl}, with {crime_lvl}.</p>
<div class="cta"><a class="btn" href="{app}">See how {nm} fits your priorities</a><a class="btn ghost" href="../../">Find your best-matching neighborhoods</a></div>

<div class="facts">
<div class="fact"><b>{money(p['price'])}</b><span>Typical home value · {rank_txt('price', p, 'highest priced')}</span></div>
<div class="fact"><b>{round(sc)}%</b><span>Students meeting standard nearby · {rank_txt('school_avg', p, 'best schools')}</span></div>
<div class="fact"><b>{round(p['crime_index'])}</b><span>Crimes per 1,000 residents · {rank_txt('crime_index', p, 'lowest crime', False)}</span></div>
<div class="fact"><b>{p['walk']:.1f}<small style="font-size:13px"> / 20</small></b><span>Walkability · {rank_txt('walk', p, 'most walkable')}</span></div>
</div>

<h2>Home prices and the market</h2>
<table>
<tr><th>Typical home value</th><td>{money(p['price'])}{f" · {yoy:+.1f}% over 12 months" if yoy is not None else ''}</td></tr>
<tr><th>Homes sold, last 12 months</th><td>{p['sold_12m']}{f" · median sale price {money(p['median_sale'])}" if p.get('median_sale') else ''}{f" · {p['sold_condo_12m']} were condos" if p.get('sold_condo_12m') else ''}</td></tr>
<tr><th>Homes for sale (estimate)</th><td>{round(p['for_sale']) if p.get('for_sale') is not None else '—'}{f" · homes typically go under contract in {round(p['dom'])} days" if p.get('dom') else ''}</td></tr>
<tr><th>Median household income</th><td>{money(p['income'])} · <span class="rank">{rank_txt('income', p, 'highest income')}</span></td></tr>
</table>

<h2>Schools</h2>
<table>{sch_rows}
<tr><th>Nearest college</th><td>{esc(p['college_name'])}, {p['college_mi']} mi</td></tr>
</table>
<p class="note">Share of students meeting the Washington state standard in English and math ({esc(M['ospi_year'])}). The nearest school is not always the assigned school; check with the school district.</p>

<h2>Safety</h2>
<p>About <b>{round(p['crime_index'])} crimes per 1,000 residents</b> a year (violent crimes counted three times), {crime_lvl}: <span class="rank">{rank_txt('crime_index', p, 'lowest crime', False)}</span>. {crime_note}</p>

<h2>Getting around</h2>
<table>
<tr><th>Walkability</th><td>{p['walk']:.1f} of 20 ({walk_lvl}) · <span class="rank">{rank_txt('walk', p, 'most walkable')}</span></td></tr>
<tr><th>Light rail or train</th><td>{esc(p['rail_name'])}, {p['rail_mi']} mi · <span class="rank">{rank_txt('rail_mi', p, 'closest to rail', False)}</span></td></tr>
<tr><th>Nearest bus stop</th><td>{esc(p['bus_name'])}, {p['bus_mi']:.2f} mi</td></tr>
<tr><th>How residents commute</th><td>{round(p.get('pct_transit_commute') or 0)}% take transit · {round(p.get('pct_wfh') or 0)}% work from home</td></tr>
</table>

<h2>Everyday amenities</h2>
<table>
<tr><th>Grocery store</th><td>{esc(p['grocery_name'])}, {p['grocery_mi']} mi · {p['grocery_1mi']} within a mile</td></tr>
<tr><th>Pharmacy</th><td>{esc(p['pharm_name'])}, {p['pharm_mi']} mi</td></tr>
<tr><th>Restaurants</th><td>{p['rest_1mi']} within a mile · <span class="rank">{rank_txt('rest_1mi', p, 'most restaurants nearby')}</span></td></tr>
<tr><th>Shopping</th><td>{esc(p['retail_name'])}, {p['retail_mi']} mi</td></tr>
<tr><th>Hospital</th><td>{esc(p['hosp_name'])}, {p['hosp_mi']} mi · {p['clinics_2mi']} clinics within 2 miles</td></tr>
<tr><th>Library</th><td>{esc(p['lib_name'])}, {p['lib_mi']} mi</td></tr>
</table>

<h2>Parks and recreation</h2>
<table>
<tr><th>Nearest park</th><td>{esc(p['park_name'])}, {p['park_mi']} mi · {round(p['park_acres_1mi']):,} acres of parks within a mile</td></tr>
<tr><th>Large green space</th><td>{esc(p['green_name'])}, {p['green_mi']} mi</td></tr>
<tr><th>Walking trail</th><td>{esc(p['trail_name'] or '—')}, {p['trail_mi']} mi</td></tr>
<tr><th>Gyms, spas and studios</th><td>{p['fit_1mi']} within a mile</td></tr>
<tr><th>Golf</th><td>{esc(p['golf_name'])}, {p['golf_mi']} mi</td></tr>
</table>

{agent_box(p)}

<h2>Nearby neighborhoods</h2>
<ul class="near">{near}</ul>

<p class="note">Data as of: home values Zillow {esc(M['zhvi_month'])}; recorded sales {esc(M['sales_window'])}; schools OSPI {esc(M['ospi_year'])}; Census ACS {esc(M['acs_year'])}. Distances are straight-line from the center of the neighborhood.</p>
</main>
{FOOT.format(agent=agent_footer())}
</body></html>
"""


def index_page():
    cities = {}
    for p in sorted(P, key=lambda q: q['name']):
        cities.setdefault(p['city'], []).append(p)
    blocks = ''.join(f"<div><h2>{esc(c)}</h2><ul>" + ''.join(f'<li><a href="{q["slug"]}/">{esc(q["name"])}</a> <span class="note">{money(q["price"])}</span></li>' for q in cities[c]) + '</ul></div>'
                     for c in ['Seattle', 'Bellevue', 'Kirkland', 'Redmond', 'Mercer Island', 'Issaquah', 'Sammamish'] if c in cities)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Seattle-Area Neighborhood Guides: Schools, Prices, Crime & Commute</title>
<meta name="description" content="Guides to {N} neighborhoods in Seattle, Bellevue, Kirkland, Redmond, Mercer Island, Issaquah and Sammamish: home prices, schools, crime, walkability, transit and parks from public data.">
<link rel="canonical" href="{BASE}neighborhoods/">
<link rel="stylesheet" href="style.css">
</head><body>
<header class="site"><a href="../">← Seattle Neighborhood Match</a></header>
<main>
<h1>Seattle-area neighborhood guides</h1>
<p class="lede">Home prices, schools, safety, walkability, transit and parks for {N} neighborhoods, built from public data. Want them ranked for you? <a href="../">Answer a few questions</a>.</p>
<div class="cities">{blocks}</div>
</main>
{FOOT.format(agent=agent_footer())}
</body></html>
"""


os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'style.css'), 'w').write(CSS)
for p in P:
    d = os.path.join(OUT, p['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w').write(page(p))
open(os.path.join(OUT, 'index.html'), 'w').write(index_page())
urls = [BASE, BASE + 'neighborhoods/'] + [f"{BASE}neighborhoods/{p['slug']}/" for p in P]
open(os.path.join(HERE, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                                   + ''.join(f'  <url><loc>{u}</loc><lastmod>{DATA["generated"]}</lastmod></url>\n' for u in urls) + '</urlset>\n')
print('wrote', N, 'guide pages, index and sitemap with', len(urls), 'URLs')
