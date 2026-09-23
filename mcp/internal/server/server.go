// Package server exposes the parcel data catalog as MCP tools and resources.
package server

import (
	"context"
	"encoding/json"
	"fmt"
	"slices"
	"strings"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/catalog"
	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/manifest"
	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/queries"
)

const instructions = `This server documents the normalized historical NYC MapPLUTO parcel data (2002-2025) that the nyc-parcel-atm ELT pipeline publishes to a Cloudflare R2 bucket as GeoParquet, FlatGeobuf and PMTiles.
It does not run queries. It tells you where the files are, what the columns mean and gives DuckDB SQL to query them.
Typical flow: get_duckdb_setup (run once per DuckDB session, creates a "pluto" view) -> get_schema -> get_example_queries.
Read the caveats in get_schema before comparing years.`

// Server holds the data location config and optional live manifest.
type Server struct {
	Config   queries.Config
	Manifest *manifest.Loader
	Version  string
}

// New builds the MCP server with all tools and resources registered.
func (s *Server) New() *mcp.Server {
	srv := mcp.NewServer(&mcp.Implementation{
		Name:    "nyc-parcel-data",
		Title:   "NYC historical parcel data (MapPLUTO 2002-2025)",
		Version: s.Version,
	}, &mcp.ServerOptions{Instructions: instructions})

	mcp.AddTool(srv, &mcp.Tool{
		Name:        "get_data_locations",
		Title:       "Where the parcel data lives",
		Description: "List the datasets in the bucket (normalized GeoParquet, per-year full GeoParquet, FlatGeobuf, PMTiles) with their URLs per year, formats, CRS and, when the manifest is reachable, sizes and row counts.",
		Annotations: readOnly(),
	}, s.dataLocations)

	mcp.AddTool(srv, &mcp.Tool{
		Name:        "get_schema",
		Title:       "Parcel dataset schema",
		Description: "Describe columns: names, DuckDB types, meaning and code values (land use, borough, building class, owner type). The 'core' dataset has the same columns in every year; for the 'full' dataset pass a year to get that year's columns. Includes caveats for cross-year analysis.",
		Annotations: readOnly(),
	}, s.schema)

	mcp.AddTool(srv, &mcp.Tool{
		Name:        "get_duckdb_setup",
		Title:       "DuckDB setup SQL",
		Description: "SQL to run once per DuckDB session: loads spatial + httpfs, configures credentials for the chosen access mode and creates a `pluto` view over the normalized data that the example queries use.",
		Annotations: readOnly(),
	}, s.duckdbSetup)

	mcp.AddTool(srv, &mcp.Tool{
		Name:        "get_example_queries",
		Title:       "Example DuckDB queries",
		Description: "Ready-to-run DuckDB SQL for common questions (parcel history by BBL or point, land use / zoning change, housing growth, valuation, ownership, spatial joins, exports). Filter by topic: " + strings.Join(queries.Topics(), ", ") + ".",
		Annotations: readOnly(),
	}, s.exampleQueries)

	s.addResources(srv)
	return srv
}

func readOnly() *mcp.ToolAnnotations {
	f := false
	return &mcp.ToolAnnotations{ReadOnlyHint: true, OpenWorldHint: &f}
}

func text(s string) *mcp.CallToolResult {
	return &mcp.CallToolResult{Content: []mcp.Content{&mcp.TextContent{Text: s}}}
}

// years returns the years in the manifest for a dataset, or the configured
// default range, and a note when the manifest couldn't be used.
func (s *Server) years(ctx context.Context, dataset string) ([]int, *manifest.Manifest, string) {
	m, err := s.Manifest.Get(ctx)
	if m != nil {
		if d, ok := m.Datasets[dataset]; ok && len(d.Years) > 0 {
			return d.Years, m, ""
		}
	}
	note := "Manifest unavailable, so years are the pipeline's configured range and may include years not uploaded yet."
	if err != nil {
		note += " (" + err.Error() + ")"
	}
	return catalog.DefaultYears(), m, note
}

