// Package catalog describes the normalized historical PLUTO datasets that the
// ELT pipeline (../elt) exports and syncs to Cloudflare R2.
//
// Core column names and types must stay in sync with elt/elt/schema.py.
package catalog

import "fmt"

// Column documents one column in a parcel dataset.
type Column struct {
	Name        string `json:"name"`
	Type        string `json:"type"`
	Description string `json:"description"`
	// Derived columns are computed by the ELT export rather than copied from
	// the source MapPLUTO shapefiles.
	Derived bool `json:"derived,omitempty"`
	// Codes maps coded values to their meaning, when the column is coded.
	Codes []Code `json:"codes,omitempty"`
}

// Code is one value of a coded column.
type Code struct {
	Value   string `json:"value"`
	Meaning string `json:"meaning"`
}

// Dataset describes one family of files in the bucket.
type Dataset struct {
	Name        string `json:"name"`
	Format      string `json:"format"`
	CRS         string `json:"crs"`
	PathPattern string `json:"path_pattern"`
	Description string `json:"description"`
}

// MinYear and MaxYear bound the MapPLUTO releases the pipeline ingests. The live
// manifest, when available, is authoritative for which years were uploaded.
const (
	MinYear = 2002
	MaxYear = 2025
)

// DefaultYears returns every year the pipeline is configured to export.
func DefaultYears() []int {
	years := make([]int, 0, MaxYear-MinYear+1)
	for y := MinYear; y <= MaxYear; y++ {
		years = append(years, y)
	}
	return years
}

var Datasets = []Dataset{
	{
		Name:        "core",
		Format:      "GeoParquet",
		CRS:         "EPSG:4326 (lon/lat)",
		PathPattern: "parquet/core/year={YYYY}/data.parquet",
		Description: "Normalized parcels for every year. Only columns that exist in all MapPLUTO releases, cast to one type per column, so every year can be queried together. Start here.",
	},
	{
		Name:        "full",
		Format:      "GeoParquet",
		CRS:         "EPSG:4326 (lon/lat)",
		PathPattern: "parquet/full/year={YYYY}/data.parquet",
		Description: "Every harmonized column for a single year with its source type. Column sets and types differ between years; query one year at a time, or use union_by_name = true and cast explicitly.",
	},
	{
		Name:        "fgb",
		Format:      "FlatGeobuf",
		CRS:         "EPSG:2263 (NY State Plane Long Island, US feet)",
		PathPattern: "fgb/pluto{YY}.fgb",
		Description: "All harmonized columns in the source projection with a spatial index. Good for bbox-filtered reads with ST_Read(..., spatial_filter_box := ...). This is what the Parcel ATM backend queries.",
	},
	{
		Name:        "pmtiles",
		Format:      "PMTiles vector tiles",
		CRS:         "EPSG:3857 tiles",
		PathPattern: "pmtiles/pluto{YY}_shp_wgs.pmtiles",
		Description: "Vector tiles for web maps with a subset of columns (landuse, zonedist1, assessland, assesstot, numfloors, yearbuilt, unitsres, bldgclass, yearalter1, builtfar). Not meant for DuckDB.",
	},
}

// DatasetByName returns the dataset with the given name.
func DatasetByName(name string) (Dataset, bool) {
	for _, d := range Datasets {
		if d.Name == name {
			return d, true
		}
	}
	return Dataset{}, false
}

// FileKey returns the bucket-relative key for a dataset file in a given year.
func FileKey(dataset string, year int) (string, error) {
	switch dataset {
	case "core", "full":
		return fmt.Sprintf("parquet/%s/year=%d/data.parquet", dataset, year), nil
	case "fgb":
		return fmt.Sprintf("fgb/pluto%02d.fgb", year%100), nil
	case "pmtiles":
		return fmt.Sprintf("pmtiles/pluto%02d_shp_wgs.pmtiles", year%100), nil
	}
	return "", fmt.Errorf("unknown dataset %q", dataset)
}

var Boroughs = []Code{
	{"1", "Manhattan (MN)"},
	{"2", "Bronx (BX)"},
	{"3", "Brooklyn (BK)"},
	{"4", "Queens (QN)"},
	{"5", "Staten Island (SI)"},
}

var LandUse = []Code{
	{"1", "One & Two Family Buildings"},
	{"2", "Multi-Family Walk-Up Buildings"},
	{"3", "Multi-Family Elevator Buildings"},
	{"4", "Mixed Residential & Commercial Buildings"},
	{"5", "Commercial & Office Buildings"},
	{"6", "Industrial & Manufacturing"},
	{"7", "Transportation & Utility"},
	{"8", "Public Facilities & Institutions"},
	{"9", "Open Space & Outdoor Recreation"},
	{"10", "Parking Facilities"},
	{"11", "Vacant Land"},
}

