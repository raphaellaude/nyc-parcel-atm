// Package queries renders DuckDB setup SQL and example queries for the parcel
// datasets, with file locations filled in for a given way of reaching the bucket.
package queries

import (
	"fmt"
	"strings"

	"github.com/raphaellaude/nyc-parcel-atm/mcp/internal/catalog"
)

// Access is how DuckDB reaches the bucket.
type Access string

const (
	// AccessHTTPS reads anonymously through the bucket's public URL (r2.dev or a
	// custom domain). HTTP can't list objects, so files are addressed explicitly.
	AccessHTTPS Access = "https"
	// AccessR2 uses DuckDB's native r2:// support with an R2 API token.
	AccessR2 Access = "r2"
	// AccessS3 uses s3:// against a custom S3-compatible endpoint, e.g. LocalStack
	// or MinIO during development.
	AccessS3 Access = "s3"
)

// Config says where the data lives.
type Config struct {
	Bucket        string
	Prefix        string
	PublicBaseURL string
	R2AccountID   string
	S3Endpoint    string
	S3Region      string
	S3UseSSL      bool
}

// DefaultAccess picks the simplest access mode the config supports.
func (c Config) DefaultAccess() Access {
	switch {
	case c.PublicBaseURL != "":
		return AccessHTTPS
	case c.S3Endpoint != "":
		return AccessS3
	default:
		return AccessR2
	}
}

// ParseAccess validates an access mode, falling back to the config's default.
func (c Config) ParseAccess(s string) (Access, error) {
	switch Access(strings.ToLower(strings.TrimSpace(s))) {
	case "":
		return c.DefaultAccess(), nil
	case AccessHTTPS:
		if c.PublicBaseURL == "" {
			return "", fmt.Errorf("https access needs a public bucket URL; this server has none configured (PARCEL_PUBLIC_BASE_URL)")
		}
		return AccessHTTPS, nil
	case AccessR2:
		return AccessR2, nil
	case AccessS3:
		return AccessS3, nil
	}
	return "", fmt.Errorf("unknown access mode %q (want https, r2 or s3)", s)
}

func (c Config) key(rel string) string {
	if p := strings.Trim(c.Prefix, "/"); p != "" {
		return p + "/" + rel
	}
	return rel
}

func (c Config) bucket() string {
	if c.Bucket == "" {
		return "<bucket>"
	}
	return c.Bucket
}

// URL returns the location of a bucket-relative key for the access mode.
func (c Config) URL(a Access, rel string) string {
	switch a {
	case AccessHTTPS:
		return strings.TrimRight(c.PublicBaseURL, "/") + "/" + c.key(rel)
	case AccessS3:
		return "s3://" + c.bucket() + "/" + c.key(rel)
	default:
		return "r2://" + c.bucket() + "/" + c.key(rel)
	}
}

// ManifestURL is where the sync script writes manifest.json, when publicly readable.
func (c Config) ManifestURL() string {
	if c.PublicBaseURL == "" {
		return ""
	}
	return c.URL(AccessHTTPS, "manifest.json")
}

// ParquetSource returns a DuckDB read_parquet(...) expression over a dataset.
// years limits the files for https access, where globbing isn't possible.
func (c Config) ParquetSource(a Access, dataset string, years []int) string {
	if a == AccessHTTPS {
		urls := make([]string, 0, len(years))
		for _, y := range years {
			key, _ := catalog.FileKey(dataset, y)
			urls = append(urls, "        '"+c.URL(a, key)+"'")
		}
		return "read_parquet([\n" + strings.Join(urls, ",\n") + "\n    ], hive_partitioning = true)"
	}
	return fmt.Sprintf("read_parquet('%s', hive_partitioning = true)", c.URL(a, "parquet/"+dataset+"/*/data.parquet"))
}

// SetupSQL returns the statements to run once per DuckDB session: extensions,
// credentials and a `pluto` view over the core dataset for the given years.
func (c Config) SetupSQL(a Access, years []int) string {
	var b strings.Builder
	b.WriteString("INSTALL spatial; LOAD spatial;\nINSTALL httpfs; LOAD httpfs;\n\n")

	switch a {
	case AccessR2:
		account := c.R2AccountID
		if account == "" {
			account = "<R2_ACCOUNT_ID>"
		}
		fmt.Fprintf(&b, `-- Needs an R2 API token with read access to the bucket.
CREATE OR REPLACE SECRET parcels_r2 (
    TYPE r2,
    KEY_ID '<R2_ACCESS_KEY_ID>',
    SECRET '<R2_SECRET_ACCESS_KEY>',
    ACCOUNT_ID '%s'
);

`, account)
	case AccessS3:
		region := c.S3Region
		if region == "" {
			region = "us-east-1"
		}
		endpoint := c.S3Endpoint
		if endpoint == "" {
			endpoint = "<host:port>"
		}
		fmt.Fprintf(&b, `-- S3-compatible endpoint (LocalStack / MinIO use any key, e.g. 'test').
CREATE OR REPLACE SECRET parcels_s3 (
    TYPE s3,
    KEY_ID '<ACCESS_KEY_ID>',
    SECRET '<SECRET_ACCESS_KEY>',
    ENDPOINT '%s',
    URL_STYLE 'path',
    USE_SSL %t,
    REGION '%s'
);

`, endpoint, c.S3UseSSL, region)
	case AccessHTTPS:
		b.WriteString("-- Public bucket: no credentials needed. HTTP can't list files, so each year is listed.\n")
	}

	fmt.Fprintf(&b, "-- Normalized parcels, all years. Filter on year to only read the files you need.\nCREATE OR REPLACE VIEW pluto AS\n    SELECT * FROM %s;\n", c.ParquetSource(a, "core", years))
	return b.String()
}
