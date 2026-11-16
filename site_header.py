"""The site header (phone numbers, Rachel Yo, brokerage line, menu) shared by every page that isn't the home page.

It reproduces the home page's header exactly (solid navy, like the What's My Home Worth? page). Class names start
with "shd" so they never collide with a page's own styles.
"""

SERIF = 'Charter,"Bitstream Charter","Iowan Old Style","Sitka Text",Cambria,Georgia,serif'
SANS = 'Inter,"Public Sans",system-ui,sans-serif'
PHONE_FONT = '-apple-system,BlinkMacSystemFont,system-ui,"Segoe UI",Roboto,sans-serif'

CSS = f"""
/* ===== shared site header (matches the home page) ===== */
header.shd{{position:relative;z-index:5;display:block;background:#002349;color:#fff;margin:0 calc(50% - 50vw);padding:0;border:0;font:16px/1.6 {SANS};text-align:left;box-sizing:border-box}}
header.shd *{{box-sizing:border-box}}
header.shd a{{color:#fff;text-decoration:none}}
.shd-in{{max-width:1180px;margin:0 auto;padding:0 32px}}
.shd-bar{{border-bottom:1px solid rgba(255,255,255,.18);font-size:12px;letter-spacing:.08em}}
.shd-bar .shd-in{{display:flex;justify-content:flex-end;gap:10px;padding-top:7px;padding-bottom:7px}}
.shd-bar a{{opacity:.92}}.shd-bar a:hover{{color:#e9cf8f}}.shd-bar span{{opacity:.5}}
.shd-main{{display:flex;justify-content:space-between;align-items:center;padding-top:22px;padding-bottom:22px}}
.shd-brand{{display:block}}
.shd-brand b{{display:block;font:400 26px/1 {SERIF};letter-spacing:.24em;text-transform:uppercase;color:#fff}}
.shd-brand>span{{display:block;font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;opacity:.85;margin-top:8px;font-weight:400}}
.shd-brand .l2,.shd-brand .y2{{display:inline;margin:0}}
.shd-nav{{display:flex;gap:22px;align-items:center;font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;font-weight:400}}
.shd-nav a{{white-space:nowrap;margin:0;font-weight:400;letter-spacing:inherit}}
.shd-nav a.cta{{display:inline-block;margin:0;gap:0;border:1px solid #fff;padding:10px 16px;background:none;font-weight:400}}
.shd-nav a.new{{color:#e9cf8f}}
.shd-menu{{display:none}}
@media(max-width:1100px){{.shd-nav a:not(.cta):not(.new){{display:none}}}}
@media(max-width:760px){{
 .shd-in{{padding:0 18px}}
 .shd-main{{flex-wrap:nowrap;padding-top:14px;padding-bottom:14px}}
 header.shd.open .shd-main{{flex-wrap:wrap}}
 .shd-brand{{margin-right:20px;min-width:0}}
 .shd-brand b{{font-size:19px}}.shd-brand>span{{font-size:8.5px;letter-spacing:.12em}}
 .shd-nav,.shd-nav a.cta{{display:none}}
 .shd-menu{{display:block;flex:none;margin-left:auto;font:600 11px {SANS};letter-spacing:.16em;text-transform:uppercase;color:#fff;background:transparent;border:1px solid #fff;border-radius:0;padding:11px 14px;min-height:44px;cursor:pointer}}
 header.shd.open .shd-nav{{display:flex;flex-direction:column;align-items:stretch;gap:0;width:100%;margin-top:12px;padding:6px 0}}
 header.shd.open .shd-nav a{{display:block!important;padding:14px 18px;border:0;font-size:13px;color:#fff}}
}}
@media(max-width:700px){{
 .shd-brand .l2{{display:block;margin-top:3px}}
 .shd-brand .y2{{display:block;margin-top:2px}}
 .shd-bar{{background:#001a38;padding:0;line-height:1.2}}
 .shd-bar .shd-in{{justify-content:center;flex-wrap:nowrap;gap:0;padding:0 4px;font-size:0;overflow:hidden}}
 .shd-bar a{{display:inline-flex;align-items:center;min-height:44px;padding:0 6px;white-space:nowrap;font:400 clamp(10px,3.3vw,12.5px) {PHONE_FONT};letter-spacing:.05em;color:#fff;opacity:.92}}
 .shd-bar a+span+a::before{{content:"·";opacity:.5;margin:0 12px 0 0}}
 .shd-bar span{{display:none}}
}}
"""

# shrinks the phone numbers just enough to stay on one line on very narrow screens
FIT = ('<script>(function(){function fit(){document.querySelectorAll(".shd-bar .shd-in").forEach(function(el){'
       'var as=el.querySelectorAll("a[href^=\'tel:\']");as.forEach(function(a){a.style.removeProperty("font-size")});'
       'if(innerWidth>700)return;var s=parseFloat(getComputedStyle(as[0]).fontSize)||12.5;'
       'while(el.scrollWidth>el.clientWidth+1&&s>8){s-=.25;as.forEach(function(a){a.style.setProperty("font-size",s+"px","important")})}})}'
       'fit();addEventListener("resize",fit);addEventListener("load",fit);if(document.fonts)document.fonts.ready.then(fit)})()</script>')

MENU_JS = ("var h=this.closest('header');var o=h.classList.toggle('open');"
           "this.setAttribute('aria-expanded',o);this.textContent=o?'Close':'Menu'")


def html(pfx, active=''):
    """Header markup. pfx is the path back to the site root ('../' or '../../'); active is 'match' or 'value'."""
    cls = lambda k: ' class="new" aria-current="page"' if k == active else ''
    return (f'<header class="shd"><div class="shd-bar"><div class="shd-in"><a href="tel:+15127971935">Mobile 512.797.1935</a><span>·</span>'
            f'<a href="tel:+14256585300">Office 425.658.5300</a></div></div>{FIT}'
            f'<div class="shd-in shd-main"><a class="shd-brand" href="{pfx}"><b>Rachel <span class="y2">Yo</span></b>'
            f'<span>Realogics Sotheby\'s <span class="l2">International Realty</span></span></a>'
            f'<button class="shd-menu" type="button" aria-expanded="false" onclick="{MENU_JS}">Menu</button>'
            f'<nav class="shd-nav" aria-label="Site"><a href="{pfx}match/"{cls("match")}>Neighborhood Match</a>'
            f'<a href="{pfx}home-value/"{cls("value")}>What\'s My Home Worth?</a><a href="{pfx}#about">About</a>'
            f'<a class="cta" href="{pfx}#contact">Let\'s talk</a></nav></div></header>')