// BuildingClassCategories are the first letter of the DOF building class.
var BuildingClassCategories = []Code{
	{"A", "One family dwellings"},
	{"B", "Two family dwellings"},
	{"C", "Walk-up apartments"},
	{"D", "Elevator apartments"},
	{"E", "Warehouses"},
	{"F", "Factory & industrial buildings"},
	{"G", "Garages, gas stations & parking"},
	{"H", "Hotels"},
	{"I", "Hospitals & health facilities"},
	{"J", "Theatres"},
	{"K", "Store buildings"},
	{"L", "Loft buildings"},
	{"M", "Religious facilities"},
	{"N", "Asylums & homes"},
	{"O", "Office buildings"},
	{"P", "Places of public assembly & cultural facilities"},
	{"Q", "Outdoor recreation facilities"},
	{"R", "Condominiums"},
	{"S", "Residence, multiple use (mostly residential with stores/offices)"},
	{"T", "Transportation facilities"},
	{"U", "Utility bureau properties"},
	{"V", "Vacant land"},
	{"W", "Educational facilities"},
	{"Y", "Government / city department facilities"},
	{"Z", "Miscellaneous"},
}

var OwnerTypes = []Code{
	{"C", "City owned"},
	{"M", "Mixed city & private ownership"},
	{"O", "Other public (state, federal, authorities)"},
	{"P", "Private"},
	{"X", "Fully tax-exempt property (may be public or private)"},
	{"NULL", "Unknown; usually private"},
}

