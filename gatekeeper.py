"""
CropCare AI - Lightweight image gatekeeper

This gatekeeper runs BEFORE the 38-class disease model.

Goals:
- Reject obvious non-plant images such as cats, dogs, people, cars, etc.
- Reject blank / extremely dark / extremely uniform images.
- Avoid loading a second TensorFlow/MobileNetV2 model.
- Keep Render memory and startup time low.
- Work directly with the PIL Image already opened by app.py.

app.py expects:
    gatekeeper.load_gatekeeper()
    gatekeeper.is_loaded()
    gatekeeper.check_image(image)
"""

import sys

import numpy as np
from PIL import Image, ImageOps


# ============================================================
# SETTINGS
# ============================================================

MIN_SIDE = 80

# Reject images with almost no visual information.
MIN_PIXEL_STD = 8.0

# Minimum amount of vegetation-like colour for a normal green crop.
MIN_GREEN_RATIO = 0.055

# Slightly higher requirement when the image is mostly neutral.
MIN_LEAF_COLOR_RATIO = 0.080

# Very dark images are usually unusable.
MIN_BRIGHT_RATIO = 0.08

# Avoid accepting images where almost everything is one colour.
MAX_DOMINANT_COLOR_RATIO = 0.92


# ============================================================
# GATEKEEPER STATE
# ============================================================

_loaded = False


# ============================================================
# LOAD
# ============================================================

def load_gatekeeper():
    """
    Lightweight gatekeeper initialization.

    No TensorFlow model is loaded here.
    This prevents a second MobileNetV2 model from consuming
    Render memory and avoids the extra ImageNet download.
    """

    global _loaded

    _loaded = True

    print("Lightweight gatekeeper loaded.")

    return True


def is_loaded():
    return _loaded


# ============================================================
# IMAGE HELPERS
# ============================================================

def _open_rgb(image):
    """
    Convert PIL image / file-like input to RGB PIL image.
    """

    if image is None:
        raise ValueError("No image was provided.")

    if not isinstance(image, Image.Image):
        image = Image.open(image)

    image = ImageOps.exif_transpose(image)

    return image.convert("RGB")


def _result(accepted, reason, **details):
    return {
        "accepted": bool(accepted),
        "reason": str(reason),
        "details": details,
    }


# ============================================================
# COLOUR ANALYSIS
# ============================================================

