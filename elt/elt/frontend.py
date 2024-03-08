import json
import os
import re
import subprocess

TILES_DIR = "/Users/raphaellaude/Documents/Projects/dxd/v2/assets/tilesets"


def get_layer_id(tiles):
    command = f'ogrinfo {TILES_DIR}/{tiles} | grep "1:"'
    result = subprocess.run(command, shell=True, text=True, capture_output=True)

    if result.returncode != 0:
        print("Error executing command:", result.stderr)
        raise Exception("Error executing command:", result.stderr)

    layer_id = re.search("(?<=\s)(.*?)(?=\s\()", result.stdout)

    layer_id_match = re.search(r"(?<=\s)(.*?)(?=\s\()", result.stdout)
    layer_id = layer_id_match.group(0)

    return layer_id


def create_json():
    json = {}
    for tiles in os.listdir(TILES_DIR):
        if tiles.endswith(".pmtiles"):
            print(tiles)
            year = re.search("\d{2}", tiles)[0]
            layer_id = get_layer_id(tiles)

            json[year] = {
                "year": int("20" + year),
                "id": layer_id,
                "url": f"pmtiles://https://pluto-hist.s3.amazonaws.com/data/tilesets/{tiles}",
                "columns": [
                    {
                        "name": "Land use",
                        "id": "landuse",
                    },
                    {
                        "name": "Simplified zoning district",
                        "id": "zonedist1",
                    },
                    {
                        "name": "Assessed land value",
                        "id": "assessland",
                    },
                    {
                        "name": "Assessed total value",
                        "id": "assesstot",

                    },
                    {
                        "name": "Number of floors",
                        "id": "numfloors",
                    },
                    {
                        "name": "Year built",
                        "id": "yearbuilt",
                    },
                    {
                        "name": "Residential units",
                        "id": "unitsres",
                    },
                    {
                        "name": "Building class",
                        "id": "bldgclass",
                    },
                    {
                        "name": "Year altered",
                        "id": "yearalter1",
                    },
                    {
                        "name": "Built FAR",
                        "id": "builtfar",
                    },
                ],
            }
    return json
