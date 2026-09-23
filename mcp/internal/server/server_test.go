package server

import (
	"context"
	"os"
	"regexp"
	"strings"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/catalog"
	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/manifest"
	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/queries"
)

// testdata/manifest.json was produced by `elt sync-to-r2` against LocalStack
// with a two-year (2002, 2024) fixture.
func newTestSession(t *testing.T, cfg queries.Config, manifestPath string) *mcp.ClientSession {
	t.Helper()
	ctx := context.Background()
	s := &Server{Config: cfg, Manifest: manifest.NewLoader(manifestPath, time.Minute), Version: "test"}

	serverTransport, clientTransport := mcp.NewInMemoryTransports()
	if _, err := s.New().Connect(ctx, serverTransport, nil); err != nil {
		t.Fatal(err)
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "test"}, nil)
	session, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { session.Close() })
	return session
}

var publicCfg = queries.Config{Bucket: "nyc-parcels", PublicBaseURL: "https://data.example.com"}

func call(t *testing.T, session *mcp.ClientSession, tool string, args map[string]any) (string, bool) {
	t.Helper()
	res, err := session.CallTool(context.Background(), &mcp.CallToolParams{Name: tool, Arguments: args})
	if err != nil {
		t.Fatalf("%s: %v", tool, err)
	}
	var b strings.Builder
	for _, c := range res.Content {
		if tc, ok := c.(*mcp.TextContent); ok {
			b.WriteString(tc.Text)
		}
	}
	return b.String(), res.IsError
}

func mustContain(t *testing.T, got string, wants ...string) {
	t.Helper()
	for _, w := range wants {
		if !strings.Contains(got, w) {
			t.Errorf("output missing %q:\n%s", w, got)
		}
	}
}

func TestListTools(t *testing.T) {
	session := newTestSession(t, publicCfg, "testdata/manifest.json")
	res, err := session.ListTools(context.Background(), nil)
	if err != nil {
		t.Fatal(err)
	}
	var names []string
	for _, tool := range res.Tools {
		names = append(names, tool.Name)
	}
	mustContain(t, strings.Join(names, ","), "get_data_locations", "get_schema", "get_duckdb_setup", "get_example_queries")
}

func TestDataLocations(t *testing.T) {
	session := newTestSession(t, publicCfg, "testdata/manifest.json")

	out, isErr := call(t, session, "get_data_locations", map[string]any{"dataset": "core"})
	if isErr {
		t.Fatal(out)
	}
	mustContain(t, out,
		"https://data.example.com/parquet/core/year=2002/data.parquet",
		"https://data.example.com/parquet/core/year=2024/data.parquet",
		"| 20 |", // row count from manifest
	)
	if strings.Contains(out, "year=2010") {
		t.Error("should only list years present in the manifest")
	}

	out, _ = call(t, session, "get_data_locations", map[string]any{"dataset": "fgb", "years": []int{2, 24}})
	mustContain(t, out, "fgb/pluto24.fgb", "missing") // 2002 fgb isn't in the fixture bucket

	out, _ = call(t, session, "get_data_locations", map[string]any{"dataset": "core", "access": "r2"})
	mustContain(t, out, "r2://nyc-parcels/parquet/core/*/data.parquet")

	_, isErr = call(t, session, "get_data_locations", map[string]any{"dataset": "nope"})
	if !isErr {
		t.Error("expected error for unknown dataset")
	}
}

func TestDataLocationsWithoutManifest(t *testing.T) {
	session := newTestSession(t, queries.Config{Bucket: "b", R2AccountID: "acct"}, "")
	out, isErr := call(t, session, "get_data_locations", map[string]any{"dataset": "core"})
	if isErr {
		t.Fatal(out)
	}
	mustContain(t, out, "Manifest unavailable", "r2://b/parquet/core/year=2010/data.parquet")
}

