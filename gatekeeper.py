import os
import json
import numpy as np
from PIL import Image, ImageOps

try:
    from ai_edge_litert.interpreter import Interpreter
except Exception:
    Interpreter = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")

GATEKEEPER_MODEL = os.path.join(MODEL_DIR, "gatekeeper.tflite")
LABELS_FILE = os.path.join(MODEL_DIR, "imagenet_labels.json")

interpreter = None
input_details = None
output_details = None
labels = []

# Objects that should NEVER be accepted as crop/plant images.
REJECT_WORDS = {
    "cat",
    "dog",
    "person",
    "man",
    "woman",
    "boy",
    "girl",
    "human",
    "car",
    "truck",
    "bus",
    "motorcycle",
    "bicycle",
    "airplane",
    "boat",
    "bird",
    "horse",
    "cow",
    "sheep",
    "elephant",
    "bear",
    "tiger",
    "lion",
    "monkey",
    "rabbit",
    "fish",
    "phone",
    "laptop",
    "computer",
    "keyboard",
    "mouse",
    "television",
    "chair",
    "table",
    "bed",
    "sofa",
    "couch",
    "shoe",
    "bag",
    "backpack",
    "bottle",
    "cup",
    "clock",
    "book",
    "ball",
    "football",
    "basketball",
    "umbrella",
    "building",
    "house",
    "street",
    "road",
}

# ImageNet labels that are clearly plant-related.
PLANT_WORDS = {
    "plant",
    "tree",
    "leaf",
    "flower",
    "fruit",
    "vegetable",
    "mushroom",
    "cabbage",
    "cauliflower",
    "broccoli",
    "corn",
    "maize",
    "potato",
    "tomato",
    "pepper",
    "bell_pepper",
    "cucumber",
    "zucchini",
    "pumpkin",
    "orange",
    "lemon",
    "banana",
    "apple",
    "pineapple",
    "strawberry",
    "fig",
    "pomegranate",
    "acorn",
    "coffee",
    "bean",
    "pod",
    "daisy",
    "sunflower",
    "rose",
    "dandelion",
    "lily",
    "orchid",
    "violet",
    "bouquet",
    "pot",
    "garden",
    "vine",
    "fungus",
}


def load_gatekeeper():
    global interpreter
    global input_details
    global output_details
    global labels

    if Interpreter is None:
        raise RuntimeError(
            "ai_edge_litert is not installed."
        )

    if not os.path.exists(GATEKEEPER_MODEL):
        raise FileNotFoundError(
            f"Gatekeeper model not found: {GATEKEEPER_MODEL}"
        )

    if not os.path.exists(LABELS_FILE):
        raise FileNotFoundError(
            f"Gatekeeper labels not found: {LABELS_FILE}"
        )

    with open(LABELS_FILE, "r", encoding="utf-8") as f:
        labels = json.load(f)

    interpreter = Interpreter(
        model_path=GATEKEEPER_MODEL,
        num_threads=2,
    )

    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print("TFLite gatekeeper loaded.")
    print("Gatekeeper model:", GATEKEEPER_MODEL)
    print("Gatekeeper labels:", len(labels))
    print("Gatekeeper input:", input_details[0]["shape"])
    print("Gatekeeper dtype:", input_details[0]["dtype"])


def is_loaded():
    return interpreter is not None


def _label_name(index):
    if index < 0 or index >= len(labels):
        return ""

    item = labels[index]

    if isinstance(item, dict):
        return str(item.get("name", "")).lower()

    return str(item).lower()


def _prepare_image(image):
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = image.resize((224, 224))

    arr = np.asarray(image, dtype=np.float32)

    # MobileNetV2 preprocessing:
    # 0..255 -> -1..1
    arr = (arr / 127.5) - 1.0

    arr = np.expand_dims(arr, axis=0)

    return arr


def _run_classifier(image):
    arr = _prepare_image(image)

    detail = input_details[0]

    # Handle model input dtype.
    if detail["dtype"] != np.float32:
        scale, zero_point = detail["quantization"]

        if scale and scale > 0:
            arr = arr / scale + zero_point

        arr = arr.astype(detail["dtype"])

    interpreter.set_tensor(
        detail["index"],
        arr,
    )

    interpreter.invoke()

    output = interpreter.get_tensor(
        output_details[0]["index"]
    )

    output = np.asarray(
        output,
        dtype=np.float32,
    ).reshape(-1)

    # Dequantize output if necessary.
    scale, zero_point = output_details[0]["quantization"]

    if scale and scale > 0:
        output = (output - zero_point) * scale

    # Convert logits to probabilities if required.
    if (
        np.min(output) < 0
        or np.max(output) > 1.0
        or abs(float(np.sum(output)) - 1.0) > 0.05
    ):
        output = output - np.max(output)
        exp_output = np.exp(output)
        output = exp_output / np.sum(exp_output)

    top_indices = np.argsort(output)[::-1][:10]

    results = []

    for index in top_indices:
        results.append(
            {
                "index": int(index),
                "label": _label_name(int(index)),
                "confidence": float(output[index]),
            }
        )

    return results


def _contains_word(label, words):
    label = label.lower().replace("-", "_").replace(" ", "_")

    for word in words:
        if word in label:
            return True

    return False


def check_image(image):
    """
    Check whether an uploaded image looks acceptable
    for crop-disease analysis.

    Uses MobileNetV2/ImageNet classification rather than
    simple green-pixel detection.
    """

    if not is_loaded():
        return {
            "accepted": False,
            "reason": "Gatekeeper model is not loaded.",
            "details": {},
        }

    try:
        results = _run_classifier(image)

        if not results:
            return {
                "accepted": False,
                "reason": "Unable to classify the image.",
                "details": {},
            }

        top = results[0]

        top_label = top["label"]
        top_conf = top["confidence"]

        # ------------------------------------------------
        # STRONG NON-PLANT REJECTION
        # ------------------------------------------------

        for result in results[:10]:
            label = result["label"]
            confidence = result["confidence"]

            if _contains_word(label, REJECT_WORDS):
                if confidence >= 0.10:
                    return {
                        "accepted": False,
                        "reason": "The image does not appear to be a crop or plant.",
                        "details": {
                            "detected": label,
                            "confidence": round(confidence * 100, 2),
                            "top_predictions": results[:5],
                        },
                    }

        # ------------------------------------------------
        # PLANT DETECTION
        # ------------------------------------------------

        plant_found = False
        plant_confidence = 0.0

        for result in results[:10]:
            label = result["label"]

            if _contains_word(label, PLANT_WORDS):
                plant_found = True
                plant_confidence = max(
                    plant_confidence,
                    result["confidence"],
                )

        # If ImageNet strongly sees a non-plant object,
        # reject it.
        if top_conf >= 0.35 and not plant_found:
            return {
                "accepted": False,
                "reason": "The image does not appear to contain a crop or plant.",
                "details": {
                    "detected": top_label,
                    "confidence": round(top_conf * 100, 2),
                    "top_predictions": results[:5],
                },
            }

        # Otherwise allow the crop model to perform
        # the final disease classification.
        return {
            "accepted": True,
            "reason": "Image passed the gatekeeper.",
            "details": {
                "detected": top_label,
                "confidence": round(top_conf * 100, 2),
                "plant_confidence": round(
                    plant_confidence * 100,
                    2,
                ),
                "top_predictions": results[:5],
            },
        }

    except Exception as e:
        return {
            "accepted": False,
            "reason": f"Gatekeeper error: {str(e)}",
            "details": {},
        }


if __name__ == "__main__":
    load_gatekeeper()

    print("Gatekeeper ready.")
