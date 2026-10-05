"""
CropCare AI - 38-Class TFLite Backend

Uses:
    model/crop_disease_model.tflite
    model/labels.json

The backend uses LiteRT instead of full TensorFlow so that
the Render deployment uses much less memory.

Local:
    python app.py

Render:
    gunicorn app:app --workers 1 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT
"""

import os
import json
import traceback

import numpy as np
from PIL import Image, ImageOps

from flask import Flask, request, jsonify
from flask_cors import CORS

from ai_edge_litert.interpreter import Interpreter

import gatekeeper


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMG_SIZE = (224, 224)

MIN_CROP_CONFIDENCE = 60.0


MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "crop_disease_model.tflite"
)

LABELS_PATH = os.path.join(
    BASE_DIR,
    "model",
    "labels.json"
)


# ============================================================
# WEBSITE
# ============================================================

def find_site_dir():

    candidates = [
        os.path.join(BASE_DIR, "static"),
        os.path.join(BASE_DIR, "website"),
        os.path.join(BASE_DIR, "..", "website"),
    ]

    for path in candidates:
        if os.path.isdir(path):
            return path

    return None


SITE_DIR = find_site_dir()


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__,
    static_folder=SITE_DIR,
    static_url_path=""
)

CORS(app)

app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024


# ============================================================
# GLOBAL MODEL
# ============================================================

interpreter = None

input_details = None
output_details = None

class_names = []


# ============================================================
# LABEL HELPERS
# ============================================================

def tidy(text):
    return str(text).replace("_", " ").strip(" ,")


def get_crop_name(label):

    label = str(label)

    if "___" in label:
        return tidy(label.split("___", 1)[0])

    return tidy(label.split("_")[0])


def get_condition_name(label):

    label = str(label)

    if "___" in label:
        return tidy(label.split("___", 1)[1])

    return tidy(label)


def normalize_labels(data):

    if isinstance(data, list):
        return [str(x) for x in data]

    if isinstance(data, dict):

        for key in ("classes", "class_names"):

            if isinstance(data.get(key), list):
                return [str(x) for x in data[key]]

        numeric = []

        for key in data:

            try:
                numeric.append((int(key), key))
            except (ValueError, TypeError):
                pass

        if numeric:

            numeric.sort()

            return [
                str(data[key])
                for _, key in numeric
            ]

    raise ValueError("Unsupported labels.json format")


# ============================================================
# LOAD LABELS
# ============================================================

