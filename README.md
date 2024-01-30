# Parcel ATM

_Parcel ATM_ is an art project and website conceived for [Data through Design 2024](https://datathroughdesign.com/). The installation will allow visitors to query [22 years of NYC MapPLUTO data](https://www.nyc.gov/site/planning/data-maps/open-data/bytes-archive.page). This repo contains the source code for the ATM's interface.

## To do

### ELT

- [x] Extract all years of MapPLUTO data
- [x] Unzip and union shapefiles
- [x] Drop null geoms
- [x] Copy to S3

### EDA

- [ ] Investigate change over time in layers

### Frontend

- [x] Load initial `.pmtiles` with land use
- [x] Render layers
- [x] First draft / key UI elements: legend, year selected, title, zoom level
- [x] Initial key controls
- [x] Crosshair thing
- [ ] Allow for higher zoom level
- [ ] Add additional layers to `.pmtiles`, esp. assessed value, buildfar, zoning1, yearbuilt, yearalter1, yearalter2, numfloors
- [ ] Add feature to toggle layers
- [ ] Print CSS to handle receipt printing
- [ ] Two set-ups: kiosk and not
- [ ] Add contextual layers
- [ ] (Optional) Variable styling by web-era
- [x] Do a little reasearch into old mapping interfaces e.g. MapQuest
- [ ] Implement inital UI w/ oldschool mapping UI elements, e.g.
- [ ] Custom vintage looking icons and logo
- [ ] Crosshair as grainy icon / info pin
- [ ] Variable layer change by zoom level (more time for bigger zoom levels)

### Backend

- [x] Stand-up Django app
- [x] Create models for each layer
- [x] Load all data to postgres
- [x] Deploy backend
- [x] Deploy DB
- [x] Single endpoint fetching all rows from a single location
- [ ] Record location of queried parcels
- [ ] Add summary view of data across years
- [ ] Stacked axo view of parcels?

### ATM

- [x] Build custom numpad with rotary encoder
- [x] Figure out screen
- [x] Figure out thermal printer
- [x] First draft of ATM plans
- [ ] Carpentry classes
- [ ] Detailed ATM plans
- [ ] Build ATM
