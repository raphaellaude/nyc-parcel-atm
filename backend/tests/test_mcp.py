import asyncio

from fastmcp import Client

from mcp_server import mcp


def call(tool, **arguments):
    async def run():
        async with Client(mcp) as client:
            return await client.call_tool(tool, arguments)

    return asyncio.run(run())


def test_catalog_lists_datasets():
    catalog = call("read_catalog").structured_content["result"]
    assert [entry["id"] for entry in catalog] == ["neighborhoods", "pluto"]
    for entry in catalog:
        assert entry["resource"].startswith("https://data.parcels.nyc/")


def test_read_resource_returns_markdown():
    text = call("read_resource", id="/pluto.md").data
    assert "https://data.parcels.nyc/pluto/fgb/pluto26.fgb" in text
    assert "```sql" in text


def test_read_neighborhoods_resource():
    text = call("read_resource", id="neighborhoods").data
    assert "https://data.parcels.nyc/neighborhoods/neighborhoods.parquet" in text
    assert "parcels.neighborhoods" in text


def test_unknown_resource_lists_ids():
    assert (
        "Available ids: neighborhoods, pluto" in call("read_resource", id="nope").data
    )
