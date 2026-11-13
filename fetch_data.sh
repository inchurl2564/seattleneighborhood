#!/usr/bin/env bash
# Downloads every public dataset the build uses into ./raw  (run from this folder).
# Needs: curl, python3 with pandas/geopandas. Some sources are large (Assessor sales ~150 MB, Zillow ~120 MB, ZCTA ~65 MB).
set -e
mkdir -p raw && cd raw
B=https://www2.census.gov/geo/tiger
curl -sSLo tracts.zip $B/GENZ2023/shp/cb_2023_53_tract_500k.zip
curl -sSLo places.zip $B/GENZ2023/shp/cb_2023_53_place_500k.zip
curl -sSLo bg.zip     $B/GENZ2023/shp/cb_2023_53_bg_500k.zip
curl -sSLo prisec.zip $B/TIGER2023/PRISECROADS/tl_2023_53_prisecroads.zip
curl -sSLo water.zip  $B/TIGER2023/AREAWATER/tl_2023_53033_areawater.zip
curl -sSLo zcta.zip   $B/GENZ2020/shp/cb_2020_us_zcta520_500k.zip
Y=2024; echo $Y > acs_year   # ACS 5-year summary files (no API key needed)
for t in b19013 b25077 b01003 b01002 b15003 b11005 b25003 b08301; do
  curl -sSL https://www2.census.gov/programs-surveys/acs/summary_file/$Y/table-based-SF/data/5YRData/acsdt5y$Y-$t.dat | awk -F'|' 'NR==1 || $1 ~ /^1400000US53033/' > acs_$t.dat; done
curl -sSL https://www2.census.gov/programs-surveys/acs/summary_file/$Y/table-based-SF/data/5YRData/acsdt5y$Y-b01003.dat | awk -F'|' 'NR==1 || $1 ~ /^1500000US53033/' > acs_bg_b01003.dat
curl -sSLo metro.zip https://metro.kingcounty.gov/GTFS/google_transit.zip
curl -sSLo st.zip https://www.soundtransit.org/GTFS-rail/40_gtfs.zip
Z=https://files.zillowstatic.com/research/public_csvs
curl -sSLo zhvi.csv $Z/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv
curl -sSLo z_Zip_invt_fs_uc_sfrcondo_sm_month.csv $Z/invt_fs/Zip_invt_fs_uc_sfrcondo_sm_month.csv
curl -sSLo z_Zip_new_listings_uc_sfrcondo_sm_month.csv $Z/new_listings/Zip_new_listings_uc_sfrcondo_sm_month.csv
curl -sSLo z_Zip_med_doz_pending_uc_sfrcondo_sm_month.csv $Z/med_doz_pending/Zip_med_doz_pending_uc_sfrcondo_sm_month.csv
curl -sSLo z_City_med_doz_pending_uc_sfrcondo_sm_month.csv $Z/med_doz_pending/City_med_doz_pending_uc_sfrcondo_sm_month.csv
curl -sSLo schools.zip https://nces.ed.gov/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_2324.zip && unzip -oq schools.zip 'EDGE_GEOCODE_PUBLICSCH_2324/EDGE_GEOCODE_PUBLICSCH_2324.TXT'
O="https://data.wa.gov/resource/qh4i-zmju.csv"   # OSPI Report Card Assessment 2024-25
curl -sSLo ospi.csv "$O?\$select=districtcode,districtname,schoolcode,schoolname,gradelevel,testsubject,count_of_students_tested,count_consistent_grade_level&\$where=county='King'%20AND%20organizationlevel='School'%20AND%20studentgroup='All%20Students'%20AND%20gradelevel='All%20Grades'&\$limit=50000"
curl -sSLo ospi_grades.csv "$O?\$select=districtcode,districtname,schoolcode,schoolname,gradelevel,testsubject,count_of_students_tested,count_consistent_grade_level&\$where=county='King'%20AND%20organizationlevel='School'%20AND%20studentgroup='All%20Students'%20AND%20gradelevel%20in('3','4','5','6','7','8','10','11','03','04','05','06','07','08')&\$limit=100000"
curl -sSLo sea_crime.csv "https://data.seattle.gov/resource/tazs-3rd5.csv?\$select=offense_date,nibrs_crime_against_category,offense_category,offense_sub_category,latitude,longitude&\$where=offense_date>='2025-11-01T00:00:00'&\$limit=500000"
curl -sSLo nhoods.geojson "https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/nma_nhoods_sub/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
KC=https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services
POI="$KC/COMMON_INTEREST_POINT_731/FeatureServer/0/query?outFields=NAME,ADDRESS,CODE&outSR=4326&f=geojson&where="
curl -sSLo clinics.geojson "${POI}CODE+IN+(330,340)"; curl -sSLo poi_nh.geojson "${POI}CODE%3D90"
curl -sSLo golf_kc.geojson "${POI}CODE%3D300"; curl -sSLo colleges.geojson "${POI}CODE%3D663"; curl -sSLo shopping.geojson "${POI}CODE%3D690"; curl -sSLo libraries.geojson "${POI}CODE%3D390"
curl -sSLo hosp.geojson "$KC/HOSPITALS_POINT_99/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
curl -sSLo kc_sales.zip "https://aqua.kingcounty.gov/extranet/assessor/Real%20Property%20Sales.zip"
cd .. && python3 fetch_extra.py   # ArcGIS layers, FBI rates, OSM, sales geocoding
