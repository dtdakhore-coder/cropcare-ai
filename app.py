"""
CropCare AI - 38-class crop disease prediction + image gatekeeper
Run locally:  python app.py      (then open http://127.0.0.1:5000)
Render:       gunicorn app:app --workers 1 --timeout 180
"""

import os
import json
import traceback

import numpy as np
from PIL import Image, ImageOps
from flask import Flask, request, jsonify
from flask_cors import CORS
from tensorflow.keras.models import load_model

import gatekeeper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMG_SIZE = (224, 224)
MIN_CROP_CONFIDENCE = 60.0   # % - below this the result is rejected as unsure


# ============================================================
# FIND FILES
# ============================================================

def first_existing(candidates, folder=False):
    check = os.path.isdir if folder else os.path.isfile
    for path in candidates:
        path = os.path.abspath(path)
        if check(path):
            return path
    return None


MODEL_PATH = first_existing([
    os.path.join(BASE_DIR, "model", "crop_disease_model.keras"),
    os.path.join(BASE_DIR, "model", "crop_disease_model.h5"),
    os.path.join(BASE_DIR, "crop_disease_model.keras"),
    os.path.join(BASE_DIR, "crop_disease_model.h5"),
])

LABELS_PATH = first_existing([
    os.path.join(BASE_DIR, "model", "labels.json"),
    os.path.join(BASE_DIR, "labels.json"),
])

# README says the website lives in static/
SITE_DIR = first_existing([
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "website"),
    os.path.join(BASE_DIR, "..", "website"),
], folder=True)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__, static_folder=SITE_DIR, static_url_path="")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

model = None
class_names = []


# ============================================================
# LABEL HELPERS
# ============================================================

def _tidy(text):
    return text.replace("_", " ").strip(" ,")


def get_crop_name(label):
    label = str(label)
    if "___" in label:
        return _tidy(label.split("___", 1)[0])
    return _tidy(label.split("_")[0])


def get_condition_name(label):
    label = str(label)
    if "___" in label:
        return _tidy(label.split("___", 1)[1])
    return _tidy(label)


def normalize_labels(data):
    if isinstance(data, list):
        return [str(x) for x in data]
    if isinstance(data, dict):
        for key in ("classes", "class_names"):
            if isinstance(data.get(key), list):
                return [str(x) for x in data[key]]
        numeric = []
        for k in data:
            try:
                numeric.append((int(k), k))
            except ValueError:
                pass
        if numeric:
            return [str(data[k]) for _, k in sorted(numeric)]
    raise ValueError("Unsupported labels.json format")


# ============================================================
# LOAD EVERYTHING (runs on import, so gunicorn loads it too)
# ============================================================

def load_everything():
    global model, class_names

    print("=" * 60)
    print("CropCare AI starting")
    print("=" * 60)

    try:
        if not LABELS_PATH:
            raise FileNotFoundError("labels.json not found (put it in model/)")
        with open(LABELS_PATH, "r", encoding="utf-8") as f:
            class_names = normalize_labels(json.load(f))
        print(f"Labels: {len(class_names)} classes")
    except Exception as e:
        print("ERROR loading labels:", e)

    try:
        if not MODEL_PATH:
            raise FileNotFoundError(
                "crop_disease_model.keras / .h5 not found (put it in model/)")
        print("Loading model:", MODEL_PATH)
        model = load_model(MODEL_PATH, compile=False)
        print("Crop model loaded.")
    except Exception as e:
        print("ERROR loading crop model:", e)
        traceback.print_exc()

    gk = gatekeeper.load_gatekeeper()

    print("-" * 60)
    print("Model loaded:     ", model is not None)
    print("Gatekeeper loaded:", gk)
    print("Website folder:   ", SITE_DIR)
    print("=" * 60)


load_everything()


# ============================================================
# ADVICE
# ============================================================

HEALTHY = {
    "summary": "The crop appears healthy based on the model prediction.",
    "symptoms": ["No major disease pattern detected.",
                 "Leaves appear relatively normal.",
                 "Continue monitoring the crop regularly."],
    "advice": ["Continue normal crop care.", "Maintain suitable irrigation.",
               "Monitor new leaves for changes."],
    "prevention": ["Keep the field clean.",
                   "Avoid excessive moisture on leaves.",
                   "Inspect plants regularly."],
}

ADVICE_BY_KEYWORD = [
    ("late blight", {
        "summary": "A fungal-like disease that can damage leaves and reduce yield if it spreads.",
        "symptoms": ["Dark or irregular spots on leaves.",
                     "Yellowing around affected areas.",
                     "Rapid spread during humid conditions."],
        "advice": ["Remove badly affected leaves.",
                   "Improve air circulation around plants.",
                   "Avoid overhead watering.",
                   "Follow local agricultural guidance."],
        "prevention": ["Keep leaves dry where possible.",
                       "Remove infected plant debris.",
                       "Give plants adequate spacing."],
    }),
    ("early blight", {
        "summary": "A fungal disease that commonly causes spots and leaf damage.",
        "symptoms": ["Brown or dark spots on leaves.",
                     "Concentric ring patterns may appear.",
                     "Older leaves may be affected first."],
        "advice": ["Remove severely affected leaves.",
                   "Improve air circulation.",
                   "Avoid wetting foliage unnecessarily."],
        "prevention": ["Use clean planting material.",
                       "Remove crop debris.",
                       "Rotate crops where practical."],
    }),
    ("rust", {
        "summary": "Rust disease can produce characteristic spots or pustules on leaves.",
        "symptoms": ["Orange, brown or reddish spots.",
                     "Powder-like growth may appear.",
                     "Leaves can become weak or yellow."],
        "advice": ["Remove severely infected leaves.", "Improve airflow.",
                   "Avoid prolonged leaf wetness."],
        "prevention": ["Keep the field clean.",
                       "Use healthy planting material.",
                       "Monitor plants regularly."],
    }),
    ("mildew", {
        "summary": "Mildew can produce visible fungal growth and weaken affected leaves.",
        "symptoms": ["White or powdery growth.", "Yellowing leaves.",
                     "Reduced plant vigor."],
        "advice": ["Improve ventilation.", "Remove badly affected foliage.",
                   "Avoid unnecessary leaf moisture."],
        "prevention": ["Maintain adequate plant spacing.", "Monitor humidity.",
                       "Remove infected debris."],
    }),
]