func filterYears(all, want []int) []int {
	if len(want) == 0 {
		return all
	}
	var out []int
	for _, y := range want {
		if y < 100 {
			y += 2000
		}
		if slices.Contains(all, y) {
			out = append(out, y)
		}
	}
	return out
}

// --- get_data_locations ---

type LocationsInput struct {
	Dataset string `json:"dataset,omitempty" jsonschema:"one of core, full, fgb, pmtiles; omit for all"`
	Years   []int  `json:"years,omitempty" jsonschema:"limit per-year URLs to these years (e.g. 2010 or 10); omit for all"`
	Access  string `json:"access,omitempty" jsonschema:"https (public bucket URL), r2 (r2:// with an API token) or s3 (s3:// with a custom endpoint); defaults to what the server is configured for"`
}

func (s *Server) dataLocations(ctx context.Context, _ *mcp.CallToolRequest, in LocationsInput) (*mcp.CallToolResult, any, error) {
	access, err := s.Config.ParseAccess(in.Access)
	if err != nil {
		return nil, nil, err
	}
	datasets := catalog.Datasets
	if in.Dataset != "" {
		d, ok := catalog.DatasetByName(in.Dataset)
		if !ok {
			return nil, nil, fmt.Errorf("unknown dataset %q (want core, full, fgb or pmtiles)", in.Dataset)
		}
		datasets = []catalog.Dataset{d}
	}

	var b strings.Builder
	fmt.Fprintf(&b, "# NYC parcel data locations\n\nBucket: `%s`", s.Config.Bucket)
	if s.Config.Prefix != "" {
		fmt.Fprintf(&b, " (prefix `%s`)", s.Config.Prefix)
	}
	fmt.Fprintf(&b, "\nAccess mode: `%s`\n", access)
	if s.Config.PublicBaseURL != "" {
		fmt.Fprintf(&b, "Public base URL: %s\n", s.Config.PublicBaseURL)
	}
	if u := s.Config.ManifestURL(); u != "" {
		fmt.Fprintf(&b, "Manifest (file list, row counts, per-year schemas): %s\n", u)
	}

	for _, d := range datasets {
		// fgb/pmtiles years come from the parquet datasets in the manifest.
		manifestDataset := d.Name
		if d.Name == "fgb" || d.Name == "pmtiles" {
			manifestDataset = "core"
		}
		all, m, note := s.years(ctx, manifestDataset)
		years := filterYears(all, in.Years)

		fmt.Fprintf(&b, "\n## %s\n\n%s\n\n- Format: %s\n- CRS: %s\n- Path: `%s`\n", d.Name, d.Description, d.Format, d.CRS, d.PathPattern)
		if d.Name == "core" || d.Name == "full" {
			if access != queries.AccessHTTPS {
				fmt.Fprintf(&b, "- Glob: `%s`\n", s.Config.URL(access, "parquet/"+d.Name+"/*/data.parquet"))
			}
			if m != nil {
				if md, ok := m.Datasets[d.Name]; ok {
					fmt.Fprintf(&b, "- Rows (all years): %d\n", md.RowCount)
				}
			}
		}
		if note != "" {
			fmt.Fprintf(&b, "- Note: %s\n", note)
		}
		if len(years) == 0 {
			b.WriteString("\nNo matching years.\n")
			continue
		}

		b.WriteString("\n| year | url | size | rows |\n|---|---|---|---|\n")
		for _, y := range years {
			key, _ := catalog.FileKey(d.Name, y)
			url := s.Config.URL(access, key)
			if d.Name == "fgb" || d.Name == "pmtiles" {
				// GDAL and map clients read these over HTTP, not through DuckDB secrets.
				if s.Config.PublicBaseURL != "" {
					url = s.Config.URL(queries.AccessHTTPS, key)
				}
			}
			size, rows := "", ""
			if m != nil {
				var f manifest.File
				var ok bool
				if d.Name == "core" || d.Name == "full" {
					f, ok = m.DatasetFile(d.Name, y)
				} else {
					f, ok = m.HasFile(key)
				}
				if ok {
					size = humanBytes(f.SizeBytes)
					if f.RowCount > 0 {
						rows = fmt.Sprint(f.RowCount)
					}
				} else {
					size = "missing"
				}
			}
			fmt.Fprintf(&b, "| %d | `%s` | %s | %s |\n", y, url, size, rows)
		}
	}
	return text(b.String()), nil, nil
}

