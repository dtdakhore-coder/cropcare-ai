document.addEventListener("DOMContentLoaded", () => {

  const API_URL = (window.API_BASE || "") + "/predict";

  const $ = id => document.getElementById(id);

  const esc = s =>
    String(s ?? "").replace(/[&<>"]/g, c => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;"
    }[c]));

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


  /* =========================
     LANGUAGE TEXT
  ========================= */

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


  /* =========================
     FILE SELECTION
  ========================= */

  if (chooseBtn && fileInput) {

    chooseBtn.addEventListener("click", function (e) {

      e.preventDefault();
      e.stopPropagation();

      fileInput.click();

    });

  }


  if (dropZone && fileInput) {

    dropZone.addEventListener("click", function (e) {

      if (e.target.closest("button")) return;

      fileInput.click();

    });

  }


  if (fileInput) {

    fileInput.addEventListener("change", function (e) {

      const file = e.target.files && e.target.files[0];

      if (file) {
        setFile(file);
      }

    });

  }


  ["dragenter", "dragover"].forEach(eventName => {

    if (!dropZone) return;

    dropZone.addEventListener(eventName, e => {

      e.preventDefault();
      e.stopPropagation();

      dropZone.classList.add("dragging");

    });

  });


  ["dragleave", "drop"].forEach(eventName => {

    if (!dropZone) return;

    dropZone.addEventListener(eventName, e => {

      e.preventDefault();
      e.stopPropagation();

      dropZone.classList.remove("dragging");

    });

  });


  if (dropZone) {

    dropZone.addEventListener("drop", e => {

      const file =
        e.dataTransfer &&
        e.dataTransfer.files &&
        e.dataTransfer.files[0];

      if (file) {
        setFile(file);
      }

    });

  }


  if (removeBtn) {
    removeBtn.addEventListener("click", resetAnalyzer);
  }


  if (tryAgainBtn) {
    tryAgainBtn.addEventListener("click", resetAnalyzer);
  }


  /* =========================
     SET IMAGE
  ========================= */

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


    reader.onerror = () => {

      alert("Unable to read this image.");

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


  /* =========================
     RESET
  ========================= */

  function resetAnalyzer() {

    selectedFile = null;
    redraw = null;


    if (fileInput) {
      fileInput.value = "";
    }


    if (previewImg) {
      previewImg.src = "";
    }


    if (fileName) {
      fileName.textContent = "";
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


  /* =========================
     ANALYZE IMAGE
  ========================= */

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

      progress = Math.min(progress + 5, 88);


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

    }, 160);


    let data = null;


    try {

      const formData = new FormData();

      formData.append("image", selectedFile);


      console.log("Sending image to:", API_URL);


      const response = await fetch(API_URL, {

        method: "POST",

        body: formData

      });


      console.log("HTTP status:", response.status);


      const text = await response.text();


      console.log("Backend response:", text);


      try {

        data = JSON.parse(text);

      } catch (jsonError) {

        console.error(
          "Invalid JSON from backend:",
          jsonError
        );


        data = {

          ok: false,

          code: "net",

          reason:
            "Backend did not return valid JSON."

        };

      }


      if (!response.ok) {

        console.error(
          "Backend HTTP error:",
          data
        );


        data = {

          ok: false,

          code: data?.code || "net",

          reason:
            data?.reason ||
            "Backend error."

        };

      }


    } catch (error) {

      console.error(
        "FETCH ERROR:",
        error
      );


      data = {

        ok: false,

        code: "net",

        reason: error.message

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


  if (analyzeBtn) {

    analyzeBtn.addEventListener(
      "click",
      analyze
    );

  }


  /* =========================
     RESPONSE HANDLER
  ========================= */

  function show(data, scroll) {

    console.log("FINAL DATA:", data);


    redraw = () => show(data, false);


    const isSuccess =
      data &&
      (
        data.ok === true ||
        data.success === true ||
        (
          data.condition &&
          (
            data.confidence !== undefined ||
            data.prediction !== undefined
          )
        )
      );


    if (isSuccess) {


      const normalized = {

        ...data,

        ok: true,


        condition:
          data.condition ||
          data.prediction ||
          data.disease ||
          "Unknown",


        confidence:
          Number(
            data.confidence ??
            data.probability ??
            0
          ),


        crop:
          data.crop ||
          data.plant ||
          "Crop",


        alternatives:
          Array.isArray(data.alternatives)
            ? data.alternatives
            : []

      };


      renderResult(
        normalized,
        scroll
      );


    } else {

      renderReject(
        data?.code || "net",
        scroll
      );

    }

  }


  /* =========================
     REJECTION
  ========================= */

  function renderReject(code, scroll) {

    let titleKey;
    let messageKey;


    if (code === "unsure") {

      titleKey = "unT";
      messageKey = "unM";


    } else if (code === "not_leaf") {

      titleKey = "badT";
      messageKey = "badM";


    } else if (code === "not_plant") {

      titleKey = "badT";
      messageKey = "badM";


    } else {

      titleKey = "netT";
      messageKey = "netM";

    }


    const title =
      typeof CC !== "undefined"
        ? CC.g(titleKey)
        : "Unable to analyze";


    const message =
      typeof CC !== "undefined"
        ? CC.g(messageKey)
        : "The image could not be processed.";


    if ($("rejTitle")) {
      $("rejTitle").textContent = title;
    }


    if ($("rejText")) {
      $("rejText").textContent = message;
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


  /* =========================
     RESULT
  ========================= */

  function renderResult(data, scroll) {

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

        .map(
          item =>
            `<li>${esc(item)}</li>`
        )

        .join("");

    };


    if (resultImg && previewImg) {

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
        list(typeText.s);

    }


    if ($("adviceList")) {

      $("adviceList").innerHTML =
        list(typeText.a);

    }


    if ($("preventList")) {

      $("preventList").innerHTML =
        list(typeText.p);

    }


    if ($("altBox")) {

      const alternatives =
        Array.isArray(data.alternatives)
          ? data.alternatives
          : [];


      let html =
        typeof CC !== "undefined"

          ? `<h3>${esc(
              CC.g("alt")
            )}</h3>`

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

      rejectionSection.hidden =
        true;

    }


    if (resultSection) {

      resultSection.hidden =
        false;

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


  /* =========================
     LANGUAGE
  ========================= */

  const previousApplyLanguage =
    window.applyLanguage;


  window.applyLanguage =
    function(language) {

      if (previousApplyLanguage) {

        previousApplyLanguage(
          language
        );

      }


      applyAnalyzeText();


      if (redraw) {

        redraw();

      }

    };


  applyAnalyzeText();


  /* =========================
     DEBUG
  ========================= */

  console.log(
    "CropCare AI analyze.js loaded successfully."
  );

  console.log(
    "Choose button:",
    chooseBtn
  );

  console.log(
    "File input:",
    fileInput
  );

});