// CoreColumns lists the columns of the core dataset in file order.
var CoreColumns = []Column{
	{Name: "year", Type: "BIGINT", Derived: true, Description: "MapPLUTO release year (2002-2025). Also the hive partition key: filter on it to read only the files you need."},
	{Name: "bbl", Type: "BIGINT", Derived: true, Description: "Borough-Block-Lot as a 10 digit number: borocode * 1e9 + block * 1e4 + lot. The parcel identifier used across NYC datasets. Files are sorted by bbl. BBLs are not permanent: lots merge, split and get condo billing lots (lot 7501+) over time."},
	{Name: "borocode", Type: "SMALLINT", Description: "Borough code.", Codes: Boroughs},
	{Name: "borough", Type: "VARCHAR", Description: "Two letter borough abbreviation: MN, BX, BK, QN, SI."},
	{Name: "block", Type: "INTEGER", Description: "Tax block within the borough."},
	{Name: "lot", Type: "INTEGER", Description: "Tax lot within the block."},
	{Name: "address", Type: "VARCHAR", Description: "Street address of the tax lot (house number and street name, upper case)."},
	{Name: "zipcode", Type: "INTEGER", Description: "ZIP code."},
	{Name: "ownername", Type: "VARCHAR", Description: "Owner name from DOF records (upper case, free text; the same owner is often spelled several ways)."},
	{Name: "ownertype", Type: "VARCHAR", Description: "Type of ownership.", Codes: OwnerTypes},
	{Name: "landuse", Type: "SMALLINT", Description: "DCP land use category, derived from building class.", Codes: LandUse},
	{Name: "bldgclass", Type: "VARCHAR", Description: "DOF building class, e.g. 'A1', 'D4', 'R4'. The first letter is the broad category (see codes); use substring(bldgclass, 1, 1) to group.", Codes: BuildingClassCategories},
	{Name: "zonedist1", Type: "VARCHAR", Description: "Primary zoning district, e.g. 'R6', 'C4-2', 'M1-1', 'PARK'. Simplify with regexp_extract(zonedist1, '^[A-Za-z]+[0-9]*', 0) to get 'R6', 'C4', 'M1'."},
	{Name: "zonedist2", Type: "VARCHAR", Description: "Second zoning district when the lot is split by a zoning boundary."},
	{Name: "overlay1", Type: "VARCHAR", Description: "Commercial overlay, e.g. 'C1-2', 'C2-4'."},
	{Name: "overlay2", Type: "VARCHAR", Description: "Second commercial overlay."},
	{Name: "spdist1", Type: "VARCHAR", Description: "Special purpose district, e.g. 'MiD' (Midtown). Abbreviations vary between years."},
	{Name: "spdist2", Type: "VARCHAR", Description: "Second special purpose district."},
	{Name: "splitzone", Type: "VARCHAR", Description: "'Y' if the lot is divided by a zoning boundary, else 'N'."},
	{Name: "histdist", Type: "VARCHAR", Description: "Name of the historic district the lot is in, if any."},
	{Name: "landmark", Type: "VARCHAR", Description: "Name of the individual landmark on the lot, if any."},
	{Name: "lotarea", Type: "DOUBLE", Description: "Lot area in square feet."},
	{Name: "lotfront", Type: "DOUBLE", Description: "Lot frontage in feet."},
	{Name: "lotdepth", Type: "DOUBLE", Description: "Lot depth in feet."},
	{Name: "irrlotcode", Type: "VARCHAR", Description: "'Y' if the lot is irregularly shaped."},
	{Name: "bldgfront", Type: "DOUBLE", Description: "Frontage of the primary building in feet."},
	{Name: "bldgdepth", Type: "DOUBLE", Description: "Depth of the primary building in feet."},
	{Name: "numbldgs", Type: "INTEGER", Description: "Number of buildings on the lot."},
	{Name: "numfloors", Type: "DOUBLE", Description: "Number of floors in the tallest building (can be fractional)."},
	{Name: "unitsres", Type: "INTEGER", Description: "Number of residential units."},
	{Name: "unitstotal", Type: "INTEGER", Description: "Total units (residential + non-residential)."},
	{Name: "comarea", Type: "DOUBLE", Description: "Commercial floor area in square feet."},
	{Name: "resarea", Type: "DOUBLE", Description: "Residential floor area in square feet."},
	{Name: "builtfar", Type: "DOUBLE", Description: "Built floor area ratio: total building floor area / lot area. Renamed from 'far' in 2002-2003; values in those years are less reliable."},
	{Name: "yearbuilt", Type: "SMALLINT", Description: "Year construction of the building was completed. 0 means unknown; many values are estimates rounded to the decade."},
	{Name: "yearalter1", Type: "SMALLINT", Description: "Year of the most recent major alteration. 0 means none recorded. Renamed from 'yearalter' in 2002."},
	{Name: "yearalter2", Type: "SMALLINT", Description: "Year of the second most recent alteration. 0 means none."},
	{Name: "assessland", Type: "DOUBLE", Description: "DOF assessed land value in dollars (nominal, not inflation adjusted). Assessed value is a fraction of market value and the ratio differs by tax class."},
	{Name: "assesstot", Type: "DOUBLE", Description: "DOF total assessed value (land + improvements) in dollars, nominal."},
	{Name: "exempttot", Type: "DOUBLE", Description: "DOF total exempt value in dollars, nominal."},
	{Name: "areasource", Type: "VARCHAR", Description: "Source code for building area values."},
	{Name: "schooldist", Type: "SMALLINT", Description: "Community school district."},
	{Name: "policeprct", Type: "SMALLINT", Description: "Police precinct."},
	{Name: "firecomp", Type: "VARCHAR", Description: "Fire company, e.g. 'E001', 'L010'."},
	{Name: "xcoord", Type: "DOUBLE", Description: "X coordinate of the lot in EPSG:2263 (US feet), from source."},
	{Name: "ycoord", Type: "DOUBLE", Description: "Y coordinate of the lot in EPSG:2263 (US feet), from source."},
	{Name: "lon", Type: "DOUBLE", Derived: true, Description: "Longitude (WGS84) of the lot polygon centroid. Filter on lon/lat before spatial predicates: it lets DuckDB skip row groups without decoding geometries."},
	{Name: "lat", Type: "DOUBLE", Derived: true, Description: "Latitude (WGS84) of the lot polygon centroid."},
	{Name: "geom", Type: "GEOMETRY", Derived: true, Description: "Lot polygon in EPSG:4326 with lon/lat axis order. Requires the spatial extension. For areas or distances in feet use ST_Transform(geom, 'EPSG:4326', 'EPSG:2263', always_xy := true)."},
}

// CoreColumn returns the documented core column with the given name.
func CoreColumn(name string) (Column, bool) {
	for _, c := range CoreColumns {
		if c.Name == name {
			return c, true
		}
	}
	return Column{}, false
}

// Caveats are things that commonly trip up analysis of the historical data.
var Caveats = []string{
	"Assessed values (assessland, assesstot, exempttot) are nominal dollars and are DOF assessed values, not market values.",
	"BBLs change over time (merges, subdivisions, condo conversions create billing lots 7501+). Joining years on bbl undercounts change; use a spatial join on geom or lon/lat for parcel continuity.",
	"yearbuilt and yearalter* use 0 for unknown / none; exclude zeros before computing min, avg or median.",
	"Columns were harmonized across years by name similarity. Codes and their definitions (e.g. special district abbreviations, areasource) shifted over 2002-2025.",
	"builtfar in 2002-2003 and yearalter1 in 2002 come from renamed source columns and are less reliable.",
	"PLUTO represents each condominium as a single record under its billing lot (bldgclass R*), with unit-level values aggregated onto that record.",
	"Parquet geometries are WGS84 (EPSG:4326, lon/lat). FlatGeobuf files and xcoord/ycoord are EPSG:2263 (US feet).",
}