func humanBytes(n int64) string {
	const unit = 1024
	if n < unit {
		return fmt.Sprintf("%d B", n)
	}
	div, exp := int64(unit), 0
	for m := n / unit; m >= unit; m /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(n)/float64(div), "KMGT"[exp])
}

// --- get_schema ---

type SchemaInput struct {
	Dataset string `json:"dataset,omitempty" jsonschema:"core (default) or full"`
	Year    int    `json:"year,omitempty" jsonschema:"for the full dataset: which year's columns to list (e.g. 2024)"`
	Column  string `json:"column,omitempty" jsonschema:"describe just this column, including all code values"`
}

func (s *Server) schema(ctx context.Context, _ *mcp.CallToolRequest, in SchemaInput) (*mcp.CallToolResult, any, error) {
	dataset := strings.ToLower(in.Dataset)
	if dataset == "" {
		dataset = "core"
	}
	if in.Year > 0 && in.Year < 100 {
		in.Year += 2000
	}

	if in.Column != "" {
		return s.columnDetail(ctx, strings.ToLower(in.Column))
	}

	var b strings.Builder
	switch dataset {
	case "core":
		b.WriteString("# Schema: core (normalized, all years)\n\n")
		b.WriteString("Same columns and types in every year. Query through the `pluto` view from get_duckdb_setup. Geometry is EPSG:4326.\n\n")
		b.WriteString("| column | type | description |\n|---|---|---|\n")
		for _, c := range catalog.CoreColumns {
			desc := c.Description
			if c.Derived {
				desc = "(derived) " + desc
			}
			if len(c.Codes) > 0 {
				desc += " Codes: " + codeSummary(c.Codes)
			}
			fmt.Fprintf(&b, "| %s | %s | %s |\n", c.Name, c.Type, escapePipes(desc))
		}
	case "full":
		m, err := s.Manifest.Get(ctx)
		if m == nil {
			return nil, nil, fmt.Errorf("the full dataset's columns vary by year and come from the bucket manifest, which is unavailable: %v. Run `DESCRIBE SELECT * FROM read_parquet('<url>')` on the year's file instead", err)
		}
		years := m.Datasets["full"].Years
		if in.Year == 0 {
			return text(s.fullColumnAvailability(m)), nil, nil
		}
		f, ok := m.DatasetFile("full", in.Year)
		if !ok {
			return nil, nil, fmt.Errorf("no full dataset file for %d; available years: %v", in.Year, years)
		}
		fmt.Fprintf(&b, "# Schema: full, %d (%d rows)\n\nColumns and types as exported for this year. Core columns are documented with get_schema(column=...).\n\n| column | type | description |\n|---|---|---|\n", in.Year, f.RowCount)
		for _, col := range f.Columns {
			desc := ""
			if c, ok := catalog.CoreColumn(col.Name); ok {
				desc = c.Description
			}
			fmt.Fprintf(&b, "| %s | %s | %s |\n", col.Name, col.Type, escapePipes(desc))
		}
	default:
		return nil, nil, fmt.Errorf("unknown dataset %q (want core or full; fgb has the same columns as full, pmtiles is for maps)", in.Dataset)
	}

	b.WriteString("\n## Caveats\n\n")
	for _, c := range catalog.Caveats {
		fmt.Fprintf(&b, "- %s\n", c)
	}
	return text(b.String()), nil, nil
}

