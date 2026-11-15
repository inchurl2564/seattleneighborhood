"""Build Rachel's home page (index.html) and the home value consultation page (home-value/index.html).

Fills site_home.html and site_value.html with:
- the six featured neighborhood tiles: the two highest-priced neighborhoods (typical home value) in Bellevue,
  Kirkland and Sammamish, recalculated from data.json on every build, so they follow the monthly data refresh
- the contact forms (sent to the agent through Formspree, or the visitor's email app if no form ID is set)
- the shared footer
"""
import html, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, 'config.json')))
A = CFG['agent']
SITE = CFG['site_url'].rstrip('/') + '/'
esc = lambda s: html.escape(str(s), quote=True)

FEATURED_CITIES = ['Bellevue', 'Kirkland', 'Sammamish']
PER_CITY = 2
DISPLAY_NAMES = {'Lake Sammamish Shore (West)': 'West Lake Sammamish'}   # shorter labels that fit on a tile


def money(v):
    return f'${v / 1e6:.2f}M' if v >= 1e6 else f'${v / 1e3:.0f}K'


def tiles():
    # reuse the guide pages' map drawing (only the setup part of make_guides.py, so no guide pages are rewritten here)
    src = open(os.path.join(HERE, 'make_guides.py')).read().split('\n')
    cut = next(i for i, l in enumerate(src) if l.startswith('for p in P'))
    ns = {'__file__': os.path.join(HERE, 'make_guides.py'), '__name__': 'make_guides_setup'}
    exec('\n'.join(src[:cut]), ns)
    for p in ns['P']: p['slug'] = ns['slug'](p)
    g = type('G', (), {'P': ns['P'], 'svg_map': staticmethod(ns['svg_map'])})
    out = []
    for city in FEATURED_CITIES:
        ps = sorted((p for p in g.P if p['city'] == city and p.get('price')), key=lambda p: -p['price'])[:PER_CITY]
        for p in ps:
            svg = g.svg_map(p)
            svg = re.sub(r'<figcaption.*?</figcaption>', '', svg, flags=re.S)
            svg = re.sub(r'<g class="m-pin">.*?</g>', '', svg)
            name = DISPLAY_NAMES.get(p['name'], p['name'])
            out.append(f'    <a class="tile maptile" href="neighborhoods/{p["slug"]}/"><span class="tmap">{svg}</span>'
                       f'<div><h3>{esc(name)}</h3><small>{esc(city)} · Typical home {money(p["price"])}</small></div></a>')
    return '\n'.join(out)


def consent(purpose):
    who = f'{esc(A["name"])} of {esc(A["brokerage"])}'
    return (f'<label class="cons"><input type="checkbox" name="consent" value="yes" required> I agree to be contacted by {who} by email or phone {purpose}.</label>\n'
            f'    <label class="cons"><input type="checkbox" name="sms_consent" value="yes"> <span><b>Optional: OK to text me.</b> {SMS}</span></label>\n'
            f'    <p class="priv">Your details go only to {esc(A["name"])} at {esc(A["brokerage"])}. They are not sold or shared, and your mobile number and texting permission are never shared with anyone for marketing.{{EXTRA}}</p>\n'
            '    <p class="ferr" role="alert" hidden></p>')


SMS = (f'I agree to receive text messages from {esc(A["name"])} of {esc(A["brokerage"])} at the mobile number above. '
       'Message frequency varies. Message and data rates may apply. Reply STOP to opt out or HELP for help. Agreeing is not required.')


def footer(pfx):
    return f'''<footer><div class="wrap">
  <div><b>Rachel Yo</b>Broker · {esc(A["brokerage"])}<br>15 Lake Street, Suite 200, Kirkland, WA 98033<br><a href="tel:+15127971935">Mobile 512.797.1935</a> · <a href="tel:+14256585300">Office 425.658.5300</a><br><a href="mailto:{esc(A["email"])}">{esc(A["email"])}</a></div>
  <div><a href="{pfx}match/">Neighborhood Match</a><br><a href="{pfx}home-value/">What's My Home Worth?</a><br><a href="{pfx}neighborhoods/">Neighborhood guides</a><br><a href="{esc(A["profile_url"])}" target="_blank" rel="noopener">Sotheby's profile</a></div>
  <div>Your privacy: what you type into Neighborhood Match stays in your browser. Contact forms go only to Rachel.</div>
  <div class="legal">{esc(A["brokerage"])}. Each office is independently owned and operated. Equal Housing Opportunity. Neighborhood Match rankings use schools, safety, prices and amenities and never race, color, religion, national origin, sex, disability or familial status. Neighborhood data is from public sources and may be incomplete; verify anything important.</div>
</div></footer>'''


