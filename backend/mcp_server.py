from pathlib import Path

import yaml
from fastmcp import FastMCP

RESOURCES_DIR = Path(__file__).parent / "resources"
OKF_RESERVED = {"index.md", "log.md"}

RESOURCES = {
    path.relative_to(RESOURCES_DIR).with_suffix("").as_posix(): path.read_text()
    for path in sorted(RESOURCES_DIR.rglob("*.md"))
    if path.name not in OKF_RESERVED
}

CATALOG = [
    {"id": resource_id, **yaml.safe_load(text.split("---", 2)[1])}
    for resource_id, text in RESOURCES.items()
]

mcp = FastMCP(
    "Parcel ATM",
    instructions=(
        "Historical NYC MapPLUTO tax lot data (2002-2026), plus a lookup mapping "
        "neighborhood names to boroughs and community districts. Call read_catalog to "
        "list datasets, then read_resource for layout, schema and DuckDB SQL examples. "
        "For questions about a named neighborhood, read 'neighborhoods' as well as 'pluto'."
    ),
)


@mcp.tool
def read_catalog() -> list[dict]:
    """List the datasets available, with their id, type, title, description and public URL."""
    return [
        {
            key: entry.get(key)
            for key in ("id", "type", "title", "description", "resource", "tags")
        }
        for entry in CATALOG
    ]


@mcp.tool
def read_resource(id: str) -> str:
    """Read the full markdown documentation for a dataset id from read_catalog."""
    resource_id = id.strip().strip("/").removesuffix(".md")
    if resource_id in RESOURCES:
        return RESOURCES[resource_id]
    return f"No resource '{id}'. Available ids: {', '.join(RESOURCES)}"