def load_labels():

    global class_names

    if not os.path.isfile(LABELS_PATH):
        raise FileNotFoundError(
            "labels.json not found: " + LABELS_PATH
        )

    with open(
        LABELS_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    class_names = normalize_labels(data)

    if len(class_names) != 38:

        raise ValueError(
            f"Expected 38 classes, but labels.json contains "
            f"{len(class_names)} classes."
        )

    print(f"Labels loaded: {len(class_names)} classes")


# ============================================================
# LOAD TFLITE MODEL
# ============================================================

def load_tflite_model():

    global interpreter
    global input_details
    global output_details

    if not os.path.isfile(MODEL_PATH):

        raise FileNotFoundError(
            "TFLite model not found: " + MODEL_PATH
        )

    print("Loading TFLite model:")
    print(MODEL_PATH)

    interpreter = Interpreter(
        model_path=MODEL_PATH,
        num_threads=2
    )

    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print("TFLite model loaded.")

    print(
        "Input shape:",
        input_details[0]["shape"]
    )

    print(
        "Input dtype:",
        input_details[0]["dtype"]
    )

    print(
        "Output shape:",
        output_details[0]["shape"]
    )

    print(
        "Output dtype:",
        output_details[0]["dtype"]
    )


# ============================================================
# LOAD EVERYTHING
# ============================================================

def load_everything():

    print("=" * 60)
    print("CropCare AI starting")
    print("=" * 60)

    try:

        load_labels()

    except Exception as e:

        print("ERROR loading labels:")
        print(e)

    try:

        load_tflite_model()

    except Exception as e:

        print("ERROR loading TFLite model:")
        print(e)

        traceback.print_exc()

    try:

        gatekeeper.load_gatekeeper()

    except Exception as e:

        print("ERROR loading gatekeeper:")
        print(e)

    print("-" * 60)

    print(
        "Model loaded:     ",
        interpreter is not None
    )

    print(
        "Gatekeeper loaded:",
        gatekeeper.is_loaded()
    )

    print(
        "Classes:          ",
        len(class_names)
    )

    print(
        "Website folder:   ",
        SITE_DIR
    )

    print("=" * 60)


load_everything()


# ============================================================
# ADVICE
# ============================================================

HEALTHY = {

    "summary":
        "The crop appears healthy based on the model prediction.",

    "symptoms": [
        "No major disease pattern detected.",
        "Leaves appear relatively normal.",
        "Continue monitoring the crop regularly."
    ],

    "advice": [
        "Continue normal crop care.",
        "Maintain suitable irrigation.",
        "Monitor new leaves for changes."
    ],

    "prevention": [
        "Keep the field clean.",
        "Avoid excessive moisture on leaves.",
        "Inspect plants regularly."
    ],
}


ADVICE_BY_KEYWORD = [

    (
        "late blight",
        {
            "summary":
                "A fungal-like disease that can damage leaves and reduce yield if it spreads.",

            "symptoms": [
                "Dark or irregular spots on leaves.",
                "Yellowing around affected areas.",
                "Rapid spread during humid conditions."
            ],

            "advice": [
                "Remove badly affected leaves.",
                "Improve air circulation around plants.",
                "Avoid overhead watering.",
                "Follow local agricultural guidance."
            ],

            "prevention": [
                "Keep leaves dry where possible.",
                "Remove infected plant debris.",
                "Give plants adequate spacing."
            ],
        }
    ),

    (
        "early blight",
        {
            "summary":
                "A fungal disease that commonly causes spots and leaf damage.",

            "symptoms": [
                "Brown or dark spots on leaves.",
                "Concentric ring patterns may appear.",
                "Older leaves may be affected first."
            ],

            "advice": [
                "Remove severely affected leaves.",
                "Improve air circulation.",
                "Avoid wetting foliage unnecessarily."
            ],

            "prevention": [
                "Use clean planting material.",
                "Remove crop debris.",
                "Rotate crops where practical."
            ],
        }
    ),

    (
        "rust",
        {
            "summary":
                "Rust disease can produce characteristic spots or pustules on leaves.",

            "symptoms": [
                "Orange, brown or reddish spots.",
                "Powder-like growth may appear.",
                "Leaves can become weak or yellow."
            ],

            "advice": [
                "Remove severely infected leaves.",
                "Improve airflow.",
                "Avoid prolonged leaf wetness."
            ],

            "prevention": [
                "Keep the field clean.",
                "Use healthy planting material.",
                "Monitor plants regularly."
            ],
        }
    ),

    (
        "mildew",
        {
            "summary":
                "Mildew can produce visible fungal growth and weaken affected leaves.",

            "symptoms": [
                "White or powdery growth.",
                "Yellowing leaves.",
                "Reduced plant vigor."
            ],

            "advice": [
                "Improve ventilation.",
                "Remove badly affected foliage.",
                "Avoid unnecessary leaf moisture."
            ],

            "prevention": [
                "Maintain adequate plant spacing.",
                "Monitor humidity.",
                "Remove infected debris."
            ],
        }
    ),
]


def get_advice(condition):

    condition_lower = str(condition).lower()

    if "healthy" in condition_lower:
        return HEALTHY

    for keyword, advice in ADVICE_BY_KEYWORD:

        if keyword in condition_lower:
            return advice

    return {

        "summary":
            f"The model detected {condition}. "
            "Treat this result as an AI-assisted indication "
            "rather than a laboratory diagnosis.",

        "symptoms": [
            "Spots or patches may appear on affected leaves.",
            "Leaves may show discoloration.",
            "Plant growth may be reduced."
        ],

        "advice": [
            "Inspect the affected plant closely.",
            "Remove severely damaged plant material where appropriate.",
            "Improve field hygiene and airflow.",
            "Follow local agricultural guidance."
        ],

        "prevention": [
            "Use healthy planting material.",
            "Keep the growing area clean.",
            "Monitor crops regularly."
        ],
    }


# ============================================================
# ALTERNATIVE PREDICTIONS
# ============================================================

def get_alternatives(probabilities, best_index):

    alternatives = []

    indices = np.argsort(probabilities)[::-1]

    for index in indices:

        index = int(index)

        if index == best_index:
            continue

        if index >= len(class_names):
            continue

        alternatives.append({

            "crop":
                get_crop_name(class_names[index]),

            "condition":
                get_condition_name(class_names[index]),

            "confidence":
                round(
                    float(probabilities[index]) * 100,
                    1
                ),
        })

        if len(alternatives) >= 3:
            break

    return alternatives


# ============================================================
# TFLITE PREDICTION
# ============================================================

def run_model(image):

    """
    Run the TFLite model.

    The model was trained with MobileNetV2 preprocessing
    inside the Keras model, so raw 0-255 float32 pixels
    are supplied here.
    """

    img = ImageOps.exif_transpose(
        image
    ).convert("RGB").resize(IMG_SIZE)

    arr = np.asarray(
        img,
        dtype=np.float32
    )

    arr = np.expand_dims(
        arr,
        axis=0
    )

    input_info = input_details[0]

    input_index = input_info["index"]

    input_dtype = input_info["dtype"]

    # --------------------------------------------------------
    # FLOAT MODEL
    # --------------------------------------------------------

    if input_dtype == np.float32:

        model_input = arr.astype(np.float32)

    # --------------------------------------------------------
    # QUANTIZED MODEL
    # --------------------------------------------------------

    else:

        scale, zero_point = input_info["quantization"]

        if scale == 0:
            raise ValueError(
                "Invalid TFLite input quantization."
            )

        model_input = (
            arr / scale + zero_point
        ).astype(input_dtype)

    interpreter.set_tensor(
        input_index,
        model_input
    )

    interpreter.invoke()

    output = interpreter.get_tensor(
        output_details[0]["index"]
    )

    output = np.asarray(
        output,
        dtype=np.float32
    )[0]

    # --------------------------------------------------------
    # DEQUANTIZE OUTPUT IF NEEDED
    # --------------------------------------------------------

    output_info = output_details[0]

    output_scale, output_zero = (
        output_info["quantization"]
    )

    if (
        output_info["dtype"] != np.float32
        and output_scale != 0
    ):

        output = (
            output - output_zero
        ) * output_scale

    # --------------------------------------------------------
    # NORMALIZE SAFELY
    # --------------------------------------------------------

    total = float(np.sum(output))

    if (
        total > 0
        and (
            np.min(output) < 0
            or np.max(output) > 1.0
            or abs(total - 1.0) > 0.05
        )
    ):

        # Softmax
        shifted = output - np.max(output)

        exp_values = np.exp(shifted)

        output = (
            exp_values /
            np.sum(exp_values)
        )

    return output


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if (
        SITE_DIR
        and os.path.isfile(
            os.path.join(
                SITE_DIR,
                "index.html"
            )
        )
    ):

        return app.send_static_file(
            "index.html"
        )

    return jsonify({

        "ok": False,

        "message":
            "Website files are missing.",

        "solution":
            "Put index.html inside the static folder.",

    }), 500


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "ok": True,

        "message":
            "CropCare AI backend is running.",

        "model_loaded":
            interpreter is not None,

        "gatekeeper_loaded":
            gatekeeper.is_loaded(),

        "classes":
            len(class_names),

        "model_type":
            "TFLite / LiteRT",

        "model_file":
            os.path.basename(MODEL_PATH),

        "website_found":
            SITE_DIR is not None,

        "website_index_found":
            bool(
                SITE_DIR
                and os.path.isfile(
                    os.path.join(
                        SITE_DIR,
                        "index.html"
                    )
                )
            ),
    })


