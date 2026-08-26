"""
UNDER ANOTHER LIGHT
Neha Naik

A tessellation in which no colour is ever chosen.

Every cell owns a reflectance spectrum, not a colour. The colour you see is
what happens when a light source meets that spectrum and a human eye
integrates the product. Change the light and the geometry holds still while
the entire palette moves -- because the palette was never in the artwork.
It was in the room.

The eye adapts to the light it lives under, which is why we do not experience
a tungsten-lit room as orange. ADAPTATION is that dial: at 1.0 the observer
has fully discounted the illuminant, at 0.0 the illuminant is seen raw.
The image lives in between, where perception actually happens.

Run:  python under_another_light.py
Deps: numpy, scipy, pillow   (pip install numpy scipy pillow)
Out:  under_another_light.svg  +  under_another_light.png
"""

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import Delaunay, Voronoi

# ----------------------------------------------------------------------------
# PARAMETERS -- the whole piece is determined by these. Change nothing else.
# ----------------------------------------------------------------------------

SEED = 1931           # the year the standard observer was defined
WIDTH, HEIGHT = 1600, 2000
CELLS = 700           # interior generating points
RELAX = 2             # Lloyd iterations: 0 is chaos, 8 is a honeycomb
LIGHT = 2856          # illuminant colour temperature in kelvin, or "D65"
ADAPTATION = 0.55     # 0.0 = illuminant seen raw, 1.0 = fully discounted
SUPERSAMPLE = 3       # raster antialiasing factor