func (s *Server) columnDetail(ctx context.Context, name string) (*mcp.CallToolResult, any, error) {
	var b strings.Builder
	c, isCore := catalog.CoreColumn(name)
	if isCore {
		fmt.Fprintf(&b, "# %s (%s)\n\n%s\n", c.Name, c.Type, c.Description)
		if c.Derived {
			b.WriteString("\nDerived by the ELT export (not a MapPLUTO source column).\n")
		}
		if len(c.Codes) > 0 {
			b.WriteString("\n| value | meaning |\n|---|---|\n")
			for _, code := range c.Codes {
				fmt.Fprintf(&b, "| %s | %s |\n", code.Value, code.Meaning)
			}
		}
	} else {
		fmt.Fprintf(&b, "# %s\n\nNot a core column: it is only in the `full` dataset for some years.\n", name)
	}

	if m, _ := s.Manifest.Get(ctx); m != nil {
		var present []string
		for _, f := range m.Datasets["full"].Files {
			for _, col := range f.Columns {
				if col.Name == name {
					present = append(present, fmt.Sprintf("%d (%s)", f.Year, col.Type))
				}
			}
		}
		if len(present) > 0 {
			fmt.Fprintf(&b, "\nIn the full dataset for: %s\n", strings.Join(present, ", "))
		} else if !isCore {
			return nil, nil, fmt.Errorf("column %q is not in the core schema or any year of the full dataset", name)
		}
	} else if !isCore {
		return nil, nil, fmt.Errorf("column %q is not a core column, and the manifest (needed to check year-specific columns) is unavailable", name)
	}
	return text(b.String()), nil, nil
}

func (s *Server) fullColumnAvailability(m *manifest.Manifest) string {
	var b strings.Builder
	files := m.Datasets["full"].Files
	counts := map[string]int{}
	var order []string
	for _, f := range files {
		for _, col := range f.Columns {
			if counts[col.Name] == 0 {
				order = append(order, col.Name)
			}
			counts[col.Name]++
		}
	}
	fmt.Fprintf(&b, "# Schema: full (per year)\n\nColumn availability across %d years. Pass `year` for one year's column types.\n\n| column | years present | core |\n|---|---|---|\n", len(files))
	for _, name := range order {
		_, core := catalog.CoreColumn(name)
		fmt.Fprintf(&b, "| %s | %d/%d | %v |\n", name, counts[name], len(files), core)
	}
	return b.String()
}

func codeSummary(codes []catalog.Code) string {
	parts := make([]string, len(codes))
	for i, c := range codes {
		parts[i] = c.Value + "=" + c.Meaning
	}
	return strings.Join(parts, "; ")
}

func escapePipes(s string) string { return strings.ReplaceAll(s, "|", "\\|") }

// --- get_duckdb_setup ---

type SetupInput struct {
	Access string `json:"access,omitempty" jsonschema:"https, r2 or s3; defaults to what the server is configured for"`
	Years  []int  `json:"years,omitempty" jsonschema:"only include these years in the pluto view (https access lists files explicitly)"`
}

func (s *Server) duckdbSetup(ctx context.Context, _ *mcp.CallToolRequest, in SetupInput) (*mcp.CallToolResult, any, error) {
	access, err := s.Config.ParseAccess(in.Access)
	if err != nil {
		return nil, nil, err
	}
	all, _, note := s.years(ctx, "core")
	years := filterYears(all, in.Years)
	if len(years) == 0 {
		return nil, nil, fmt.Errorf("none of %v are available; available years: %v", in.Years, all)
	}

	var b strings.Builder
	fmt.Fprintf(&b, "# DuckDB setup (%s)\n\nRun once per session (DuckDB >= 1.1). Afterwards query the `pluto` view.\n", access)
	if note != "" {
		fmt.Fprintf(&b, "\nNote: %s\n", note)
	}
	fmt.Fprintf(&b, "\n```sql\n%s```\n", s.Config.SetupSQL(access, years))
	b.WriteString("\nTips:\n- Always filter on `year` when you can: it's the hive partition, so other files aren't read.\n- Prefilter spatial queries on `lon`/`lat` before ST_* predicates.\n- For repeated analysis, COPY a subset to a local parquet file first.\n")
	return text(b.String()), nil, nil
}

// --- get_example_queries ---

type ExamplesInput struct {
	Topic  string `json:"topic,omitempty" jsonschema:"tag or id to filter by, e.g. history, spatial, change, housing, zoning; omit for all"`
	Access string `json:"access,omitempty" jsonschema:"https, r2 or s3; defaults to what the server is configured for"`
}

