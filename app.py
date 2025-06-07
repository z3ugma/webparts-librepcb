# Global imports
import json
import logging
import os
import sys

from first import first

from adapters.easyeda.easyeda_api import EasyEDAApi
from svg_add_pad_labels import add_pad_numbers_to_svg_file

# 1. Get the root logger (or a specific logger if your_module uses a named logger)
# For simplicity, let's configure the root logger.
# If your_module does `logger = logging.getLogger(__name__)`, then you might want to
# configure that specific logger or its parent.
logger = logging.getLogger()  # This gets the root logger
logger.setLevel(logging.INFO)

# 3. Create a handler to output to stdout (the console).
stream_handler = logging.StreamHandler(
    stream=sys.stdout
)  # Defaults to sys.stderr, use sys.stdout explicitly if needed
# stream_handler = logging.StreamHandler(sys.stdout) # To explicitly use stdout

# 4. Set the logging level for the handler.
# This also needs to be DEBUG (or lower) if you want to see debug messages.
stream_handler.setLevel(logging.INFO)

# 5. (Optional) Create a formatter to define the log message format.
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
stream_handler.setFormatter(formatter)

# 6. Add the handler to the logger.
logger.addHandler(stream_handler)

api = EasyEDAApi()
lcsc_id = "C1530836"

os.makedirs("downloads", exist_ok=True)

search_results = api.search_easyeda_api(search=lcsc_id)
print(len(search_results))
print(first(search_results)["describe"])


cad_data = api.get_cad_data_of_component(lcsc_id=lcsc_id)
# API returned no data
if not cad_data:
    logger.error(f"Failed to fetch data from EasyEDA API for part {lcsc_id}")

with open(f"downloads/{lcsc_id}.json", "w") as f:
    f.write(json.dumps(cad_data, indent=4, sort_keys=True))

parts = cad_data["packageDetail"]["dataStr"]["shape"]
svgnodes = [k for k in parts if k.startswith("SVGNODE")]
if svgnodes:
    svgjson = svgnodes[-1].split("~")[-1]
    svg_node = json.loads(svgjson)
    attrs_3d = svg_node.get("attrs", {})
    if attrs_3d.get("uuid"):
        uuid_3d = attrs_3d["uuid"]
        model3d = api.get_step_3d_model(attrs_3d["uuid"])
        print("Found 3D Model STEP file, saving...")
        with open(f"downloads/{lcsc_id}.step", "wb") as f:
            f.write(model3d)


# print(easyeda_symbol)
svgs = api.get_svgs(lcsc_id)

for i in range(0, len(svgs["result"])):
    with open(f"downloads/{lcsc_id}_{i}.svg", "w") as f:
        f.write(svgs["result"][i]["svg"])


add_pad_numbers_to_svg_file(input_svg_path=f"downloads/{lcsc_id}_1.svg")


with open(f"{lcsc_id}_svgs.json", "w") as f:
    f.write(json.dumps(svgs, indent=4, sort_keys=True))
