const API_URL = "/predict";

const $ = id => document.getElementById(id);

const esc = s =>
String(s ?? "").replace(/[&<>"]/g, c => ({
"&": "&",
"<": "<",
">": ">",
'"': """
}[c]));

// Elements
const fileInput = $("fileInput");
const chooseBtn = $("chooseBtn");
const dropZone = $("dropZone");
const previewWrap = $("previewWrap");
const previewImg = $("previewImg");
const fileName = $("fileName");
const removeBtn = $("removeBtn");
const analyzeBtn = $("analyzeBtn");

const progressBox = $("progressBox");
const progressBar = $("progressBar");
const progressText = $("progressText");

const resultSection = $("resultSection");
const rejectionSection = $("rejectionSection");
const resultImg = $("resultImg");

const diseaseName = $("diseaseName");
const confidenceValue = $("confidenceValue");
const confidenceBadge = $("confidenceBadge");
const confidenceBar = $("confidenceBar");
const diseaseSummary = $("diseaseSummary");

const tryAgainBtn = $("tryAgainBtn");

let selectedFile = null;
let redraw = null;

/* ============================================================
LANGUAGE
============================================================ */

function applyAnalyzeText() {

if (typeof CC === "undefined") return;

const set = (id, value) => {
const el = $(id);
if (el) el.textContent = value;
};

set("upT", CC.g("upT"));
set("chooseBtn", CC.g("choose"));
set("analyzeBtn", "🔬 " + CC.g("go"));
set("removeBtn", CC.g("change"));

set("lblConf", CC.g("conf"));
set("lblClass", CC.pc[CC.lang()] || CC.pc.en);

set("tryAgainBtn", CC.g("retry"));

set("hSym", CC.g("sy"));
set("hAct", CC.g("ac"));
set("hPrev", CC.g("pv"));

const stages = CC.g("stages");

if (stages && stages.length) {
set("progressLabel", stages[0]);
}
}

/* ============================================================
FILE SELECTION
============================================================ */

chooseBtn?.addEventListener("click", () => {
fileInput?.click();
});

dropZone?.addEventListener("click", e => {

if (e.target.closest("button")) return;

fileInput?.click();
});

fileInput?.addEventListener("change", e => {
setFile(e.target.files?.[0]);
});

["dragenter", "dragover"].forEach(eventName => {

dropZone?.addEventListener(eventName, e => {

e.preventDefault();
dropZone.classList.add("dragging");

});

});

["dragleave", "drop"].forEach(eventName => {

dropZone?.addEventListener(eventName, e => {

e.preventDefault();
dropZone.classList.remove("dragging");

});

});

dropZone?.addEventListener("drop", e => {
setFile(e.dataTransfer.files?.[0]);
});

removeBtn?.addEventListener("click", resetAnalyzer);
tryAgainBtn?.addEventListener("click", resetAnalyzer);

/* ============================================================
SET IMAGE
============================================================ */

function setFile(file) {

if (!file) return;

if (!file.type || !file.type.startsWith("image/")) {

alert("Please select an image file.");
return;

}

selectedFile = file;

if (fileName) {
fileName.textContent = file.name;
}

const reader = new FileReader();

reader.onload = e => {

if (previewImg) {
  previewImg.src = e.target.result;
}

if (previewWrap) {
  previewWrap.hidden = false;
}

if (dropZone) {
  dropZone.hidden = true;
}

if (analyzeBtn) {
  analyzeBtn.disabled = false;
}

};

reader.readAsDataURL(file);

if (resultSection) {
resultSection.hidden = true;
}

if (rejectionSection) {
rejectionSection.hidden = true;
}

redraw = null;
}

/* ============================================================
RESET
============================================================ */

function resetAnalyzer() {

selectedFile = null;
redraw = null;

if (fileInput) {
fileInput.value = "";
}

if (previewWrap) {
previewWrap.hidden = true;
}

if (dropZone) {
dropZone.hidden = false;
}

if (analyzeBtn) {
analyzeBtn.disabled = true;
}

if (progressBox) {
progressBox.hidden = true;
}

if (resultSection) {
resultSection.hidden = true;
}

if (rejectionSection) {
rejectionSection.hidden = true;
}

if (progressBar) {
progressBar.style.width = "0%";
}

if (progressText) {
progressText.textContent = "0%";
}
}

/* ============================================================
ANALYZE
============================================================ */

async function analyze() {

if (!selectedFile) {

alert("Please select an image first.");
return;

}

if (progressBox) {
progressBox.hidden = false;
}

if (analyzeBtn) {
analyzeBtn.disabled = true;
}

if (resultSection) {
resultSection.hidden = true;
}

if (rejectionSection) {
rejectionSection.hidden = true;
}

const stages =
typeof CC !== "undefined" && CC.g("stages")
? CC.g("stages")
: [
"Uploading image...",
"Checking image...",
"Analyzing disease..."
];

let progress = 0;

const timer = setInterval(() => {

progress = Math.min(progress + 4, 88);

if (progressBar) {
  progressBar.style.width = progress + "%";
}

if (progressText) {
  progressText.textContent = progress + "%";
}

const label = $("progressLabel");

if (label) {

  label.textContent =
    stages[
      progress < 30
        ? 0
        : progress < 60
          ? 1
          : 2
    ];

}

}, 200);

let data = null;

try {

const formData = new FormData();

formData.append("image", selectedFile);


console.log("CropCare AI: sending image to", API_URL);


const response = await fetch(API_URL, {
  method: "POST",
  body: formData
});


console.log(
  "CropCare AI: HTTP status",
  response.status
);


const text = await response.text();

console.log(
  "CropCare AI: backend response",
  text
);


try {

  data = JSON.parse(text);

} catch (error) {

  console.error(
    "CropCare AI: invalid JSON",
    error
  );

  data = {
    success: false,
    code: "invalid_response",
    reason: "The server returned an invalid response."
  };

}


/*
  IMPORTANT:
  A 200 response can still contain a legitimate rejection.

  Example:

  {
    "success": false,
    "rejected": true,
    "code": "not_plant"
  }

  That is NOT a network error.
*/

if (!response.ok) {

  console.error(
    "CropCare AI: server error",
    data
  );

  data = {
    success: false,
    code:
      data?.code ||
      "server_error",
    reason:
      data?.reason ||
      "The server could not process the image."
  };

}

} catch (error) {

console.error(
  "CropCare AI: FETCH ERROR",
  error
);

data = {
  success: false,
  code: "network",
  reason:
    "Could not connect to the CropCare AI server."
};

}

clearInterval(timer);

if (progressBar) {
progressBar.style.width = "100%";
}

if (progressText) {
progressText.textContent = "100%";
}

setTimeout(() => {

if (progressBox) {
  progressBox.hidden = true;
}

if (progressBar) {
  progressBar.style.width = "0%";
}

show(data, true);

if (analyzeBtn) {
  analyzeBtn.disabled = false;
}

}, 300);

}

analyzeBtn?.addEventListener(
"click",
analyze
);

/* ============================================================
RESPONSE HANDLER
============================================================ */

function show(data, scroll) {

console.log(
"CropCare AI FINAL DATA:",
data
);

redraw = () => show(data, false);

if (!data) {

renderReject(
  "network",
  scroll
);

return;

}

/*
ACCEPTED PREDICTION

Current backend format:

{
  success: true,
  accepted: true,
  disease: "...",
  crop: "...",
  confidence: 87,
  advice: {...}
}

*/

const accepted =
data.success === true &&
(
data.accepted === true ||
data.disease ||
data.condition ||
data.prediction
);

if (accepted) {

const advice =
  data.advice || {};


const normalized = {

  ok: true,

  crop:
    data.crop ||
    data.plant ||
    "Crop",

  condition:
    data.condition ||
    data.disease ||
    data.prediction ||
    "Unknown",

  confidence:
    Number(
      data.confidence ??
      data.probability ??
      0
    ),

  summary:
    advice.summary ||
    data.summary ||
    "AI-assisted crop disease prediction.",

  symptoms:
    advice.symptoms ||
    data.symptoms ||
    [],

  advice:
    advice.advice ||
    data.advice_list ||
    [],

  prevention:
    advice.prevention ||
    data.prevention ||
    [],

  alternatives:
    Array.isArray(data.alternatives)
      ? data.alternatives
      : []

};


renderResult(
  normalized,
  scroll
);

return;

}

/*
REJECTED IMAGE

Examples:

not_plant
unsure
not_leaf
rejected
invalid_image

*/

renderReject(
data.code ||
data.reason_code ||
(
data.rejected
? "not_plant"
: "network"
),
scroll,
data.reason
);

}

/* ============================================================
REJECTION
============================================================ */

function renderReject(
code,
scroll,
backendReason
) {

let titleKey;
let messageKey;

if (
code === "unsure"
) {

titleKey = "unT";
messageKey = "unM";

} else if (
code === "not_leaf" ||
code === "not_plant"
) {

titleKey = "badT";
messageKey = "badM";

} else if (
code === "invalid_image"
) {

titleKey = "badT";
messageKey = "badM";

} else {

titleKey = "netT";
messageKey = "netM";

}

const title =
typeof CC !== "undefined"
? CC.g(titleKey)
: (
code === "not_plant"
? "Image rejected"
: "Unable to analyze"
);

const message =
typeof CC !== "undefined"
? CC.g(messageKey)
: (
code === "not_plant"
? "This image does not appear to contain a suitable plant or crop."
: (
backendReason ||
"The image could not be processed."
)
);

if ($("rejTitle")) {
$("rejTitle").textContent = title;
}

if ($("rejText")) {

$("rejText").textContent =
  backendReason &&
  code !== "network"
    ? backendReason
    : message;

}

if (resultSection) {
resultSection.hidden = true;
}

if (rejectionSection) {
rejectionSection.hidden = false;
}

if (
scroll &&
rejectionSection
) {

rejectionSection.scrollIntoView({
  behavior: "smooth",
  block: "start"
});

}

}

/* ============================================================
RESULT
============================================================ */

function renderResult(
data,
scroll
) {

let typeText = {
o: "",
s: [],
a: [],
p: []
};

if (
typeof CC !== "undefined" &&
CC.g("T") &&
typeof CC.typeOf === "function"
) {

try {

  typeText =
    CC.g("T")[CC.typeOf(data.condition)] ||
    typeText;

} catch (e) {

  console.warn(
    "Disease type lookup failed:",
    e
  );

}

}

const confidence = Math.max(
0,
Math.min(
100,
Math.round(
Number(data.confidence) || 0
)
)
);

const list = arr => {

if (!Array.isArray(arr)) {
  return "";
}

return arr
  .map(item => {

    if (
      typeof item === "object" &&
      item !== null
    ) {

      return `<li>${esc(
        item.text ||
        item.description ||
        item.name ||
        JSON.stringify(item)
      )}</li>`;

    }

    return `<li>${esc(item)}</li>`;

  })
  .join("");

};

if (
resultImg &&
previewImg
) {

resultImg.src =
  previewImg.src;

}

if ($("resultTitle")) {

$("resultTitle").textContent =
  typeof CC !== "undefined"
    ? CC.g("rT")
    : "Analysis Result";

}

const cropName =
typeof CC !== "undefined" &&
typeof CC.cropName === "function"
? CC.cropName(data.crop)
: data.crop;

if (diseaseName) {

diseaseName.textContent =
  cropName +
  ": " +
  data.condition;

}

if (diseaseSummary) {

diseaseSummary.textContent =
  typeText.o ||
  data.summary ||
  "Crop disease prediction result.";

}

if (confidenceValue) {

confidenceValue.textContent =
  confidence + "%";

}

if (confidenceBadge) {

confidenceBadge.textContent =
  confidence + "%";

}

if (confidenceBar) {

confidenceBar.style.width =
  confidence + "%";

}

if ($("confNote")) {

let key = "cLo";

if (confidence >= 90) {
  key = "cHi";
} else if (confidence >= 75) {
  key = "cMid";
}


$("confNote").textContent =
  typeof CC !== "undefined"
    ? CC.g(key)
    : "";

}

if ($("symptomsList")) {

$("symptomsList").innerHTML =
  list(
    data.symptoms?.length
      ? data.symptoms
      : typeText.s
  );

}

if ($("adviceList")) {

$("adviceList").innerHTML =
  list(
    data.advice?.length
      ? data.advice
      : typeText.a
  );

}

if ($("preventList")) {

$("preventList").innerHTML =
  list(
    data.prevention?.length
      ? data.prevention
      : typeText.p
  );

}

if ($("altBox")) {

const alternatives =
  Array.isArray(
    data.alternatives
  )
    ? data.alternatives
    : [];


let html =
  typeof CC !== "undefined"
    ? `<h3>${esc(CC.g("alt"))}</h3>`
    : "<h3>Alternative predictions</h3>";


html += alternatives
  .map(a => {

    const altCrop =
      typeof CC !== "undefined" &&
      typeof CC.cropName === "function"
        ? CC.cropName(a.crop)
        : (
            a.crop ||
            "Crop"
          );


    return `
      <div class="alt-row">
        <span>
          ${esc(altCrop)}:
          ${esc(
            a.condition ||
            "Unknown"
          )}
        </span>

        <b>
          ${Number(
            a.confidence || 0
          )}%
        </b>
      </div>
    `;

  })
  .join("");


$("altBox").innerHTML =
  html;

}

if ($("discNote")) {

$("discNote").textContent =
  typeof CC !== "undefined"
    ? CC.g("disc")
    : "";

}

if (rejectionSection) {
rejectionSection.hidden = true;
}

if (resultSection) {
resultSection.hidden = false;
}

if (
scroll &&
resultSection
) {

resultSection.scrollIntoView({
  behavior: "smooth",
  block: "start"
});

}

}

/* ============================================================
LANGUAGE
============================================================ */

const previousApplyLanguage =
window.applyLanguage;

window.applyLanguage =
function(language) {

if (previousApplyLanguage) {
  previousApplyLanguage(language);
}

applyAnalyzeText();

if (redraw) {
  redraw();
}

};

applyAnalyzeText();
