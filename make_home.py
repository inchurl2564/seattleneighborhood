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
            from photos import photo_for, make_card_copy
            ph = photo_for(p)
            if ph:   # a neighborhood photo replaces the map on its tile
                make_card_copy(ph['file'])
                svg = (f'<img src="img/card/{esc(ph["file"])}" alt="{esc(p["name"])}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block">'
                       f'<span class="tcredit">Photo: {esc(ph["by"])}, {esc(ph["lic"])}</span>')
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
.tcredit{position:absolute;right:0;top:0;font-size:9.5px;line-height:1.4;color:#fff;background:rgba(0,0,0,.45);padding:1px 6px;z-index:2;letter-spacing:0;text-transform:none}
.phonebar{border-bottom:1px solid rgba(255,255,255,.18);font-size:12px;letter-spacing:.08em}
.phonebar .wrap{display:flex!important;justify-content:flex-end;gap:10px;padding-top:7px!important;padding-bottom:7px!important}
.phonebar a{color:inherit;opacity:.92}.phonebar a:hover{color:#e9cf8f}.phonebar span{opacity:.5}
.hero2 .wrap{padding-top:180px}
@media(max-width:760px){.phonebar{font-size:12.5px;background:#001a38}.phonebar .wrap{justify-content:center;padding-top:9px!important;padding-bottom:9px!important}.phonebar a{padding:4px 2px}}
.leadform .times label{display:flex;flex-direction:row;align-items:center;gap:8px;font-weight:400;font-size:14px}.leadform .times input{width:auto;padding:0}
.contact h2{font-size:38px}
.menubtn,.readmore,.quick,.swipehint,.guides-below{display:none}
@media(max-width:760px){
 /* menu */
 .top .wrap{flex-wrap:wrap;padding-top:14px;padding-bottom:14px}
 .top{position:relative!important;background:#002349}
 .top .wrap{flex-wrap:nowrap}.top.open .wrap{flex-wrap:wrap}
 .brand{min-width:0}
 .menubtn{display:block;font:600 11px var(--sans);letter-spacing:.16em;text-transform:uppercase;color:inherit;background:transparent;border:1px solid currentColor;padding:11px 14px;min-height:44px;cursor:pointer}
 nav a.cta{display:none}
 .top.open nav{display:flex;flex-direction:column;align-items:stretch;gap:0;width:100%;margin-top:12px;background:#002349;padding:6px 0}
 .top.open nav a,.top.open nav a.cta{display:block;padding:14px 18px;border:0;font-size:13px;color:#fff}
 .top.open{background:#002349}
 /* hero: shorter */
 .hero2 .wrap{padding-top:30px;padding-bottom:28px;gap:22px}.hero2{min-height:0}
 .hero2 h1{font-size:31px}.hero2 .lead{font-size:15px;margin-bottom:18px}
 .who{display:none}
 .hero2 .actions .btn{padding:13px 16px}
 .nmside{padding:20px}.nmside h2{font-size:26px}.nmside p{font-size:14px;margin-bottom:12px}.nmside img{display:none}.nmside small{display:none}
 .hero2 .credit{font-size:9px}
 /* sections: less padding */
 .nbhd,.about,.services,.hv,.contact{padding:44px 0!important}
 .head{margin-bottom:18px}.head h2,.about h2,.hv h2,.contact h2{font-size:27px!important}
 /* neighborhoods and services: swipe sideways instead of scrolling down */
 .nbhd .grid,.services .grid{display:grid;grid-auto-flow:column;grid-template-columns:none;grid-auto-columns:78%;overflow-x:auto;scroll-snap-type:x mandatory;gap:12px;margin:0 -18px;padding:0 18px 6px;-webkit-overflow-scrolling:touch}
 .nbhd .grid>*,.services .grid>*{scroll-snap-align:start}
 .tile.maptile{aspect-ratio:auto;display:flex;flex-direction:column;padding:0;background:#fff;border:1px solid var(--line);color:var(--ink)}
 .tile.maptile::before{display:none}
 .tile.maptile .tmap{position:relative;inset:auto;display:block;aspect-ratio:16/10;overflow:hidden;border-bottom:3px solid var(--gold)}
 .tile.maptile>div{padding:12px 14px 14px}
 .tile.maptile h3{color:var(--navy);font-size:21px}.tile.maptile small{color:var(--muted);opacity:1;margin-top:4px;line-height:1.5}
 .services .card{padding:20px}.services h3{font-size:21px}.services p{font-size:14.5px}
 .swipehint{display:block;font-size:12px;color:var(--muted);margin-top:8px}
 .nbhd .head>a{display:none!important}
 .guides-below{display:inline-block;margin-top:18px;padding:10px 0;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--navy);border-bottom:1px solid var(--gold)}
 /* about: photo beside the heading, second paragraph behind Read more */
 .about .wrap{grid-template-columns:1fr!important;gap:18px!important}
 .photo-real{max-width:150px!important}.photo-real::after{display:none}
 .about .more{display:none}.about.expanded .more{display:block}
 .readmore{display:inline-block;background:none;border:0;color:#e9cf8f;font:600 12px var(--sans);letter-spacing:.14em;text-transform:uppercase;padding:10px 0;margin:0 0 14px;cursor:pointer}
 .stats{display:grid!important;grid-template-columns:repeat(3,1fr);gap:10px!important;margin:6px 0 20px!important}.stats b{font-size:22px!important}.stats span{font-size:9.5px!important;letter-spacing:.08em!important}
 /* home value: drop the side card */
 .hvcard{display:none}.hv .wrap{gap:0!important}
 /* contact: one-tap buttons first, form on request */
 .contact .wrap{grid-template-columns:1fr;gap:18px}
 .contact .direct{display:none}
 .quick{display:grid;grid-template-columns:1fr 1fr;gap:10px}.quick .btn{text-align:center;padding:14px 8px;min-height:48px;cursor:pointer;font-family:var(--sans)}
 .contact form.leadform{display:none}.contact.formopen form.leadform{display:grid}.contact.formopen .quick{display:none}
 .row2{grid-template-columns:1fr}.card{padding:20px}
 /* bigger tap targets */
 .leadform .cons input{width:24px;height:24px}
 .services .card a,.head a{display:inline-block;padding:10px 0}
 footer a{display:inline-block;padding:6px 0}
 footer .wrap{gap:22px}
}


@media (max-width:700px){
 .citybar,.phonebar{background:#001a38!important;border-bottom:1px solid rgba(255,255,255,.18)!important;padding:0!important;margin-bottom:0;text-transform:none!important;line-height:1.2!important}
 .citybar .cb-l{display:none!important}
 .citybar .cb-p,.phonebar .wrap{display:flex!important;justify-content:center!important;align-items:center;flex-wrap:nowrap!important;gap:0!important;margin:0!important;padding:0 4px!important;font-size:0;overflow:hidden}
 .citybar .cb-p a,.phonebar .wrap a{display:inline-flex!important;align-items:center;min-height:44px;padding:0 6px!important;white-space:nowrap;font:400 clamp(10px,3.3vw,12.5px) -apple-system,BlinkMacSystemFont,system-ui,"Segoe UI",Roboto,sans-serif!important;letter-spacing:.05em!important;color:#fff!important;opacity:.92!important;text-decoration:none;border:0!important}
 .citybar .cb-p a+a::before,.phonebar .wrap a+span+a::before{content:"·";opacity:.5;margin:0 12px 0 0}
 .phonebar .wrap span{display:none}
}

.brand .l2{display:inline!important;margin:0!important}
@media (max-width:700px){.brand .l2{display:block!important;margin-top:3px!important}.brand{margin-right:20px;min-width:0}.menubtn{flex:none;margin-left:auto}}

.brand .y2{display:inline!important;font:inherit!important;letter-spacing:inherit!important;text-transform:inherit!important;opacity:1!important;margin:0!important;color:inherit!important}
@media (max-width:700px){.brand .y2{display:block!important;margin-top:2px!important}}
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