def _colour_features(image_rgb):
    """
    Calculate simple visual features.

    These are intentionally lightweight and require only NumPy/PIL.
    """

    img = image_rgb.resize((224, 224))

    rgb = np.asarray(img, dtype=np.float32)

    # --------------------------------------------------------
    # RGB statistics
    # --------------------------------------------------------

    mean_rgb = rgb.mean(axis=(0, 1))

    pixel_std = float(rgb.std())

    brightness = rgb.mean(axis=2)

    bright_ratio = float((brightness >= 35).mean())

    dark_ratio = float((brightness < 25).mean())


    # --------------------------------------------------------
    # HSV statistics
    # --------------------------------------------------------

    hsv = np.asarray(
        img.convert("HSV"),
        dtype=np.float32
    )

    h = hsv[..., 0]
    s = hsv[..., 1]
    v = hsv[..., 2]


    # PIL hue range is 0-255.
    #
    # Green:
    # approximately 35-170 degrees
    #
    # Yellow/green:
    # approximately 25-120 degrees
    #
    # We intentionally allow yellow/brownish crop leaves
    # because diseased leaves are not always bright green.

    green_mask = (
        (h >= 25) &
        (h <= 120) &
        (s >= 40) &
        (v >= 35)
    )

    green_ratio = float(green_mask.mean())


    # Stronger green vegetation.
    strong_green_mask = (
        (h >= 35) &
        (h <= 105) &
        (s >= 55) &
        (v >= 45)
    )

    strong_green_ratio = float(
        strong_green_mask.mean()
    )


    # Yellow / yellow-green.
    yellow_green_mask = (
        (h >= 20) &
        (h <= 75) &
        (s >= 35) &
        (v >= 35)
    )

    yellow_green_ratio = float(
        yellow_green_mask.mean()
    )


    # Brown / dry leaf-like pixels.
    brown_mask = (
        (h >= 5) &
        (h <= 35) &
        (s >= 35) &
        (v >= 30) &
        (v <= 210)
    )

    brown_ratio = float(
        brown_mask.mean()
    )


    # Combined crop/leaf colour estimate.
    leaf_color_ratio = float(
        np.logical_or(
            green_mask,
            yellow_green_mask
        ).mean()
    )


    # --------------------------------------------------------
    # Saturation
    # --------------------------------------------------------

    saturated_ratio = float(
        (s >= 45).mean()
    )


    # --------------------------------------------------------
    # Dominant colour
    # --------------------------------------------------------

    small_rgb = np.asarray(
        img.resize((32, 32)),
        dtype=np.float32
    )

    # Quantize RGB into simple bins.
    quantized = (
        (small_rgb // 32)
        .astype(np.int16)
    )

    colors = quantized.reshape(-1, 3)

    _, counts = np.unique(
        colors,
        axis=0,
        return_counts=True
    )

    dominant_color_ratio = float(
        counts.max() / len(colors)
    )


    return {
        "pixel_std": pixel_std,
        "mean_r": float(mean_rgb[0]),
        "mean_g": float(mean_rgb[1]),
        "mean_b": float(mean_rgb[2]),
        "bright_ratio": bright_ratio,
        "dark_ratio": dark_ratio,
        "green_ratio": green_ratio,
        "strong_green_ratio": strong_green_ratio,
        "yellow_green_ratio": yellow_green_ratio,
        "brown_ratio": brown_ratio,
        "leaf_color_ratio": leaf_color_ratio,
        "saturated_ratio": saturated_ratio,
        "dominant_color_ratio": dominant_color_ratio,
    }


# ============================================================
# GREEN / PLANT SCORE
# ============================================================

def _plant_score(features):
    """
    Produce a lightweight plant-likeness score.

    This is NOT a trained AI classifier.
    It is intentionally used as a fast first-stage filter.
    """

    green = features["green_ratio"]
    strong_green = features["strong_green_ratio"]
    yellow_green = features["yellow_green_ratio"]
    brown = features["brown_ratio"]
    leaf_color = features["leaf_color_ratio"]
    saturated = features["saturated_ratio"]

    score = 0.0


    # Green vegetation is the strongest signal.
    score += min(green / 0.35, 1.0) * 0.45


    # Strong green adds confidence.
    score += min(strong_green / 0.25, 1.0) * 0.20


    # Yellow-green is useful for diseased leaves.
    score += min(yellow_green / 0.30, 1.0) * 0.15


    # Brown can occur on diseased/dry leaves.
    score += min(brown / 0.25, 1.0) * 0.08


    # Leaf colours + saturation.
    score += min(leaf_color / 0.40, 1.0) * 0.07

    score += min(saturated / 0.70, 1.0) * 0.05


    return float(min(score, 1.0))


# ============================================================
# MAIN CHECK
# ============================================================

def check_image(image):
    """
    Check whether an uploaded image looks suitable for
    crop-disease analysis.

    Returns:

        {
            "accepted": True/False,
            "reason": "...",
            "details": {...}
        }
    """

    try:

        img = _open_rgb(image)

    except Exception as e:

        return _result(
            False,
            f"Unable to read image: {e}"
        )


    # --------------------------------------------------------
    # Size
    # --------------------------------------------------------

    width, height = img.size

    if width < MIN_SIDE or height < MIN_SIDE:

        return _result(
            False,
            "Image is too small. Please upload a clear crop image.",
            width=width,
            height=height
        )


    # --------------------------------------------------------
    # Visual information
    # --------------------------------------------------------

    features = _colour_features(img)


    if features["pixel_std"] < MIN_PIXEL_STD:

        return _result(
            False,
            "The uploaded image does not contain enough visual information.",
            **features
        )


    # --------------------------------------------------------
    # Extremely dark image
    # --------------------------------------------------------

    if features["bright_ratio"] < MIN_BRIGHT_RATIO:

        return _result(
            False,
            "The image is too dark to identify a crop leaf.",
            **features
        )


    # --------------------------------------------------------
    # Almost completely one colour
    # --------------------------------------------------------

    if (
        features["dominant_color_ratio"]
        > MAX_DOMINANT_COLOR_RATIO
        and features["saturated_ratio"] < 0.25
    ):

        return _result(
            False,
            "The image does not contain enough plant-like visual detail.",
            **features
        )


    # --------------------------------------------------------
    # Calculate plant score
    # --------------------------------------------------------

    score = _plant_score(features)


    # --------------------------------------------------------
    # STRONG GREEN / LEAF-LIKE IMAGE
    # --------------------------------------------------------

    if (
        features["green_ratio"] >= MIN_GREEN_RATIO
        and score >= 0.30
    ):

        return _result(
            True,
            "Plant-like vegetation detected.",
            plant_score=round(score, 3),
            **features
        )


    # --------------------------------------------------------
    # Yellow/green diseased leaf
    #
    # This allows leaves that are yellowing or partially
    # damaged instead of requiring bright green colour.
    # --------------------------------------------------------

    if (
        features["leaf_color_ratio"] >= MIN_LEAF_COLOR_RATIO
        and score >= 0.27
        and features["saturated_ratio"] >= 0.20
    ):

        return _result(
            True,
            "Leaf-like colours detected.",
            plant_score=round(score, 3),
            **features
        )


    # --------------------------------------------------------
    # Strong brown/yellow vegetation
    #
    # Allows some diseased or dried leaves.
    # --------------------------------------------------------

    if (
        features["brown_ratio"] >= 0.12
        and features["yellow_green_ratio"] >= 0.08
        and score >= 0.25
    ):

        return _result(
            True,
            "Possible diseased or dry leaf detected.",
            plant_score=round(score, 3),
            **features
        )


    # --------------------------------------------------------
    # REJECT
    # --------------------------------------------------------

    return _result(
        False,
        "This image does not appear to contain a crop or plant leaf.",
        plant_score=round(score, 3),
        **features
    )


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print(
            "Usage: python gatekeeper.py "
            "path\\to\\photo.jpg"
        )

        sys.exit(1)


    print(
        "Loading gatekeeper...",
        load_gatekeeper()
    )


    out = check_image(sys.argv[1])


    print(
        "ACCEPTED"
        if out["accepted"]
        else "REJECTED",
        "-",
        out["reason"]
    )


    print("\nDetails:")

    for key, value in out["details"].items():

        print(
            f"  {key}: {value}"
        )
