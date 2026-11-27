import asyncio

from fastmcp import Client

from mcp_server import mcp


def call(tool, **arguments):
    async def run():
        async with Client(mcp) as client:
            return await client.call_tool(tool, arguments)

    return asyncio.run(run())


def test_catalog_lists_parcel_data():
    catalog = call("read_catalog").structured_content["result"]
    assert [entry["id"] for entry in catalog] == ["pluto"]
    assert catalog[0]["resource"].startswith("https://data.parcels.nyc/")


def test_read_resource_returns_markdown():
    text = call("read_resource", id="/pluto.md").data
    assert "https://data.parcels.nyc/pluto/fgb/pluto26.fgb" in text
    assert "```sql" in text


def test_unknown_resource_lists_ids():
    assert "Available ids: pluto" in call("read_resource", id="nope").data
