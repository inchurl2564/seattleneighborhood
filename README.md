# Seattle Neighborhood Match

A free tool that helps home buyers find the right neighborhood in Seattle, Bellevue, Mercer Island,
Kirkland, Redmond, Issaquah and Sammamish. Buyers answer a few questions (or use sliders) about what
matters to them, set must-haves like budget and distance to schools or work, and get 155 neighborhoods
ranked for them, with a map, plain-language explanations, and side-by-side comparisons.

Everything is built from public data. The site is a single self-contained web page (`index.html`):
no server, no accounts, and nothing a visitor enters leaves their browser.

## How it works

1. **Priorities** – a short interview (or sliders) sets how much each factor matters: school quality,
   low crime, walkability, commute to work, public transit, hospitals, errands and dining, parks and
   trails, gyms and studios, golf, library, home prices and household income.
2. **Filters** – hard limits: budget, minimum school quality, maximum crime, distances to schools,
   transit, stores, parks and more, and which cities to include.
3. **Results** – a ranked list and map; each neighborhood has its own page with a summary of why it
   matches, details by topic, nearby places on the map, and ranks against all 155 neighborhoods.

Each factor is scored 0–100 as a percentile across all neighborhoods; the match score is the weighted
average using the visitor's slider settings.

## Files

| File | What it is |
|---|---|
| `index.html`, `home-value/` | Rachel's home page and home value consultation page, built by `make_home.py` from `site_home.html` and `site_value.html`. |
| `match/` | Neighborhood Match, built by `make_page.py` from `template.html`. |
| `template.html` | The page without data. Edit this for design or feature changes. |
| `data.json` | The combined neighborhood data the page uses. |
| `build.py` | Combines the downloaded public data into `data.json`. |
| `fetch_data.sh`, `fetch_extra.py`, `arcfetch.py` | Download every public dataset into `raw/`. |
| `make_page.py` | Puts `data.json` into `template.html` and writes `match/index.html`. |
| `privacy_text.py` | Wording of the Privacy Policy page (`privacy/`). Update it if the site starts collecting or sharing anything new. |
| `make_home.py` | Writes the home page (with the six featured neighborhoods, the two highest-priced in Bellevue, Kirkland and Sammamish) and the home value page. |
| `config.json` | Site address and agent details (name, brokerage, email, profile link, optional Formspree form ID) used by the lead forms. |
| `make_guides.py` | Writes a guide page per neighborhood (`neighborhoods/<name>-<city>/`), the guide index and `sitemap.xml`. |
| `fetch_wiki.py`, `get_photos.py` | Find each neighborhood's Wikipedia intro and lead photo (`wiki.json`), and download the photos into `img/`. |
| `photos.py` | Decides which photo and intro each neighborhood shows (license, review status), and makes the small card copies in `img/card/`. |
| `img/` | Neighborhood photos from Wikimedia Commons, each credited where it appears. |
| `neighborhoods/` | The generated neighborhood guide pages. |
| `sitemap.xml` | List of all pages for search engines. |

## Refreshing the data

```bash
pip install pandas geopandas shapely pyproj pyogrio pillow
bash fetch_data.sh        # downloads about 400 MB into raw/ (not committed)
python3 build.py          # writes data.json
python3 fetch_wiki.py     # optional: Wikipedia intros and photo credits (wiki.json)
python3 get_photos.py     # optional: downloads approved photos into img/
python3 make_page.py      # writes index.html
python3 make_guides.py    # writes the neighborhood guide pages and sitemap.xml
python3 make_home.py      # writes the home page and home value page
```

Move the date windows in the scripts forward when refreshing (crime from Nov 2025, FBI year 2025,
OSPI 2024-25, the transit service day, and the Assessor sales window).

## Photos

Photos come from Wikimedia Commons and are used only when their license allows commercial use with credit
(CC BY, CC BY-SA, CC0 or public domain). Each one is credited (author, license, link) on the card and page
where it appears. To remove a photo, set `"photo_vetoed": true` on its entry in `wiki.json`; to hold one for
review, set `"photo_hold": true`. Then rerun `make_page.py` and `make_guides.py`.

## Lead forms

Every neighborhood page (in the app and the guides) and the Results page have a contact form for the agent
named in `config.json`. With `formspree_id` empty, the form opens the visitor's email app with a ready-to-send
message that includes their budget, priorities, top matches and saved favorites. To receive submissions
directly instead, create a form at formspree.io, put its ID in `config.json`, and rerun `make_page.py` and
`make_guides.py`.

## Data sources

Zillow Research (home values, listings, days to pending); King County Assessor (recorded sales and
parcels); Washington OSPI Report Card (school test scores); NCES EDGE (school locations); Seattle and
Bellevue police open data and the FBI Crime Data Explorer (crime); US Census Bureau American Community
Survey and TIGER/Line (income, education, boundaries, water and highways); US EPA National Walkability
Index; King County Metro and Sound Transit GTFS (transit); King County GIS (hospitals, clinics,
colleges, shopping centers, libraries, parks, trails, golf courses); Seattle, Bellevue, Kirkland,
Redmond and Issaquah GIS (neighborhood boundaries); and © OpenStreetMap contributors, available under
the Open Database License (stores, restaurants, pharmacies, gyms, spas and studios).

The map uses [Leaflet](https://leafletjs.com) 1.9.4 (BSD 2-Clause license), built into the page.

## Important notes

- **For research only.** Not real estate, legal, financial or tax advice. Data can be incomplete or
  out of date; verify anything important with the original source.
- **Fair housing.** Rankings never use race, color, religion, national origin, sex, disability or
  familial status. Education and age figures are shown for context only and are never used to rank
  or filter.
- **Known limits.** Crime for Kirkland, Redmond, Issaquah, Sammamish and Mercer Island is a citywide
  rate. Homes-for-sale counts are estimates split from ZIP-level data. Distances are straight-line
  from each neighborhood's center. Nearby schools are not necessarily the assigned schools.
