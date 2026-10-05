let classes = CC.FALLBACK;
const grid = document.getElementById("diseaseGrid"), search = document.getElementById("diseaseSearch");
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function render() {
  const T = CC.g("T"); let n = 0;
  grid.innerHTML = Object.entries(classes).map(([crop, conds]) => conds.map(c => {
    n++;
    return `<article class="disease-card"><div class="disease-art">${CC.emoji[crop.split(/[ (,]/)[0]] || "🌿"}</div><div><span class="crop-tag">${esc(CC.cropName(crop))}</span><h3>${esc(c)}</h3><p>${esc(T[CC.typeOf(c)].o)}</p><a href="analyze.html">Analyze an image →</a></div></article>`;
  }).join("")).join("");
  document.getElementById("classCount").textContent = n + " classes";
  search.dispatchEvent(new Event("input"));
}
search.addEventListener("input", e => { const q = search.value.toLowerCase(); document.querySelectorAll(".disease-card").forEach(c => c.style.display = c.innerText.toLowerCase().includes(q) ? "" : "none"); });
fetch((window.API_BASE || "") + "/classes").then(r => r.json()).then(d => { if (d.classes && Object.keys(d.classes).length) { classes = d.classes; render(); } }).catch(() => {});
const prevApply = window.applyLanguage;
window.applyLanguage = function (l) { if (prevApply) prevApply(l); render(); };
render();
