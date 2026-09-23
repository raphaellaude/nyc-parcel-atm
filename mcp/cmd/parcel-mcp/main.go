// Command parcel-mcp is an MCP server that documents how to query the NYC
// historical parcel data the ELT pipeline publishes to Cloudflare R2.
//
// Usage:
//
//	parcel-mcp                 # serve MCP over stdio
//	parcel-mcp -http :8080     # serve MCP over streamable HTTP at /mcp
//	parcel-mcp sql [-access s3] > queries.sql   # print setup + example SQL
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/catalog"
	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/manifest"
	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/queries"
	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/server"
)

var version = "dev"

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func configFromEnv() queries.Config {
	useSSL, _ := strconv.ParseBool(env("PARCEL_S3_USE_SSL", "false"))
	return queries.Config{
		Bucket:        env("PARCEL_BUCKET", "nyc-parcels"),
		Prefix:        os.Getenv("PARCEL_PREFIX"),
		PublicBaseURL: os.Getenv("PARCEL_PUBLIC_BASE_URL"),
		R2AccountID:   os.Getenv("PARCEL_R2_ACCOUNT_ID"),
		S3Endpoint:    os.Getenv("PARCEL_S3_ENDPOINT"),
		S3Region:      os.Getenv("PARCEL_S3_REGION"),
		S3UseSSL:      useSSL,
	}
}

func newServer() *server.Server {
	cfg := configFromEnv()
	manifestSource := env("PARCEL_MANIFEST_URL", cfg.ManifestURL())
	return &server.Server{
		Config:   cfg,
		Manifest: manifest.NewLoader(manifestSource, 10*time.Minute),
		Version:  version,
	}
}

func main() {
	log.SetFlags(0)
	log.SetOutput(os.Stderr) // stdout is the MCP transport

	if len(os.Args) > 1 && os.Args[1] == "sql" {
		printSQL(os.Args[2:])
		return
	}

	httpAddr := flag.String("http", "", "serve streamable HTTP on this address (e.g. :8080) instead of stdio")
	flag.Parse()

	s := newServer()
	ctx := context.Background()

	if *httpAddr != "" {
		handler := mcp.NewStreamableHTTPHandler(func(*http.Request) *mcp.Server { return s.New() }, nil)
		mux := http.NewServeMux()
		mux.Handle("/mcp", handler)
		mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) { fmt.Fprintln(w, "ok") })
		log.Printf("parcel-mcp listening on %s/mcp", *httpAddr)
		log.Fatal(http.ListenAndServe(*httpAddr, mux))
	}

	if err := s.New().Run(ctx, &mcp.StdioTransport{}); err != nil {
		log.Fatal(err)
	}
}

func printSQL(args []string) {
	fs := flag.NewFlagSet("sql", flag.ExitOnError)
	access := fs.String("access", "", "https, r2 or s3 (default: from config)")
	fs.Parse(args)

	s := newServer()
	a, err := s.Config.ParseAccess(*access)
	if err != nil {
		log.Fatal(err)
	}
	years := catalog.DefaultYears()
	if m, err := s.Manifest.Get(context.Background()); err == nil {
		if d, ok := m.Datasets["core"]; ok && len(d.Years) > 0 {
			years = d.Years
		}
	} else {
		log.Printf("warning: %v; using years %d-%d", err, catalog.MinYear, catalog.MaxYear)
	}
	script, err := s.SQLScript(a, years)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Print(script)
}
