#!/usr/bin/env bash
# Full pipeline: textures -> Blender passes for both views -> web layers.
set -euo pipefail
cd "$(dirname "$0")"
python3 tex_misc.py
PIZZA_RES=4096 python3 tex_pizza.py
for v in ${VIEWS:-desktop}; do
  python3 scene.py --view "$v" --mode final ${SAMPLES:+--samples $SAMPLES}
done
python3 extract.py
