package queries

import (
	"bytes"
	"fmt"
	"slices"
	"strings"
	"text/template"

	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/catalog"
)

// Example is a documented DuckDB query. SQL is a text/template rendered with
// Earliest/Latest years and helpers for file locations; it assumes SetupSQL ran.
type Example struct {
	ID          string
	Title       string
	Description string
	Tags        []string
	// HTTPSOnly marks examples that need anonymous HTTP access (GDAL /vsicurl/).
	HTTPSOnly bool
	SQL       string
}

// Topics lists the tags used by the examples.
func Topics() []string {
	var topics []string
	for _, e := range Examples {
		for _, t := range e.Tags {
			if !slices.Contains(topics, t) {
				topics = append(topics, t)
			}
		}
	}
	slices.Sort(topics)
	return topics
}

var Examples = []Example{
	{
		ID:          "overview-by-year",
		Title:       "Parcels, units and assessed value per year",
		Description: "A quick sanity check of what's loaded and how the city changed at a glance.",
		Tags:        []string{"overview", "housing", "valuation"},
		SQL: `SELECT
    year,
    count(*) AS parcels,
    sum(unitsres) AS residential_units,
    round(sum(assesstot) / 1e9, 1) AS assessed_total_billions
FROM pluto
GROUP BY year
ORDER BY year;`,
	},
	{
		ID:          "parcel-history-by-bbl",
		Title:       "History of one parcel by BBL",
		Description: "Every year of one tax lot (here the Empire State Building, BBL 1008350041). Because files are sorted by bbl, DuckDB skips most row groups.",
		Tags:        []string{"history", "lookup"},
		SQL: `SELECT year, address, ownername, bldgclass, landuse, zonedist1,
       numfloors, unitsres, assessland, assesstot
FROM pluto
WHERE bbl = 1008350041
ORDER BY year;`,
	},
	{
		ID:          "point-lookup",
		Title:       "Parcel containing a lon/lat point in every year",
		Description: "Prefilters on the lon/lat centroid columns (cheap, prunes row groups) and then tests the polygon. Widen the box for very large lots whose centroid may be far from the point.",
		Tags:        []string{"spatial", "lookup", "history"},
		SQL: `SELECT year, bbl, address, ownername, zonedist1, landuse, assesstot
FROM pluto
WHERE lon BETWEEN -73.9877 AND -73.9837
  AND lat BETWEEN 40.7464 AND 40.7504
  AND ST_Contains(geom, ST_Point(-73.9857, 40.7484))
ORDER BY year;`,
	},
	{
		ID:          "address-search",
		Title:       "Find a parcel by address",
		Description: "PLUTO addresses are upper case with numbered avenues/streets written as digits ('350 5 AVENUE'). Use ILIKE with wildcards; spellings drift between years.",
		Tags:        []string{"lookup"},
		SQL: `SELECT year, bbl, address, ownername
FROM pluto
WHERE year = {{.Latest}}
  AND address ILIKE '%350 5 AVENUE%';`,
	},
	{
		ID:          "within-distance",
		Title:       "Parcels within 500 feet of a point",
		Description: "Distances need a projected CRS: transform to EPSG:2263 (US feet). The lon/lat box keeps the transform to nearby rows.",
		Tags:        []string{"spatial"},
		SQL: `WITH target AS (
    SELECT ST_Transform(ST_Point(-73.9857, 40.7484), 'EPSG:4326', 'EPSG:2263', always_xy := true) AS pt
)
SELECT bbl, address, landuse, numfloors, yearbuilt
FROM pluto, target
WHERE year = {{.Latest}}
  AND lon BETWEEN -73.992 AND -73.979
  AND lat BETWEEN 40.743 AND 40.753
  AND ST_DWithin(ST_Transform(geom, 'EPSG:4326', 'EPSG:2263', always_xy := true), target.pt, 500)
ORDER BY bbl;`,
	},
	{
		ID:          "land-use-by-year",
		Title:       "Land use mix per year",
		Description: "Parcel counts and acreage by DCP land use category, with labels.",
		Tags:        []string{"land-use", "overview"},
		SQL: `WITH labels(landuse, label) AS (VALUES
    (1, 'One & Two Family'), (2, 'Multi-Family Walk-Up'), (3, 'Multi-Family Elevator'),
    (4, 'Mixed Res. & Commercial'), (5, 'Commercial & Office'), (6, 'Industrial & Manufacturing'),
    (7, 'Transportation & Utility'), (8, 'Public Facilities'), (9, 'Open Space'),
    (10, 'Parking'), (11, 'Vacant Land')
)
SELECT year, landuse, label, count(*) AS parcels, round(sum(lotarea) / 43560) AS acres
FROM pluto JOIN labels USING (landuse)
GROUP BY ALL
ORDER BY year, landuse;`,
	},
	{
		ID:          "land-use-transitions",
		Title:       "How land use changed between two years",
		Description: "Joins two years on bbl. Lots that were merged or split between the years drop out of the join; see the caveats.",
		Tags:        []string{"land-use", "change"},
		SQL: `WITH before AS (SELECT bbl, landuse FROM pluto WHERE year = {{.Earliest}}),
     after AS (SELECT bbl, landuse FROM pluto WHERE year = {{.Latest}})
SELECT before.landuse AS landuse_{{.Earliest}}, after.landuse AS landuse_{{.Latest}}, count(*) AS parcels
FROM before JOIN after USING (bbl)
WHERE before.landuse IS DISTINCT FROM after.landuse
GROUP BY ALL
ORDER BY parcels DESC
LIMIT 20;`,
	},
	{
		ID:          "vacant-lots-developed",
		Title:       "Vacant lots that were built on",
		Description: "Lots that were vacant (landuse 11) in the first year and not vacant in the latest, with what they became.",
		Tags:        []string{"land-use", "change", "housing"},
		SQL: `SELECT
    after.borough,
    after.landuse,
    count(*) AS lots,
    sum(after.unitsres) AS new_residential_units
FROM pluto AS before
JOIN pluto AS after USING (bbl)
WHERE before.year = {{.Earliest}} AND before.landuse = 11
  AND after.year = {{.Latest}} AND after.landuse <> 11
GROUP BY ALL
ORDER BY lots DESC;`,
	},
	{
		ID:          "rezonings",
		Title:       "Lots whose zoning district changed",
		Description: "Compares simplified zoning districts (e.g. 'M1', 'R6') between two years, by borough.",
		Tags:        []string{"zoning", "change"},
		SQL: `WITH z AS (
    SELECT year, bbl, borough,
           regexp_extract(zonedist1, '^[A-Za-z]+[0-9]*', 0) AS zone
    FROM pluto
    WHERE year IN ({{.Earliest}}, {{.Latest}})
)
SELECT a.borough, a.zone AS zone_{{.Earliest}}, b.zone AS zone_{{.Latest}}, count(*) AS lots
FROM z AS a JOIN z AS b ON a.bbl = b.bbl AND a.year = {{.Earliest}} AND b.year = {{.Latest}}
WHERE a.zone IS DISTINCT FROM b.zone
GROUP BY ALL
ORDER BY lots DESC
LIMIT 25;`,
	},
	{
		ID:          "units-growth-by-zip",
		Title:       "Residential unit growth by ZIP code",
		Description: "Aggregating before comparing avoids the BBL-change problem.",
		Tags:        []string{"housing", "change"},
		SQL: `SELECT
    zipcode,
    sum(unitsres) FILTER (WHERE year = {{.Earliest}}) AS units_{{.Earliest}},
    sum(unitsres) FILTER (WHERE year = {{.Latest}}) AS units_{{.Latest}},
    units_{{.Latest}} - units_{{.Earliest}} AS added
FROM pluto
WHERE year IN ({{.Earliest}}, {{.Latest}}) AND zipcode IS NOT NULL
GROUP BY zipcode
ORDER BY added DESC NULLS LAST
LIMIT 20;`,
	},
	{
		ID:          "new-construction",
		Title:       "New buildings by year built and borough",
		Description: "Uses the latest release, where yearbuilt is most complete. yearbuilt = 0 means unknown.",
		Tags:        []string{"housing"},
		SQL: `SELECT yearbuilt, borough, count(*) AS buildings, sum(unitsres) AS residential_units
FROM pluto
WHERE year = {{.Latest}} AND yearbuilt >= 2000
GROUP BY ALL
ORDER BY yearbuilt, borough;`,
	},
	{
		ID:          "median-assessed-value",
		Title:       "Median assessed value of 1-2 family homes by borough",
		Description: "Nominal DOF assessed values, not market values.",
		Tags:        []string{"valuation", "history"},
		SQL: `SELECT year, borough, median(assesstot) AS median_assessed, count(*) AS lots
FROM pluto
WHERE landuse = 1 AND assesstot > 0
GROUP BY ALL
ORDER BY borough, year;`,
	},
	{
		ID:          "top-owners",
		Title:       "Largest owners by assessed value",
		Description: "ownername is free text; the same owner often appears under several spellings.",
		Tags:        []string{"ownership", "valuation"},
		SQL: `SELECT ownername, count(*) AS lots, round(sum(assesstot) / 1e6) AS assessed_millions
FROM pluto
WHERE year = {{.Latest}} AND ownername IS NOT NULL
GROUP BY ownername
ORDER BY assessed_millions DESC
LIMIT 25;`,
	},
	{
		ID:          "owner-over-time",
		Title:       "One owner's holdings over time",
		Description: "Pattern match on ownername to catch spelling variants.",
		Tags:        []string{"ownership", "history"},
		SQL: `SELECT year, count(*) AS lots, sum(unitsres) AS residential_units
FROM pluto
WHERE ownername ILIKE '%HOUSING AUTH%'
GROUP BY year
ORDER BY year;`,
	},
	{
		ID:          "building-class-mix",
		Title:       "Building class categories per year",
		Description: "Groups the DOF building class by its first letter.",
		Tags:        []string{"land-use", "overview"},
		SQL: `SELECT year, substring(bldgclass, 1, 1) AS bldgclass_category, count(*) AS lots
FROM pluto
WHERE bldgclass IS NOT NULL
GROUP BY ALL
ORDER BY year, lots DESC;`,
	},
	{
		ID:          "lot-area-check",
		Title:       "Compute polygon area in square feet",
		Description: "Reproject to EPSG:2263 for areas and lengths in feet, e.g. to check lotarea.",
		Tags:        []string{"spatial"},
		SQL: `SELECT bbl, lotarea,
       round(ST_Area(ST_Transform(geom, 'EPSG:4326', 'EPSG:2263', always_xy := true))) AS polygon_sqft
FROM pluto
WHERE year = {{.Latest}} AND borocode = 1
LIMIT 10;`,
	},
	{
		ID:          "full-dataset-one-year",
		Title:       "All columns for a single year",
		Description: "The full dataset keeps every harmonized column for that year, including ones not present in every year. Check the schema first.",
		Tags:        []string{"schema"},
		SQL: `DESCRIBE SELECT * FROM {{full .Latest}};

SELECT * FROM {{full .Latest}} LIMIT 5;`,
	},
	{
		ID:          "export-geojson",
		Title:       "Export a subset to GeoJSON",
		Description: "Writes a local file with GDAL; any GDAL vector driver works.",
		Tags:        []string{"export", "spatial"},
		SQL: `COPY (
    SELECT bbl, address, landuse, zonedist1, geom
    FROM pluto
    WHERE year = {{.Latest}} AND borocode = 1 AND zonedist1 LIKE 'M%'
) TO 'manhattan_manufacturing_{{.Latest}}.geojson' WITH (FORMAT GDAL, DRIVER 'GeoJSON');`,
	},
	{
		ID:          "cache-locally",
		Title:       "Cache a subset as local parquet",
		Description: "Pull what you need once, then iterate locally without network round trips.",
		Tags:        []string{"export"},
		SQL: `COPY (SELECT * FROM pluto WHERE borocode = 3)
TO 'brooklyn_parcels.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);

CREATE OR REPLACE VIEW brooklyn AS SELECT * FROM 'brooklyn_parcels.parquet';`,
	},
	{
		ID:          "flatgeobuf-bbox",
		Title:       "Bounding-box read from FlatGeobuf",
		Description: "FlatGeobuf files are in EPSG:2263 with a spatial index, so a bbox read only fetches nearby features over HTTP range requests.",
		Tags:        []string{"spatial", "lookup"},
		HTTPSOnly:   true,
		SQL: `SELECT address, ownername, zonedist1, assesstot
FROM ST_Read(
    '/vsicurl/{{fgb .Latest}}',
    spatial_filter_box = ST_MakeBox2D(ST_Point(988000, 211500), ST_Point(989000, 212500))::BOX_2D
);`,
	},
}

