window.CropCareI18n={
en:{
"nav.home":"Home","nav.analyze":"Analyze","nav.how":"How It Works","nav.diseases":"Diseases","nav.faq":"FAQ",
"hero.title":"Detect crop problems earlier.<br><span>Protect your crops smarter.</span>",
"hero.text":"Upload a clear crop-leaf image and get an AI-based prediction with practical, farmer-friendly guidance.",
"hero.cta":"Analyze Crop"
},
mr:{
"nav.home":"मुख्यपृष्ठ","nav.analyze":"विश्लेषण","nav.how":"कसे कार्य करते","nav.diseases":"रोग","nav.faq":"सामान्य प्रश्न",
"hero.title":"पिकांच्या समस्या लवकर ओळखा.<br><span>पिकांचे संरक्षण अधिक हुशारीने करा.</span>",
"hero.text":"पिकाच्या पानाचा स्पष्ट फोटो अपलोड करा आणि AI आधारित अंदाज व सोपे मार्गदर्शन मिळवा.",
"hero.cta":"पिकाचे विश्लेषण करा"
},
hi:{
"nav.home":"होम","nav.analyze":"विश्लेषण","nav.how":"कैसे काम करता है","nav.diseases":"रोग","nav.faq":"सामान्य प्रश्न",
"hero.title":"फसल की समस्याओं को जल्दी पहचानें।<br><span>अपनी फसल की बेहतर सुरक्षा करें।</span>",
"hero.text":"फसल की पत्ती की साफ तस्वीर अपलोड करें और AI आधारित अनुमान व आसान मार्गदर्शन प्राप्त करें।",
"hero.cta":"फसल का विश्लेषण करें"
}};
window.applyLanguage=function(lang){
 const dict=window.CropCareI18n[lang]||window.CropCareI18n.en;
 document.documentElement.lang=lang;
 document.querySelectorAll("[data-i18n]").forEach(el=>{const k=el.dataset.i18n;if(dict[k]!==undefined)el.innerHTML=dict[k]});
};