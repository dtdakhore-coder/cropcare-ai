"""
CropCare AI gatekeeper

Decides whether an uploaded photo looks like a plant / crop leaf BEFORE the
disease model runs. app.py imports this file.

Test from Command Prompt:
    python gatekeeper.py path\\to\\photo.jpg
"""

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
FALLBACK_VEGETATION_RATIO = 0.15  # used only if the ImageNet model failed to load

_model = None

# ============================================================
# WORD LISTS (ImageNet label words)
# ============================================================

PLANT_WORDS = {
    "plant", "tree", "flower", "leaf", "leaves", "vegetable", "fruit", "crop",
    "maize", "corn", "wheat", "rice", "potato", "tomato", "pepper", "cabbage",
    "lettuce", "broccoli", "cauliflower", "cucumber", "pumpkin", "zucchini",
    "squash", "bean", "pea", "apple", "orange", "lemon", "banana", "strawberry",
    "pineapple", "mushroom", "daisy", "rose", "sunflower", "vine", "palm",
    "bamboo", "fern", "fig", "acorn", "berry", "pod", "ear", "pot", "hay",
    "greenhouse", "cardoon", "artichoke", "rapeseed", "buckeye", "hip",
}

NON_PLANT_WORDS = {
    "cat", "dog", "puppy", "kitten", "horse", "cow", "sheep", "goat", "pig",
    "chicken", "bird", "fish", "tiger", "lion", "bear", "monkey", "person",
    "man", "woman", "boy", "girl", "car", "truck", "bus", "motorcycle",
    "bicycle", "airplane", "boat", "ship", "computer", "laptop", "keyboard",
    "phone", "cellphone", "television", "chair", "table", "sofa", "couch",
    "bed", "shoe", "bottle", "cup", "clock", "book", "ball", "guitar",
    "camera", "mouse", "remote", "backpack", "bag", "pizza", "cheeseburger",
    "hotdog", "sandwich", "cake",
}


# ============================================================
# LOAD IMAGENET MODEL
# ============================================================

def load_gatekeeper():
    """Load MobileNetV2 (ImageNet). Needs internet the first time (~14 MB)."""
    global _model
    try:
        from tensorflow.keras.applications import MobileNetV2
        _model = MobileNetV2(weights="imagenet", include_top=True)
        return True
    except Exception as e:
        print("Gatekeeper model could not be loaded:", e)
        _model = None
        return False


def is_loaded():
    return _model is not None


# ============================================================
# HELPERS
# ============================================================

def _open_rgb(image):
    if image is None:
        raise ValueError("No image was provided.")
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    image = ImageOps.exif_transpose(image)  # fix phone-photo rotation
    return image.convert("RGB")


def vegetation_ratio(image_rgb):
    """Share of pixels that are green / yellow-green (leaf colours)."""
    hsv = np.asarray(
        image_rgb.resize((224, 224)).convert("HSV"), dtype=np.float32
    )
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # PIL hue is 0-255 (360 degrees). 25..120 is about 35..170 degrees.
    mask = (h >= 25) & (h <= 120) & (s >= 45) & (v >= 40)
    return float(mask.mean())


def _result(accepted, reason, **details):
    return {"accepted": accepted, "reason": reason, "details": details}


# ============================================================
# MAIN CHECK
# ============================================================

def check_image(image):
    """
    Returns {"accepted": True/False, "reason": "...", "details": {...}}
    """
    try:
        img = _open_rgb(image)
    except Exception as e:
        return _result(False, f"Unable to read image: {e}")

    width, height = img.size
    if width < MIN_SIDE or height < MIN_SIDE:
        return _result(False, "Image is too small. Please upload a clear crop image.")

    if np.asarray(img, dtype=np.float32).std() < MIN_PIXEL_STD:
        return _result(False, "The uploaded image does not contain enough visual information.")

    green = vegetation_ratio(img)

    # ---- ImageNet model not available: green-colour check only ----
    if _model is None:
        if green >= FALLBACK_VEGETATION_RATIO:
            return _result(True, "Passed colour check (ImageNet model unavailable).",
                           vegetation=round(green, 3))
        return _result(False, "This image does not look like a plant leaf.",
                       vegetation=round(green, 3))

    from tensorflow.keras.applications.mobilenet_v2 import (
        preprocess_input, decode_predictions,
    )

    x = np.asarray(img.resize((224, 224)), dtype=np.float32)[None, ...]
    preds = _model.predict(preprocess_input(x), verbose=0)
    probs = preds[0]

    # ImageNet classes 0-397 are all animals; 981-983 are people.
    animal = max(float(probs[:398].max()), float(probs[981:984].max()))

    plant_score = 0.0
    nonplant_score = 0.0
    top5 = []
    for _, label, p in decode_predictions(preds, top=5)[0]:
        p = float(p)
        text = label.replace("_", " ").lower()
        top5.append(f"{text}={p:.2f}")
        words = set(text.split())
        if words & PLANT_WORDS:
            plant_score = max(plant_score, p)
        if words & NON_PLANT_WORDS:
            nonplant_score = max(nonplant_score, p)

    info = dict(
        vegetation=round(green, 3),
        plant_score=round(plant_score, 3),
        nonplant_score=round(nonplant_score, 3),
        animal_person_score=round(animal, 3),
        top5=top5,
    )

    if animal >= ANIMAL_PERSON_REJECT and animal > plant_score:
        return _result(False, "This looks like an animal or a person, not a crop leaf.", **info)

    if nonplant_score >= NON_PLANT_WORD_REJECT and nonplant_score > plant_score:
        return _result(False, "This looks like an object, not a crop leaf.", **info)

    if plant_score >= PLANT_WORD_ACCEPT:
        return _result(True, "Plant detected.", **info)

    if green >= MIN_VEGETATION_RATIO:
        return _result(True, "Leaf-like colours detected.", **info)

    return _result(False, "This image does not appear to contain a plant or crop.", **info)


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gatekeeper.py path\\to\\photo.jpg")
        sys.exit(1)
    print("Loading gatekeeper...", load_gatekeeper())
    out = check_image(sys.argv[1])
    print("ACCEPTED" if out["accepted"] else "REJECTED", "-", out["reason"])
    for k, v in out["details"].items():
        print(f"  {k}: {v}")