# ============================================================
# CLASSES
# ============================================================

@app.route("/classes")
def classes():

    return jsonify({

        "ok": True,

        "count":
            len(class_names),

        "classes":
            class_names,

    })


# ============================================================
# PREDICT
# ============================================================

@app.route(
    "/predict",
    methods=["POST"]
)
def predict():

    try:

        # ----------------------------------------------------
        # MODEL CHECK
        # ----------------------------------------------------

        if interpreter is None:

            return jsonify({

                "ok": False,

                "code": "model",

                "reason":
                    "Crop disease TFLite model is not loaded.",

            }), 500

        # ----------------------------------------------------
        # IMAGE CHECK
        # ----------------------------------------------------

        if "image" not in request.files:

            return jsonify({

                "ok": False,

                "code": "image",

                "reason":
                    "No image was uploaded.",

            }), 400

        file = request.files["image"]

        if file.filename == "":

            return jsonify({

                "ok": False,

                "code": "image",

                "reason":
                    "No image file was selected.",

            }), 400

        # ----------------------------------------------------
        # OPEN IMAGE
        # ----------------------------------------------------

        try:

            image = Image.open(
                file.stream
            )

            image.load()

        except Exception:

            return jsonify({

                "ok": False,

                "code": "invalid_image",

                "reason":
                    "The uploaded file is not a valid image.",

            }), 400

        # ----------------------------------------------------
        # GATEKEEPER
        # ----------------------------------------------------

        gk = gatekeeper.check_image(
            image
        )

        print(
            "GATEKEEPER:",
            "ACCEPT"
            if gk["accepted"]
            else "REJECT",
            "-",
            gk["reason"],
            gk.get("details", {})
        )

        if not gk["accepted"]:

            return jsonify({

                "ok": False,

                "rejected": True,

                "code":
                    "non_plant_image",

                "reason":
                    gk["reason"],

                "message":
                    "Image rejected by CropCare AI gatekeeper.",

            }), 422

        # ----------------------------------------------------
        # DISEASE MODEL
        # ----------------------------------------------------

        probabilities = run_model(
            image
        )

        # ----------------------------------------------------
        # CLASS CHECK
        # ----------------------------------------------------

        if len(probabilities) != len(class_names):

            return jsonify({

                "ok": False,

                "code":
                    "class_mismatch",

                "reason":
                    "TFLite model output count does not match labels.json.",

                "model_outputs":
                    len(probabilities),

                "labels":
                    len(class_names),

            }), 500

        # ----------------------------------------------------
        # BEST CLASS
        # ----------------------------------------------------

        best = int(
            np.argmax(probabilities)
        )

        confidence = (
            float(probabilities[best])
            * 100
        )

        raw_label = class_names[best]

        crop = get_crop_name(
            raw_label
        )

        condition = get_condition_name(
            raw_label
        )

        print(
            "PREDICTION:",
            raw_label,
            "| confidence:",
            round(confidence, 2)
        )

        # ----------------------------------------------------
        # LOW CONFIDENCE
        # ----------------------------------------------------

        if confidence < MIN_CROP_CONFIDENCE:

            return jsonify({

                "ok": False,

                "rejected": True,

                "code":
                    "low_confidence",

                "reason":
                    "The image passed the plant check, "
                    "but the crop disease model is not "
                    "confident enough.",

                "confidence":
                    round(confidence, 1),

                "message":
                    "Please upload a clearer image "
                    "of the affected crop leaf.",

            }), 422

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return jsonify({

            "ok": True,

            "success": True,

            "rejected": False,

            "crop":
                crop,

            "condition":
                condition,

            "label":
                raw_label,

            "confidence":
                round(confidence, 1),

            "advice":
                get_advice(condition),

            "alternatives":
                get_alternatives(
                    probabilities,
                    best
                ),

        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "ok": False,

            "code":
                "server_error",

            "reason":
                str(e),

        }), 500


# ============================================================
# LOCAL RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print(
        f"Website: http://127.0.0.1:{port}/"
    )

    print(
        f"Health: http://127.0.0.1:{port}/health"
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
