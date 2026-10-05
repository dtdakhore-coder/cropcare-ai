# CropCare AI

Upload a leaf photo, get the crop and disease (38 classes, PlantVillage). A gatekeeper rejects
photos that aren't plants (animals, people, objects).

## Folder layout
```
app.py  gatekeeper.py  requirements.txt  render.yaml  Procfile
model/crop_disease_model.keras   model/labels.json
static/   index.html analyze.html how-it-works.html diseases.html faq.html about.html
          css/  js/  img/
```
`static/` is served by Flask. Language choices (English, Marathi, Hindi) are saved in the browser.
To host the frontend on a different domain, set `window.API_BASE` to the backend URL before
`js/analyze.js` loads.

## Train the model (Colab)
1. Run the cells in `colab_training.py` (GPU runtime). Note the `TF version` it prints.
2. Download `crop_disease_model.keras` and `labels.json` and put them in `model/`.
3. Set `tensorflow-cpu==<that version>` in `requirements.txt`.

## Run locally (Command Prompt, Python 3.10 or 3.11)
```
py -3.10 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 and check http://127.0.0.1:5000/health
(`model_loaded`, `gatekeeper_loaded`, `website_index_found` should all be true).

Test the gatekeeper alone:
```
python gatekeeper.py path\to\photo.jpg
```

## Deploy
Push to GitHub. Render redeploys automatically
(build: `pip install -r requirements.txt`, start: `gunicorn app:app --workers 1 --timeout 180`).

## Notes
- If the model file is over 100 MB, use Git LFS for it.
- Gatekeeper thresholds are at the top of `gatekeeper.py`; the minimum disease confidence
  (`MIN_CROP_CONFIDENCE`) is at the top of `app.py`.
- The model is trained on PlantVillage lab-style photos, so real field photos are less accurate.
  Results are an AI indication, not a diagnosis.
- Render's free plan has 512 MB RAM, which is tight for TensorFlow. If the service crashes on
  the first prediction, upgrade the instance.
