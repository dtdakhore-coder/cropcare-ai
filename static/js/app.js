document.addEventListener("DOMContentLoaded",()=>{
  const menuBtn=document.getElementById("menuBtn"), mobile=document.getElementById("mobileMenu");
  if(menuBtn) menuBtn.addEventListener("click",()=>{mobile.style.display=mobile.style.display==="block"?"none":"block"});
  const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add("visible")}),{threshold:.12});
  document.querySelectorAll(".reveal").forEach(el=>observer.observe(el));
  const select=document.getElementById("languageSelect");
  if(select){
    const saved=localStorage.getItem("cropcare-language")||"en"; select.value=saved;
    select.addEventListener("change",()=>{localStorage.setItem("cropcare-language",select.value); if(window.applyLanguage) window.applyLanguage(select.value)});
    if(window.applyLanguage) window.applyLanguage(saved);
  }
});
// v4: count-up numbers, parallax, wipe reveals
document.addEventListener("DOMContentLoaded",()=>{
  const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const io=new IntersectionObserver(es=>es.forEach(e=>{
    if(!e.isIntersecting)return; io.unobserve(e.target);
    const el=e.target, end=+el.dataset.count, suf=el.dataset.suffix||"";
    if(reduce){el.textContent=end+suf;return}
    const t0=performance.now();(function tick(t){const p=Math.min((t-t0)/1200,1);el.textContent=Math.round(end*(1-Math.pow(1-p,3)))+suf;if(p<1)requestAnimationFrame(tick)})(t0);
  }),{threshold:.6});
  document.querySelectorAll("[data-count]").forEach(el=>io.observe(el));
  const wipes=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add("visible");wipes.unobserve(e.target)}}),{threshold:.2});
  document.querySelectorAll(".wipe").forEach(el=>wipes.observe(el));
  const px=document.querySelector(".parallax");
  if(px&&!reduce)addEventListener("scroll",()=>{const r=px.parentElement.getBoundingClientRect();if(r.bottom>0&&r.top<innerHeight){px.style.transform="translateY("+(-(innerHeight-r.top)*0.06)+"px)"}},{passive:true});
});
