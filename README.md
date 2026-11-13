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
| `index.html` | The finished site. GitHub Pages serves this. |
| `template.html` | The page without data. Edit this for design or feature changes. |
| `data.json` | The combined neighborhood data the page uses. |
| `build.py` | Combines the downloaded public data into `data.json`. |
| `fetch_data.sh`, `fetch_extra.py`, `arcfetch.py` | Download every public dataset into `raw/`. |
| `make_page.py` | Puts `data.json` into `template.html` and writes `index.html`. |
| `make_guides.py` | Writes a guide page per neighborhood (`neighborhoods/<name>-<city>/`), the guide index and `sitemap.xml`. |
| `neighborhoods/` | The generated neighborhood guide pages. |
| `sitemap.xml` | List of all pages for search engines. |

## Refreshing the data

```bash
pip install pandas geopandas shapely pyproj pyogrio
bash fetch_data.sh        # downloads about 400 MB into raw/ (not committed)
python3 build.py          # writes data.json
python3 make_page.py      # writes index.html
python3 make_guides.py    # writes the neighborhood guide pages and sitemap.xml
```

Move the date windows in the scripts forward when refreshing (crime from Nov 2025, FBI year 2025,
OSPI 2024-25, the transit service day, and the Assessor sales window).

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
