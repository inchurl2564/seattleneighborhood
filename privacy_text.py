"""Plain-language privacy policy for the site. Edit the wording here, then run make_home.py.

Describes what the site actually does (checked Nov 2026): no cookies, no ads, no analytics or tracking;
Neighborhood Match answers kept only in the visitor's browser (localStorage key "nm-state-v3");
forms delivered by Formspree; site hosted on GitHub Pages; Neighborhood Match loads a font from Google Fonts.
If any of this changes (for example, adding visitor counts or a CRM), update this text.
"""

EFFECTIVE = 'November 16, 2026'

BODY = """
<p class="lede">This policy explains what information this website collects, how it's used, and the choices you have. It covers this site, including Neighborhood Match, the neighborhood guides and the What's My Home Worth? page.</p>

<h2>Who we are</h2>
<p>This site is operated by Rachel Yo, a real estate broker with {brokerage}, 15 Lake Street, Suite 200, Kirkland, WA 98033. In this policy, "I," "me" and "Rachel" mean Rachel Yo.</p>

<h2>What you share with me</h2>
<p>I only collect personal information when you choose to send it through a form on this site: a contact form, an "Ask Rachel" form, or the home value consultation request. Depending on the form, this can include:</p>
<ul>
<li>your name, email address and, if you provide them, your mobile phone number and home address</li>
<li>details you give about your home or search, such as home type, timeline, best times for a visit and your message</li>
<li>if you send your Neighborhood Match results, the budget, priorities, matches and saved neighborhoods listed under "What's included"</li>
<li>whether you agreed to be contacted and to receive text messages, the wording you agreed to, and the time you sent the form</li>
</ul>

<h2>How I use it</h2>
<p>I use this information only to respond to your request: to answer your questions, schedule and prepare a home value consultation, send homes and information related to your search, and keep a record of your consent to be contacted. I don't sell, rent or trade your information.</p>

<h2>Text messages</h2>
<p>I only text you if you checked the box agreeing to receive texts and gave a mobile number. Message frequency varies, and message and data rates may apply. Reply STOP at any time to opt out, or HELP for help. Agreeing to texts is never required to work with me. <b>Your mobile number and texting consent are never shared with or sold to anyone for their marketing.</b></p>

<h2>Neighborhood Match stays on your device</h2>
<p>Your Neighborhood Match answers, priorities, filters, matches and saved neighborhoods are stored only in your own web browser on your device, so they're there when you come back. They are not sent to me or anyone else unless you choose to send them with a form. To clear them, use "Start over" in Neighborhood Match or clear your browser's site data.</p>

<h2>Cookies, ads and tracking</h2>
<p>This site doesn't use cookies, advertising, analytics or tracking tools, and it doesn't build a profile of your visits.</p>

<h2>Service providers</h2>
<p>A few outside services help run the site. Each receives only what it needs:</p>
<ul>
<li><b>Formspree</b> delivers form submissions to my email. It receives the information you enter when you press Send.</li>
<li><b>GitHub Pages</b> hosts the website. Like any web host, it may record basic technical information such as your IP address and browser type to deliver and secure the site.</li>
<li><b>Google Fonts</b> supplies a typeface used on the Neighborhood Match page, so your browser requests it from Google, which receives your IP address.</li>
<li>Your <b>email app</b> or <b>phone</b> handles messages if you choose to email, call or text me directly.</li>
</ul>
<p>Links to other sites, such as photo credits, data sources and my Sotheby's profile, go to sites with their own privacy policies.</p>

<h2>Sharing</h2>
<p>I may share your information with {brokerage} as needed to serve you and meet brokerage record-keeping requirements, with professionals involved in your transaction when you ask me to, or when required by law. I don't share it with anyone for their own marketing.</p>

<h2>How long I keep it</h2>
<p>I keep your information only as long as needed to help you and to meet legal and brokerage record-keeping requirements.</p>

<h2>Your choices</h2>
<p>You can ask me at any time to see, correct or delete the information you've sent, or to stop contacting you. Email <a href="mailto:{email}">{email}</a> or call <a href="tel:+14256585300">425.658.5300</a>, and I'll respond promptly. Depending on where you live, you may have additional rights under your state's privacy laws, and I'll honor those requests.</p>

<h2>Children</h2>
<p>This site is intended for adults and isn't directed to children under 13. I don't knowingly collect information from children.</p>

<h2>Security</h2>
<p>The site uses a secure (HTTPS) connection, and form submissions are sent securely. No website or email service is perfectly secure, so please don't send sensitive financial information through the forms.</p>

<h2>Changes to this policy</h2>
<p>If I change how the site handles information, I'll update this page and its effective date.</p>

<h2>Contact</h2>
<p>Rachel Yo, Broker, {brokerage}<br>15 Lake Street, Suite 200, Kirkland, WA 98033<br><a href="mailto:{email}">{email}</a> · <a href="tel:+14256585300">Office 425.658.5300</a></p>
"""