// RenderData is available to example templates.
type RenderData struct {
	Earliest int
	Latest   int
}

// Render fills an example's template for an access mode.
func (c Config) Render(e Example, a Access, years []int) (string, error) {
	if len(years) == 0 {
		years = catalog.DefaultYears()
	}
	data := RenderData{Earliest: slices.Min(years), Latest: slices.Max(years)}

	funcs := template.FuncMap{
		"full": func(year int) string {
			key, _ := catalog.FileKey("full", year)
			return fmt.Sprintf("read_parquet('%s')", c.URL(a, key))
		},
		"fgb": func(year int) string {
			key, _ := catalog.FileKey("fgb", year)
			return c.URL(AccessHTTPS, key)
		},
	}
	tmpl, err := template.New(e.ID).Funcs(funcs).Parse(e.SQL)
	if err != nil {
		return "", fmt.Errorf("parsing example %s: %w", e.ID, err)
	}
	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, data); err != nil {
		return "", fmt.Errorf("rendering example %s: %w", e.ID, err)
	}
	return buf.String(), nil
}

// Filter returns examples matching a topic tag or id substring (empty = all),
// dropping examples the access mode can't run.
func (c Config) Filter(topic string, a Access) []Example {
	topic = strings.ToLower(strings.TrimSpace(topic))
	var out []Example
	for _, e := range Examples {
		if e.HTTPSOnly && (a != AccessHTTPS || c.PublicBaseURL == "") {
			continue
		}
		if topic == "" || slices.Contains(e.Tags, topic) || strings.Contains(e.ID, topic) {
			out = append(out, e)
		}
	}
	return out
}
