import os
import re
import json
import subprocess

TILES_DIR = "/Users/raphaellaude/Documents/Projects/dxd/processed_data/tiles/"


def get_landuse(year):
    if year == "02":
        return "landUse2"
    elif year in ("03", "04"):
        return "LANDUSE"
    return "LandUse"


def get_layer_id(tiles):
    command = f"ogrinfo {TILES_DIR}/{tiles} | grep \"1:\""
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
                "url": f"pmtiles://https://pluto-hist.s3.amazonaws.com/data/{tiles}",
                "columns": [
                    {
                        "name": "Land use",
                        "id": get_landuse(year),
                    }
                ]
            }
    return json

if __name__ == "__main__":
    data = create_json()
    
    with open("data.json", "w") as f:
        f.write(json.dumps(data))
