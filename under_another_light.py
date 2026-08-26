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

# ----------------------------------------------------------------------------
# THE STANDARD OBSERVER
# CIE 1931 2-degree colour-matching functions and the D65 relative spectral
# power distribution, tabulated at 10 nm from 380 to 780 nm.
# ----------------------------------------------------------------------------

WAVELENGTHS = np.arange(380, 781, 10)

XBAR = np.array([
    0.001368, 0.004243, 0.014310, 0.043510, 0.134380, 0.283900, 0.348280, 0.336200,
    0.290800, 0.195360, 0.095640, 0.032010, 0.004900, 0.009300, 0.063270, 0.165500,
    0.290400, 0.433450, 0.594500, 0.762100, 0.916300, 1.026300, 1.062200, 1.002600,
    0.854450, 0.642400, 0.447900, 0.283500, 0.164900, 0.087400, 0.046770, 0.022700,
    0.011359, 0.005790, 0.002899, 0.001440, 0.000690, 0.000332, 0.000166, 0.000083,
    0.000042,
])
YBAR = np.array([
    0.000039, 0.000120, 0.000396, 0.001210, 0.004000, 0.011600, 0.023000, 0.038000,
    0.060000, 0.090980, 0.139020, 0.208020, 0.323000, 0.503000, 0.710000, 0.862000,
    0.954000, 0.994950, 0.995000, 0.952000, 0.870000, 0.757000, 0.631000, 0.503000,
    0.381000, 0.265000, 0.175000, 0.107000, 0.061000, 0.032000, 0.017000, 0.008210,
    0.004102, 0.002091, 0.001047, 0.000520, 0.000249, 0.000120, 0.000060, 0.000030,
    0.000015,
])
ZBAR = np.array([
    0.006450, 0.020050, 0.067850, 0.207400, 0.645600, 1.385600, 1.747060, 1.772110,
    1.669200, 1.287640, 0.812950, 0.465180, 0.272000, 0.158200, 0.078250, 0.042160,
    0.020300, 0.008750, 0.003900, 0.002100, 0.001650, 0.001100, 0.000800, 0.000340,
    0.000190, 0.000050, 0.000020, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000,
])
D65_SPD = np.array([
    49.975, 54.648, 82.755, 91.486, 93.432, 86.682, 104.865, 117.008,
    117.812, 114.861, 115.923, 108.811, 109.354, 107.802, 104.790, 107.689,
    104.405, 104.046, 100.000, 96.334, 95.788, 88.686, 90.006, 89.599,
    87.699, 83.289, 83.699, 80.027, 80.215, 82.278, 78.284, 69.721,
    71.609, 74.349, 61.604, 69.886, 75.087, 63.593, 46.418, 66.805,
    63.383,
])

XYZ_TO_LINEAR_SRGB = np.array([
    [ 3.24062548, -1.53720797, -0.49862860],
    [-0.96893071,  1.87575606,  0.04151752],
    [ 0.05571012, -0.20402105,  1.05699594],
])
CAT02 = np.array([
    [ 0.7328,  0.4296, -0.1624],
    [-0.7036,  1.6975,  0.0061],
    [ 0.0030,  0.0136,  0.9834],
])


def illuminant(spec):
    """Relative spectral power. A number is read as a Planckian radiator."""
    if spec == "D65":
        return D65_SPD
    wl = WAVELENGTHS * 1e-9
    c1, c2 = 3.741771e-16, 1.438777e-2      # SI radiation constants
    spd = c1 / (wl ** 5 * (np.exp(c2 / (wl * spec)) - 1.0))
    return 100.0 * spd / spd[WAVELENGTHS == 560]


# ----------------------------------------------------------------------------
# REFLECTANCE
# Each cell is given a spectrum built from two Gaussian lobes over
# wavelength. Their positions drift across the canvas as smooth fields, so
# neighbouring cells are spectrally related rather than randomly coloured --
# the composition is continuous even though every cell is computed alone.
# ----------------------------------------------------------------------------

def smooth_field(points, rng, waves=3, scale=1.6):
    """A sum of a few plane waves. Deterministic, band-limited, in [-1, 1]."""
    total = np.zeros(len(points))
    for _ in range(waves):
        direction = rng.normal(size=2)
        direction /= np.linalg.norm(direction)
        frequency = scale * np.pi * rng.uniform(0.4, 1.5)
        phase = rng.uniform(0, 2 * np.pi)
        total += np.cos(points @ direction * frequency + phase)
    return total / waves


def reflectance_spectra(points, rng):
    """One reflectance curve per cell, values in [0.015, 0.96].

    Two families of pigment, continuously mixed. A REFLECTING band returns a
    narrow slice of the spectrum and reads as a spectral hue. An ABSORBING
    notch subtracts one instead, which is how magenta and every other
    non-spectral colour comes to exist: no wavelength is magenta, it is only
    green removed. The mixture ratio is itself a field, so the two pigments
    interleave in continents rather than meeting at a seam.

    A separate albedo field then multiplies the whole curve. Darkness here is
    not a colour, it is a surface that returns less of whatever arrives.
    """
    band = smooth_field(points, rng, scale=1.4)         # where the band sits
    sharpness = smooth_field(points, rng, scale=2.3)    # how narrow it is
    mixture = smooth_field(points, rng, scale=2.0)      # reflect vs absorb
    albedo = smooth_field(points, rng, scale=0.9)       # lightness terrain

    centre = 420 + 240 * (band * 0.5 + 0.5)             # 420-660 nm
    sigma = 18 + 62 * (sharpness * 0.5 + 0.5)
    ratio = np.clip(mixture * 1.6 + 0.5, 0.0, 1.0) ** 2  # smooth, biased
    strength = 0.10 + 0.90 * (albedo * 0.5 + 0.5) ** 1.7
    grit = rng.normal(scale=0.06, size=len(points))     # per-cell dissent

    lobe = np.exp(-0.5 * ((WAVELENGTHS[None, :] - centre[:, None]) / sigma[:, None]) ** 2)
    reflecting = 0.04 + 0.92 * lobe
    absorbing = 0.96 - 0.88 * lobe

    pigment = ratio[:, None] * reflecting + (1.0 - ratio[:, None]) * absorbing
    spectra = pigment * strength[:, None] * (1.0 + grit[:, None])
    return np.clip(spectra, 0.015, 0.96)
