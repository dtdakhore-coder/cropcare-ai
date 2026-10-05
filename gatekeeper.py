"""
CropCare AI gatekeeper

Decides whether an uploaded photo looks like a plant / crop leaf BEFORE the
disease model runs. app.py imports this file.

Test from Command Prompt:
    python gatekeeper.py path\\to\\photo.jpg
"""

import os
import sys

import numpy as np
from PIL import Image, ImageOps

# ============================================================
# THRESHOLDS  (tune these)
# ============================================================

MIN_SIDE = 80                  # smaller images are rejected
MIN_PIXEL_STD = 8.0            # blank / one-colour images are rejected
ANIMAL_PERSON_REJECT = 0.30    # ImageNet animal/person probability that rejects
NON_PLANT_WORD_REJECT = 0.35   # ImageNet object probability that rejects
PLANT_WORD_ACCEPT = 0.15       # ImageNet plant probability that accepts
MIN_VEGETATION_RATIO = 0.08    # share of green/yellow-green pixels needed
FALLBACK_VEGETATION_RATIO = 0.15  # used when the ImageNet model is not loaded
MAX_SKIN_RATIO = 0.20          # colour-only mode: reject photos dominated by skin tones

# Render free plan has only 512 MB RAM, so the ImageNet model is OFF by default.
# Locally you can turn it on:  set USE_IMAGENET_GATEKEEPER=1   (Command Prompt)
USE_IMAGENET = os.environ.get("USE_IMAGENET_GATEKEEPER", "0") == "1"
