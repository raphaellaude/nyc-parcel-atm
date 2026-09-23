// Package manifest loads the manifest.json that `elt sync-to-r2` writes to the
// bucket, describing which files, years, row counts and columns are available.
package manifest

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

type ColumnInfo struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type File struct {
	Key       string       `json:"key"`
	SizeBytes int64        `json:"size_bytes"`
	Year      int          `json:"year,omitempty"`
	RowCount  int64        `json:"row_count,omitempty"`
	Columns   []ColumnInfo `json:"columns,omitempty"`
}

type Dataset struct {
	Files    []File `json:"files"`
	Years    []int  `json:"years"`
	RowCount int64  `json:"row_count"`
}

type Manifest struct {
	Version       int                `json:"version"`
	GeneratedAt   string             `json:"generated_at"`
	Bucket        string             `json:"bucket"`
	Prefix        string             `json:"prefix"`
	PublicBaseURL string             `json:"public_base_url"`
	Datasets      map[string]Dataset `json:"datasets"`
	Files         []File             `json:"files"`
}

// DatasetFile returns the manifest entry for a dataset's file in a given year.
func (m *Manifest) DatasetFile(dataset string, year int) (File, bool) {
	for _, f := range m.Datasets[dataset].Files {
		if f.Year == year {
			return f, true
		}
	}
	return File{}, false
}

// HasFile reports whether a non-parquet file (fgb, pmtiles) is in the bucket.
func (m *Manifest) HasFile(key string) (File, bool) {
	for _, f := range m.Files {
		if f.Key == key {
			return f, true
		}
	}
	return File{}, false
}

// Loader fetches the manifest from a URL or local path and caches it.
type Loader struct {
	Source string
	TTL    time.Duration
	Client *http.Client

	mu        sync.Mutex
	cached    *Manifest
	fetchedAt time.Time
	lastErr   error
}

func NewLoader(source string, ttl time.Duration) *Loader {
	return &Loader{Source: source, TTL: ttl, Client: &http.Client{Timeout: 10 * time.Second}}
}

// Get returns the cached manifest, refreshing it when stale. If a refresh fails
// the previous manifest is returned along with the error.
func (l *Loader) Get(ctx context.Context) (*Manifest, error) {
	if l == nil || l.Source == "" {
		return nil, fmt.Errorf("no manifest source configured (set PARCEL_MANIFEST_URL or PARCEL_PUBLIC_BASE_URL)")
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	if l.cached != nil && time.Since(l.fetchedAt) < l.TTL {
		return l.cached, nil
	}
	// Don't hammer an unreachable source on every tool call.
	if l.lastErr != nil && time.Since(l.fetchedAt) < 30*time.Second {
		return l.cached, l.lastErr
	}

	m, err := l.fetch(ctx)
	l.fetchedAt = time.Now()
	l.lastErr = err
	if err != nil {
		return l.cached, err
	}
	l.cached = m
	return m, nil
}

func (l *Loader) fetch(ctx context.Context) (*Manifest, error) {
	var body []byte
	var err error

	if strings.HasPrefix(l.Source, "http://") || strings.HasPrefix(l.Source, "https://") {
		body, err = l.fetchHTTP(ctx)
	} else {
		body, err = os.ReadFile(strings.TrimPrefix(l.Source, "file://"))
	}
	if err != nil {
		return nil, fmt.Errorf("loading manifest from %s: %w", l.Source, err)
	}

	var m Manifest
	if err := json.Unmarshal(body, &m); err != nil {
		return nil, fmt.Errorf("parsing manifest from %s: %w", l.Source, err)
	}
	return &m, nil
}

func (l *Loader) fetchHTTP(ctx context.Context) ([]byte, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, l.Source, nil)
	if err != nil {
		return nil, err
	}
	resp, err := l.Client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status %s", resp.Status)
	}
	return io.ReadAll(io.LimitReader(resp.Body, 32<<20))
}