FORM_JS = '''<script>
/* Contact forms: check the fields, then send to the agent (Formspree), or open an email if no form ID is set. */
(function(){
  var FS = %s, EMAIL = %s, NAME = %s, SMS = %s;
  document.querySelectorAll('a[data-topic]').forEach(function(a){ a.addEventListener('click', function(){
    var s = document.querySelector('#contact select[name=topic]'); if(s) s.value = a.dataset.topic; }); });
  document.querySelectorAll('form.leadform').forEach(function(f){
    f.addEventListener('submit', function(e){
      e.preventDefault();
      var err = f.querySelector('.ferr'), val = function(n){ var el = f.elements[n]; return el ? (el.value || '').trim() : ''; };
      var show = function(m){ err.textContent = m; err.hidden = false; };
      if(f.elements.address && !val('address')) return show('Please add your home address.');
      if(!val('name')) return show('Please add your name.');
      if(!/^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(val('email'))) return show('Please add a valid email address so Rachel can reply.');
      if(!f.elements.consent.checked) return show('Please check the box to agree to be contacted.');
      var sms = f.elements.sms_consent.checked;
      if(sms && val('phone').replace(/\\D/g,'').length < 10) return show('Please add a mobile number to get texts, or uncheck the texting box.');
      err.hidden = true;
      var data = {}, lines = [];
      Array.prototype.forEach.call(f.elements, function(el){
        if(!el.name || el.type === 'submit' || el.name === 'consent' || el.name === 'sms_consent') return;
        if(el.type === 'checkbox'){ if(el.checked) data[el.name] = (data[el.name] ? data[el.name] + ', ' : '') + el.value; return; }
        if(el.value.trim()) data[el.name] = el.value.trim();
      });
      Object.keys(data).forEach(function(k){ lines.push(k.replace(/_/g,' ') + ': ' + data[k]); });
      data._subject = f.dataset.subject + (data.name ? ' from ' + data.name : '');
      data.consent = 'yes'; data.sms_consent = sms ? 'yes' : 'no'; data.sms_terms = sms ? SMS : ''; data.consent_time = new Date().toISOString();
      lines.push('Texting: ' + (sms ? 'OK to text (agreed to: ' + SMS + ')' : 'Not permitted. Do not text.'));
      var done = function(){ f.innerHTML = '<div class="fdone"><b>Thank you, ' + (data.name || '').split(' ')[0].replace(/[<>&]/g,'') + '!</b> Your request is on its way to ' + NAME + ', who will be in touch soon.</div>'; };
      if(!FS){ location.href = 'mailto:' + EMAIL + '?subject=' + encodeURIComponent(data._subject) + '&body=' + encodeURIComponent(lines.join('\\n')); return; }
      var b = f.querySelector('button[type=submit]'); b.disabled = true; b.textContent = 'Sending…';
      fetch('https://formspree.io/f/' + encodeURIComponent(FS), {method:'POST', headers:{'Accept':'application/json','Content-Type':'application/json'}, body: JSON.stringify(data)})
        .then(function(r){ if(!r.ok) throw 0; done(); })
        .catch(function(){ show('Your message did not send. Please try again, or email ' + EMAIL + ' directly.'); b.disabled = false; b.textContent = 'Try again'; });
    });
  });
})();
</script>'''


def form_js():
    j = lambda v: json.dumps(v).replace('</', '<\\/')
    return FORM_JS % (j(A.get('formspree_id') or ''), j(A['email']), j(A['name']), j(html.unescape(SMS)))


EXTRA_CSS = '''<style>
.contact .wrap{display:grid;grid-template-columns:.8fr 1.2fr;gap:56px;text-align:left;align-items:start}
.contact .direct{font-size:15px;line-height:1.8}.contact .direct a{color:var(--navy);border-bottom:1px solid var(--gold)}
.card{background:#fff;border:1px solid var(--line);padding:30px;box-shadow:0 20px 50px rgba(0,35,73,.08)}
form.leadform{display:grid;gap:14px}.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.leadform label{display:grid;gap:6px;font-size:13px;font-weight:600;color:var(--ink)}
.leadform input,.leadform select,.leadform textarea{font:inherit;font-weight:400;font-size:15px;padding:11px 12px;border:1px solid #cfd6df;background:#fff;color:var(--ink);border-radius:0;width:100%}
.leadform .cons{display:flex;gap:10px;font-weight:400;font-size:13.5px;line-height:1.5}.leadform .cons input{width:18px;height:18px;flex:none;margin-top:2px;accent-color:var(--navy);padding:0}
.leadform .priv{font-size:12.5px;color:var(--muted);margin:0}.leadform .ferr{color:#b0412e;font-size:14px;margin:0}
.leadform button{justify-self:start;cursor:pointer;font-family:var(--sans)}.leadform button:disabled{opacity:.6}
.fdone{font-size:16px;line-height:1.6}.fdone b{display:block;font:400 26px var(--serif);color:var(--navy);margin-bottom:6px}
footer a{color:inherit;border-bottom:1px solid rgba(233,207,143,.4)}
.tile{color:#fff}
.leadform .times label{display:flex;flex-direction:row;align-items:center;gap:8px;font-weight:400;font-size:14px}.leadform .times input{width:auto;padding:0}
.contact h2{font-size:38px}
@media(max-width:760px){.contact .wrap{grid-template-columns:1fr;gap:28px}.row2{grid-template-columns:1fr}.card{padding:22px}}
</style>'''


def fill(t, pfx, purpose, extra=''):
    t = t.replace('{{SITE}}', SITE).replace('{{EMAIL}}', esc(A['email']))
    c = consent(purpose).replace('{EXTRA}', extra)
    t = t.replace('{{CONSENT}}', c).replace('{{CONSENT_VALUE}}', c)
    t = t.replace('{{FOOTER}}', footer(pfx)).replace('{{FORMJS}}', form_js())
    return t.replace('</head>', EXTRA_CSS + '</head>', 1)


if __name__ == '__main__':
    home = open(os.path.join(HERE, 'site_home.html')).read().replace('{{TILES}}', tiles())
    open(os.path.join(HERE, 'index.html'), 'w').write(fill(home, '', 'about my home search'))
    val = open(os.path.join(HERE, 'site_value.html')).read()
    os.makedirs(os.path.join(HERE, 'home-value'), exist_ok=True)
    open(os.path.join(HERE, 'home-value', 'index.html'), 'w').write(
        fill(val, '../', 'to schedule a home value consultation', ' A consultation provides a broker\'s opinion of value, not an appraisal.'))
    left = [m for f in ('index.html', 'home-value/index.html') for m in re.findall(r'\{\{[A-Z_]+\}\}', open(os.path.join(HERE, f)).read())]
    assert not left, left
    print('wrote index.html and home-value/index.html')
