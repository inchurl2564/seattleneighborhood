"""Sanity checks on a freshly built data.json before it goes live.

Compares the new build with the version currently committed (git HEAD) and fails if something looks broken,
so a bad download never replaces good data on the site. Exit code 0 = OK to publish.
Usage: python3 check_data.py
"""
import json, os, statistics, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
new = json.load(open(os.path.join(HERE, 'data.json')))
try:
    old = json.loads(subprocess.run(['git', 'show', 'HEAD:data.json'], cwd=HERE, capture_output=True, check=True).stdout)
except Exception:
    old = None

problems = []
P = [f['properties'] for f in new['neighborhoods']['features']]
if len(P) != 155: problems.append(f'expected 155 neighborhoods, got {len(P)}')

REQUIRED = ['price', 'income', 'walk', 'crime_index', 'school_prof', 'rail_mi', 'grocery_mi', 'park_mi', 'hosp_mi', 'sold_12m']
for k in REQUIRED:
    missing = [p['name'] for p in P if p.get(k) is None]
    if len(missing) > 5: problems.append(f'{k} missing for {len(missing)} neighborhoods (e.g. {", ".join(missing[:3])})')

for k in ['schools', 'safety', 'walk', 'afford', 'transit']:
    vals = [p['scores'].get(k) for p in P]
    if any(v is None or v != v for v in vals): problems.append(f'score {k} has blanks')

if old:
    OP = {p['id']: p for p in (f['properties'] for f in old['neighborhoods']['features'])}
    def med_change(k):
        r = [P_[k] / OP[P_['id']][k] for P_ in P if P_['id'] in OP and P_.get(k) and OP[P_['id']].get(k)]
        return statistics.median(r) if r else 1
    for k, lim in [('price', .15), ('income', .25), ('crime_index', .6), ('school_prof', .25), ('walk', .05)]:
        c = med_change(k)
        if abs(c - 1) > lim: problems.append(f'median {k} changed by {100 * (c - 1):+.0f}% since last build (limit ±{100 * lim:.0f}%)')
    s_new = sum(p['sold_12m'] for p in P); s_old = sum(p['sold_12m'] for p in OP.values())
    if s_old and not .6 < s_new / s_old < 1.6: problems.append(f'total recent sales went from {s_old} to {s_new}')

m = new.get('meta', {})
print('Data as of:', {k: m.get(k) for k in ('zhvi_month', 'market_month', 'sales_window', 'crime_window')})
if problems:
    print('NOT publishing, because:'); [print(' -', x) for x in problems]; sys.exit(1)
print('All checks passed.')
