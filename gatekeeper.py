"""
CropCare AI - Lightweight Plant Image Gatekeeper

This gatekeeper does NOT load TensorFlow or another AI model.
It performs a lightweight visual check before the 38-class
crop disease model runs.

Goal:
    Reject obvious non-plant images such as cats, dogs, people,
    indoor objects, blank images, etc.

The disease model is only called after this check passes.
"""

import numpy as np
from PIL import Image, ImageOps


# ============================================================
# SETTINGS
# ============================================================

MIN_SIDE = 80
MIN_PIXEL_STD = 8.0

# Minimum amount of vegetation-like pixels.
MIN_VEGETATION_RATIO = 0.08

# Very low vegetation is allowed only when there are other
# plant-like colour characteristics.
FALLBACK_VEGETATION_RATIO = 0.15

# Reject images dominated by skin-like colours.
MAX_SKIN_RATIO = 0.30

_loaded = False


# ============================================================
# LOAD
# ============================================================

def load_gatekeeper():
    """
    Lightweight gatekeeper initialization.

    No TensorFlow model is loaded here.
    """
    global _loaded
    _loaded = True

    print("Lightweight gatekeeper loaded.")
    return True


def is_loaded():
    return _loaded


# ============================================================
# IMAGE ANALYSIS
# ============================================================

def _analyse_image(image):
    """
    Calculate simple visual statistics.
    """

    image = ImageOps.exif_transpose(image).convert("RGB")

    width, height = image.size

    if width < MIN_SIDE or height < MIN_SIDE:
        return {
            "valid": False,
            "reason": "Image is too small.",
            "details": {
                "width": width,
                "height": height
            }
        }

    # Resize for fast processing.
    image = image.resize((224, 224))

    arr = np.asarray(image, dtype=np.float32)

    # Overall variation.
    pixel_std = float(np.std(arr))

    if pixel_std < MIN_PIXEL_STD:
        return {
            "valid": False,
            "reason": "Image contains too little visual information.",
            "details": {
                "pixel_std": round(pixel_std, 2)
            }
        }

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    # --------------------------------------------------------
    # GREEN / VEGETATION
    # --------------------------------------------------------

    # Green vegetation generally has G greater than R/B.
    green_mask = (
        (g > r * 1.05) &
        (g > b * 1.05) &
        (g > 45)
    )

    green_ratio = float(np.mean(green_mask))

    # --------------------------------------------------------
    # YELLOW / BROWN PLANT AREAS
    # --------------------------------------------------------

    yellow_mask = (
        (r > 70) &
        (g > 60) &
        (b < 100) &
        (r > b * 1.15) &
        (g > b * 1.05)
    )

    yellow_ratio = float(np.mean(yellow_mask))

    # Brown/dry leaf-like pixels.
    brown_mask = (
        (r > b * 1.25) &
        (g > b * 1.05) &
        (r > 55) &
        (g > 40) &
        (b < 130)
    )

    brown_ratio = float(np.mean(brown_mask))

    # --------------------------------------------------------
    # SKIN-LIKE COLOUR
    # --------------------------------------------------------

    skin_mask = (
        (r > 80) &
        (g > 35) &
        (b > 20) &
        (r > g * 1.15) &
        (r > b * 1.25)
    )

    skin_ratio = float(np.mean(skin_mask))

    # --------------------------------------------------------
    # BRIGHT / NEUTRAL AREA
    # --------------------------------------------------------

    brightness = float(np.mean(arr))

    # Plant-like colour coverage.
    vegetation_ratio = max(
        green_ratio,
        green_ratio + 0.5 * yellow_ratio,
        green_ratio + 0.4 * brown_ratio
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    details = {
        "width": width,
        "height": height,
        "pixel_std": round(pixel_std, 2),
        "green_ratio": round(green_ratio, 3),
        "yellow_ratio": round(yellow_ratio, 3),
        "brown_ratio": round(brown_ratio, 3),
        "skin_ratio": round(skin_ratio, 3),
        "vegetation_ratio": round(vegetation_ratio, 3),
        "brightness": round(brightness, 1),
    }

    # Strong rejection for obvious skin/person-dominated images.
    if skin_ratio > MAX_SKIN_RATIO and green_ratio < 0.05:
        return {
            "valid": False,
            "reason": "The image does not appear to contain a crop or plant leaf.",
            "details": details
        }

    # Normal plant/leaf case.
    if green_ratio >= MIN_VEGETATION_RATIO:
        return {
            "valid": True,
            "reason": "Plant-like vegetation detected.",
            "details": details
        }

    # Yellow/brown/damaged leaves can contain less green.
    if vegetation_ratio >= FALLBACK_VEGETATION_RATIO:
        return {
            "valid": True,
            "reason": "Plant-like leaf colours detected.",
            "details": details
        }

    # If the image has very little vegetation, reject it.
    return {
        "valid": False,
        "reason": "No sufficient plant or leaf characteristics were detected.",
        "details": details
    }


# ============================================================
# PUBLIC CHECK
# ============================================================

def check_image(image):
    """
    Returns:

        {
            "accepted": True/False,
            "reason": "...",
            "details": {...}
        }
    """

    if not _loaded:
        load_gatekeeper()

    try:
        result = _analyse_image(image)

        return {
            "accepted": bool(result["valid"]),
            "reason": result["reason"],
            "details": result.get("details", {})
        }

    except Exception as e:
        return {
            "accepted": False,
            "reason": "Unable to analyse the uploaded image.",
            "details": {
                "error": str(e)
            }
        }


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("python gatekeeper.py path\\to\\image.jpg")
        sys.exit(1)

    image_path = sys.argv[1]

    load_gatekeeper()

    try:
        image = Image.open(image_path)
        result = check_image(image)

        print()
        print("====================================")
        print("CropCare AI Gatekeeper")
        print("====================================")
        print("Accepted:", result["accepted"])
        print("Reason:", result["reason"])
        print("Details:", result["details"])

    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)