def get_advice(condition):
    c = str(condition).lower()
    if "healthy" in c:
        return HEALTHY
    for keyword, advice in ADVICE_BY_KEYWORD:
        if keyword in c:
            return advice
    return {
        "summary": (f"The model detected {condition}. Treat this result as an "
                    "AI-assisted indication rather than a laboratory diagnosis."),
        "symptoms": ["Spots or patches may appear on affected leaves.",
                     "Leaves may show discoloration.",
                     "Plant growth may be reduced."],
        "advice": ["Inspect the affected plant closely.",
                   "Remove severely damaged plant material where appropriate.",
                   "Improve field hygiene and airflow.",
                   "Follow local agricultural guidance."],
        "prevention": ["Use healthy planting material.",
                       "Keep the growing area clean.",
                       "Monitor crops regularly."],
    }


def get_alternatives(probabilities, best_index):
    out = []
    for i in np.argsort(probabilities)[::-1]:
        i = int(i)
        if i == best_index or i >= len(class_names):
            continue
        out.append({
            "crop": get_crop_name(class_names[i]),
            "condition": get_condition_name(class_names[i]),
            "confidence": round(float(probabilities[i] * 100), 1),
        })
        if len(out) >= 3:
            break
    return out


# ============================================================
# ROUTES
# (other pages such as /analyze.html are served automatically
#  from the static folder)
# ============================================================

@app.route("/")
def home():
    if SITE_DIR and os.path.isfile(os.path.join(SITE_DIR, "index.html")):
        return app.send_static_file("index.html")
    return jsonify({
        "ok": False,
        "message": "Website files are missing.",
        "solution": "Put index.html and the other pages inside the static folder.",
    }), 500


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "message": "CropCare AI backend is running.",
        "model_loaded": model is not None,
        "gatekeeper_loaded": gatekeeper.is_loaded(),
        "classes": len(class_names),
        "website_found": SITE_DIR is not None,
        "website_index_found": bool(
            SITE_DIR and os.path.isfile(os.path.join(SITE_DIR, "index.html"))),
    })


@app.route("/classes")
def classes():
    return jsonify({"ok": True, "count": len(class_names), "classes": class_names})


@app.route("/predict", methods=["POST"])
def predict():
    try:
        if model is None:
            return jsonify({"ok": False, "code": "model",
                            "reason": "Crop disease model is not loaded."}), 500

        if "image" not in request.files:
            return jsonify({"ok": False, "code": "image",
                            "reason": "No image was uploaded."}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"ok": False, "code": "image",
                            "reason": "No image file was selected."}), 400

        try:
            image = Image.open(file.stream)
            image.load()
        except Exception:
            return jsonify({"ok": False, "code": "invalid_image",
                            "reason": "The uploaded file is not a valid image."}), 400

        # ---- gatekeeper ----
        gk = gatekeeper.check_image(image)
        print("GATEKEEPER:", "ACCEPT" if gk["accepted"] else "REJECT",
              "-", gk["reason"], gk.get("details", {}))
        if not gk["accepted"]:
            return jsonify({
                "ok": False,
                "rejected": True,
                "code": "non_plant_image",
                "reason": gk["reason"],
                "message": "Image rejected by CropCare AI gatekeeper.",
            }), 422

        # ---- disease model (the model has its own Rescaling layer,
        #      so it takes raw 0-255 pixels) ----
        img = ImageOps.exif_transpose(image).convert("RGB").resize(IMG_SIZE)
        arr = np.expand_dims(np.asarray(img, dtype=np.float32), axis=0)
        probabilities = np.asarray(model.predict(arr, verbose=0)[0], dtype=np.float32)

        if len(probabilities) != len(class_names):
            return jsonify({
                "ok": False, "code": "class_mismatch",
                "reason": "Model output count does not match labels.json.",
                "model_outputs": len(probabilities), "labels": len(class_names),
            }), 500

        best = int(np.argmax(probabilities))
        confidence = float(probabilities[best] * 100)
        raw_label = class_names[best]
        condition = get_condition_name(raw_label)

        if confidence < MIN_CROP_CONFIDENCE:
            return jsonify({
                "ok": False, "rejected": True, "code": "low_confidence",
                "reason": "The image passed the plant check, but the crop disease "
                          "model is not confident enough.",
                "confidence": round(confidence, 1),
                "message": "Please upload a clearer image of the affected crop leaf.",
            }), 422

        return jsonify({
            "ok": True,
            "rejected": False,
            "crop": get_crop_name(raw_label),
            "condition": condition,
            "label": raw_label,
            "confidence": round(confidence, 1),
            "advice": get_advice(condition),
            "alternatives": get_alternatives(probabilities, best),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "code": "server_error", "reason": str(e)}), 500


# ============================================================
# RUN (local only - Render uses gunicorn)
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Website: http://127.0.0.1:{port}/")
    print(f"Health:  http://127.0.0.1:{port}/health")
    app.run(host="0.0.0.0", port=port, debug=False)