func (s *Server) exampleQueries(ctx context.Context, _ *mcp.CallToolRequest, in ExamplesInput) (*mcp.CallToolResult, any, error) {
	access, err := s.Config.ParseAccess(in.Access)
	if err != nil {
		return nil, nil, err
	}
	years, _, _ := s.years(ctx, "core")
	examples := s.Config.Filter(in.Topic, access)
	if len(examples) == 0 {
		return nil, nil, fmt.Errorf("no examples for topic %q; topics: %s", in.Topic, strings.Join(queries.Topics(), ", "))
	}

	var b strings.Builder
	b.WriteString("# Example DuckDB queries\n\nThese assume the setup SQL from get_duckdb_setup has been run (it creates the `pluto` view).\n")
	for _, e := range examples {
		sql, err := s.Config.Render(e, access, years)
		if err != nil {
			return nil, nil, err
		}
		fmt.Fprintf(&b, "\n## %s\n\n`%s` · tags: %s\n\n%s\n\n```sql\n%s\n```\n", e.Title, e.ID, strings.Join(e.Tags, ", "), e.Description, sql)
	}
	return text(b.String()), nil, nil
}

// --- resources ---

func (s *Server) addResources(srv *mcp.Server) {
	srv.AddResource(&mcp.Resource{
		URI:         "parcels://schema/core",
		Name:        "core-schema",
		Title:       "Core parcel schema",
		Description: "Columns, types, descriptions and code values of the normalized dataset, as JSON.",
		MIMEType:    "application/json",
	}, func(context.Context, *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		body, err := json.MarshalIndent(map[string]any{
			"columns":  catalog.CoreColumns,
			"datasets": catalog.Datasets,
			"caveats":  catalog.Caveats,
		}, "", "  ")
		if err != nil {
			return nil, err
		}
		return &mcp.ReadResourceResult{Contents: []*mcp.ResourceContents{{
			URI: "parcels://schema/core", MIMEType: "application/json", Text: string(body),
		}}}, nil
	})

	srv.AddResource(&mcp.Resource{
		URI:         "parcels://manifest",
		Name:        "manifest",
		Title:       "Bucket manifest",
		Description: "The manifest.json written by the ELT sync: files, sizes, row counts and per-year columns.",
		MIMEType:    "application/json",
	}, func(ctx context.Context, _ *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		m, err := s.Manifest.Get(ctx)
		if m == nil {
			return nil, err
		}
		body, err := json.MarshalIndent(m, "", "  ")
		if err != nil {
			return nil, err
		}
		return &mcp.ReadResourceResult{Contents: []*mcp.ResourceContents{{
			URI: "parcels://manifest", MIMEType: "application/json", Text: string(body),
		}}}, nil
	})

	srv.AddResource(&mcp.Resource{
		URI:         "parcels://queries.sql",
		Name:        "queries",
		Title:       "Setup and example queries",
		Description: "DuckDB setup plus every example query as one SQL script, for the server's default access mode.",
		MIMEType:    "application/sql",
	}, func(ctx context.Context, _ *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		years, _, _ := s.years(ctx, "core")
		script, err := s.SQLScript(s.Config.DefaultAccess(), years)
		if err != nil {
			return nil, err
		}
		return &mcp.ReadResourceResult{Contents: []*mcp.ResourceContents{{
			URI: "parcels://queries.sql", MIMEType: "application/sql", Text: script,
		}}}, nil
	})
}

// SQLScript renders the setup SQL and every example as a single script.
func (s *Server) SQLScript(access queries.Access, years []int) (string, error) {
	var b strings.Builder
	b.WriteString("-- NYC historical parcel data: DuckDB setup and example queries\n\n")
	b.WriteString(s.Config.SetupSQL(access, years))
	for _, e := range s.Config.Filter("", access) {
		sql, err := s.Config.Render(e, access, years)
		if err != nil {
			return "", err
		}
		fmt.Fprintf(&b, "\n-- %s: %s\n%s\n", e.ID, e.Title, sql)
	}
	return b.String(), nil
}
