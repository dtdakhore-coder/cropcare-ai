# Run each block as a separate Colab cell. Runtime > Change runtime type > GPU.

# --- Cell 1: Kaggle download (upload kaggle.json when prompted)
!pip install -q kaggle
from google.colab import files
files.upload()
!mkdir -p ~/.kaggle && cp kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json
!kaggle datasets download -d vipoooool/new-plant-diseases-dataset
!unzip -q new-plant-diseases-dataset.zip -d data

# --- Cell 2: load data
import tensorflow as tf, json
print("TF version:", tf.__version__)   # put this SAME version in requirements.txt (tensorflow-cpu==...)
base = "data/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)"
train = tf.keras.utils.image_dataset_from_directory(f"{base}/train", image_size=(224, 224), batch_size=32)
val = tf.keras.utils.image_dataset_from_directory(f"{base}/valid", image_size=(224, 224), batch_size=32)
class_names = train.class_names
print(len(class_names))  # expect 38
json.dump(class_names, open("labels.json", "w"))

# --- Cell 3: build the model (augmentation is only active while training)
augment = tf.keras.Sequential([
    tf.keras.layers.RandomFlip("horizontal_and_vertical"),
    tf.keras.layers.RandomRotation(0.25),
    tf.keras.layers.RandomZoom(0.25),
    tf.keras.layers.RandomBrightness(0.3, value_range=(0, 255)),
    tf.keras.layers.RandomContrast(0.3),
])

base_model = tf.keras.applications.MobileNetV2(
    input_shape=(224, 224, 3), include_top=False, weights="imagenet")
base_model.trainable = False

inputs = tf.keras.Input(shape=(224, 224, 3))
x = augment(inputs)
x = tf.keras.layers.Rescaling(1. / 127.5, offset=-1)(x)   # model takes raw 0-255 pixels
x = base_model(x, training=False)
x = tf.keras.layers.GlobalAveragePooling2D()(x)
x = tf.keras.layers.Dropout(0.3)(x)
outputs = tf.keras.layers.Dense(38, activation="softmax")(x)
model = tf.keras.Model(inputs, outputs)

# --- Cell 4: stage 1 - train only the new top layers
model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model.fit(train, validation_data=val, epochs=5)

# --- Cell 5: stage 2 - fine-tune the last 40 layers of MobileNetV2 slowly
base_model.trainable = True
for layer in base_model.layers[:-40]:
    layer.trainable = False
model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model.fit(train, validation_data=val, epochs=5)

# --- Cell 6: check accuracy, then save
loss, acc = model.evaluate(val)
print("Validation accuracy:", acc)   # about 0.95+ means the pipeline is fine
model.save("crop_disease_model.keras")

# --- Cell 7: download
files.download("crop_disease_model.keras")
files.download("labels.json")
