import os
import re
import subprocess
from pathlib import Path

from elt.constants import BASE_DIR

TILES_DIR = Path(BASE_DIR or ".") / "assets" / "tilesets"


def get_layer_id(tiles):
    command = f'ogrinfo {TILES_DIR}/{tiles} | grep "1:"'
    result = subprocess.run(command, shell=True, text=True, capture_output=True)

    if result.returncode != 0:
        print("Error executing command:", result.stderr)
        raise Exception("Error executing command:", result.stderr)

    layer_id_match = re.search(r"(?<=\s)(.*?)(?=\s\()", result.stdout)

    if not layer_id_match:
        raise ValueError(f"Could not find layer ID in output: {result.stdout}")

    layer_id = layer_id_match.group(0)

    return layer_id


def create_json():
    json = {}
    for tiles in os.listdir(TILES_DIR):
        if tiles.endswith(".pmtiles"):
            print(tiles)
            year = re.search("\d{2}", tiles)
            if not year:
                raise ValueError(f"Could not find year in filename: {tiles}")
            year = year[0]
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