func TestSchema(t *testing.T) {
	session := newTestSession(t, publicCfg, "testdata/manifest.json")

	out, _ := call(t, session, "get_schema", nil)
	mustContain(t, out, "| landuse | SMALLINT |", "11=Vacant Land", "| geom | GEOMETRY |", "Caveats")

	out, _ = call(t, session, "get_schema", map[string]any{"dataset": "full", "year": 2002})
	mustContain(t, out, "full, 2002", "| oldcol |")

	out, _ = call(t, session, "get_schema", map[string]any{"dataset": "full"})
	mustContain(t, out, "| oldcol | 1/2 | false |", "| landuse | 2/2 | true |")

	out, _ = call(t, session, "get_schema", map[string]any{"column": "bldgclass"})
	mustContain(t, out, "| D | Elevator apartments |")

	out, _ = call(t, session, "get_schema", map[string]any{"column": "oldcol"})
	mustContain(t, out, "Not a core column", "2002 (VARCHAR)")

	_, isErr := call(t, session, "get_schema", map[string]any{"column": "does_not_exist"})
	if !isErr {
		t.Error("expected error for unknown column")
	}
}

func TestDuckDBSetup(t *testing.T) {
	cfg := publicCfg
	cfg.S3Endpoint = "localhost:4566"
	session := newTestSession(t, cfg, "testdata/manifest.json")

	out, _ := call(t, session, "get_duckdb_setup", nil)
	mustContain(t, out, "CREATE OR REPLACE VIEW pluto", "https://data.example.com/parquet/core/year=2024/data.parquet")

	out, _ = call(t, session, "get_duckdb_setup", map[string]any{"access": "s3"})
	mustContain(t, out, "TYPE s3", "ENDPOINT 'localhost:4566'", "s3://nyc-parcels/parquet/core/*/data.parquet")

	out, _ = call(t, session, "get_duckdb_setup", map[string]any{"access": "r2"})
	mustContain(t, out, "TYPE r2", "ACCOUNT_ID '<R2_ACCOUNT_ID>'")
}

func TestExampleQueries(t *testing.T) {
	session := newTestSession(t, publicCfg, "testdata/manifest.json")

	out, _ := call(t, session, "get_example_queries", map[string]any{"topic": "change"})
	mustContain(t, out, "land-use-transitions", "year = 2002", "year = 2024")
	if strings.Contains(out, "top-owners") {
		t.Error("topic filter not applied")
	}

	out, _ = call(t, session, "get_example_queries", map[string]any{"topic": "spatial"})
	mustContain(t, out, "/vsicurl/https://data.example.com/fgb/pluto24.fgb")

	out, _ = call(t, session, "get_example_queries", map[string]any{"topic": "spatial", "access": "r2"})
	if strings.Contains(out, "vsicurl") {
		t.Error("https-only example included for r2 access")
	}
}

func TestAllExamplesRender(t *testing.T) {
	cfg := queries.Config{Bucket: "b", PublicBaseURL: "https://x", S3Endpoint: "localhost:4566"}
	for _, a := range []queries.Access{queries.AccessHTTPS, queries.AccessR2, queries.AccessS3} {
		for _, e := range cfg.Filter("", a) {
			sql, err := cfg.Render(e, a, catalog.DefaultYears())
			if err != nil {
				t.Fatalf("%s/%s: %v", a, e.ID, err)
			}
			if strings.Contains(sql, "{{") || strings.Contains(sql, "<no value>") {
				t.Errorf("%s/%s: unrendered template:\n%s", a, e.ID, sql)
			}
		}
	}
}

// The Go catalog documents the columns elt/elt/schema.py exports. Keep them in sync.
func TestCoreColumnsMatchELTSchema(t *testing.T) {
	src, err := os.ReadFile("../../../elt/elt/schema.py")
	if err != nil {
		t.Skipf("elt schema not found: %v", err)
	}
	block := regexp.MustCompile(`(?s)CORE_COLUMNS[^{]*\{(.*?)\n\}`).FindSubmatch(src)
	if block == nil {
		t.Fatal("CORE_COLUMNS not found in schema.py")
	}
	pairs := regexp.MustCompile(`"(\w+)":\s*"(\w+)"`).FindAllSubmatch(block[1], -1)

	derived := 0
	for _, c := range catalog.CoreColumns {
		if c.Derived {
			derived++
		}
	}
	if got, want := len(catalog.CoreColumns)-derived, len(pairs); got != want {
		t.Errorf("catalog has %d source columns, schema.py has %d", got, want)
	}
	for _, p := range pairs {
		name, typ := string(p[1]), string(p[2])
		c, ok := catalog.CoreColumn(name)
		if !ok {
			t.Errorf("column %s from schema.py is not documented in the catalog", name)
			continue
		}
		if c.Type != typ {
			t.Errorf("column %s: catalog type %s, schema.py type %s", name, c.Type, typ)
		}
	}
}
