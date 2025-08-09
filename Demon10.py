#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# angel_demon_translator_combined.py
import re, unicodedata, random
import streamlit as st

# ========= helpers =========
TOK_RE = re.compile(r"(\w+|\s+|[^\w\s]+)", re.UNICODE)
INV = "\u2063"
def mark_insert(s): return INV + s + INV
def unmark_all(s):  return s.replace(INV, "")

# ========= header (Fraktur for headings only) =========
def to_fraktur(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    fraktur = [
        "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷"
    ]
    mapping = {c: f for c, f in zip(normal, fraktur[0] + fraktur[1])}
    return ''.join(mapping.get(ch, ch) for ch in text)

# ========= fonts per 10-point band (visual only) =========
FONT_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=EB+Garamond:wght@400;600&family=Spectral+SC:wght@400;600&family=Playfair+Display:wght@400;700&family=Tenor+Sans&family=UnifrakturMaguntia&family=Fruktur&family=Metal+Mania&family=Nosifer&family=Creepster&display=swap" rel="stylesheet">
<style>
  .band1  { font-family: "Cinzel","EB Garamond",serif; letter-spacing:0.1px; }
  .band2  { font-family: "EB Garamond","Playfair Display",serif; letter-spacing:0.15px; }
  .band3  { font-family: "Spectral SC","Playfair Display",serif; letter-spacing:0.2px; }
  .band4  { font-family: "Tenor Sans","Spectral SC",serif; letter-spacing:0.25px; }
  .band5  { font-family: "Spectral SC","UnifrakturMaguntia",serif; letter-spacing:0.3px; text-shadow: 0 0 0.5px rgba(0,0,0,.35); }
  .band6  { font-family: "UnifrakturMaguntia","Fruktur",serif; letter-spacing:0.35px; text-shadow: 0 0 1px rgba(0,0,0,.45); }
  .band7  { font-family: "Fruktur","UnifrakturMaguntia",serif; letter-spacing:0.4px; text-shadow: 0 0 1.2px rgba(120,0,0,.5); }
  .band8  { font-family: "Metal Mania","Fruktur","UnifrakturMaguntia",serif; letter-spacing:0.45px; text-shadow: 0 0 1.5px rgba(160,0,0,.6); transform: skewX(-1deg); }
  .band9  { font-family: "Nosifer","Metal Mania","UnifrakturMaguntia",serif; letter-spacing:0.5px; text-shadow: 0 0 2px rgba(200,0,0,.7); transform: skewX(-2deg); }
  .band10 { font-family: "Creepster","Nosifer","Metal Mania",serif; letter-spacing:0.6px; text-shadow: 0 0 3px rgba(255,0,0,.8); transform: skewX(-3deg) rotate(-0.2deg); }
  .small-note { color:#777; font-size:0.9em; }
</style>
"""
st.markdown(FONT_CSS, unsafe_allow_html=True)

def band_for(c:int) -> str:
    idx = (max(1, min(100, c)) - 1)//10 + 1
    return f"band{idx}"

# ========= “persona” flavor assets (used as options) =========
_VOWELS_ANGEL = {'a':['ā','a'],'e':['ē','e'],'i':['ī','i'],'o':['ō','o'],'u':['ū','u'],'y':['ȳ','y']}
_VOWELS_DEMON = {'a':['â','a'],'e':['ê','e'],'i':['î','i'],'o':['ô','o'],'u':['û','u'],'y':['ŷ','y']}

_DGR_ANGEL = [('the','θe'),('The','Θe'),('sh','š'),('Sh','Š'),('ph','φ'),('Ph','Φ')]
_DGR_DEMON = [('the','ðe'),('The','Ðe'),('th','þ'),('Th','Þ'),('sh','ʃ'),('Sh','ʃ'),
              ('ch','χ'),('Ch','Χ'),('ph','ƒ'),('Ph','Ƒ'),('qu','q͟u'),('Qu','Q͟u')]

_AFFIX_PRE_ANG = ["el’","sa’","’el"]
_AFFIX_SUF_ANG = ["-iel","-ael","-hosanna"]
_AFFIX_PRE_DEM = ["ba’","’ba","me’","’me","za’","ka’","’za"]
_AFFIX_SUF_DEM = ["-oth","-’rim","-az","-ius","-orum","-atrix","-zik","-gob","-’hii"]

_OATHS_ANG = ["⟨amen⟩","⟨selah⟩","⟨gloria⟩","⟨hallelujah⟩"]
_OATHS_DEM = ["⟨behold⟩","⟨thus bound⟩","⟨by pact⟩","⟨ipso facto⟩","⟨inter alia⟩"]

# ornaments/zalgo
_CONS_ORN = {'s':'ſ','t':'†','h':'ʰ','n':'ñ','r':'ŕ'}
_ZALGO_L = [u"\u0301", u"\u0302", u"\u0308", u"\u0336", u"\u034f"]
_ZALGO_H = _ZALGO_L + [u"\u0317", u"\u0316", u"\u0352", u"\u035B", u"\u0360", u"\u0362"]

# archaic + latinisms (from your file)
ARCHAIC_MAP = {
    "you are":"thou art","you will":"thou shalt","shall not":"shalt not",
    "your":"thy","yours":"thine","you":"thou","are":"art"
}
LATINISMS = ["ergo","inter alia","ipso facto","sine die","ad infinitum","mutatis mutandis"]

def apply_archaic_pronouns(s:str)->str:
    for k in sorted(ARCHAIC_MAP, key=len, reverse=True):
        s = s.replace(k, ARCHAIC_MAP[k]).replace(k.capitalize(), ARCHAIC_MAP[k].capitalize())
    return s

def sprinkle_latinisms(s:str, rng:random.Random, rate:float)->str:
    tokens = s.split()
    out=[]
    for t in tokens:
        out.append(t)
        if rng.random() < rate and t[-1].isalnum():
            out.append(mark_insert("⟨"+rng.choice(LATINISMS)+"⟩"))
    return " ".join(out)

# ========= deterministic RNG =========
def _rng(c:int, text:str, seed:str|None):
    base = f"{c}|{len(text)}|{text[:128]}"
    if seed: base += f"|seed:{seed}"
    return random.Random(base)

# ========= continuous style profiles =========
def lerp(a,b,t): return a + (b-a)*t

def angel_profile(c:int):
    t = 1 - (min(39, max(1, c)) - 1)/38.0
    return {
        "p_vowel":  lerp(0.25, 0.55, t),
        "p_dg":     lerp(0.08, 0.22, t),
        "p_oath":   lerp(0.02, 0.10, t),
        "p_pref":   lerp(0.02, 0.10, t),
        "p_suf":    lerp(0.02, 0.09, t),
        "intensity": 1 + int(t>0.33) + int(t>0.66),
    }

def demon_profile(c:int):
    t = (min(100, max(55, c)) - 55)/45.0
    return {
        "p_vowel":  lerp(0.30, 0.65, t),
        "p_dg":     lerp(0.20, 0.45, t),
        "p_oath":   lerp(0.05, 0.16, t),
        "p_pref":   lerp(0.06, 0.18, t),
        "p_suf":    lerp(0.05, 0.16, t),
        "p_orn":    lerp(0.12, 0.35, t),
        "p_glitch": lerp(0.00, 0.12, t),
        "intensity": 1 + int(t>0.33) + int(t>0.66),
    }

def neutral_profile(c:int):
    t = (min(54, max(40, c)) - 40)/14.0
    return {
        "p_vowel_ang": lerp(0.04, 0.07, 1-t),
        "p_vowel_dem": lerp(0.04, 0.07, t),
        "p_dg_ang":    lerp(0.02, 0.05, 1-t),
        "p_dg_dem":    lerp(0.02, 0.05, t),
    }

# ========= core word stylizer =========
def _style_word(word, rng, vowels_map, p_vowel, allow_orn=False, p_orn=0.0, allow_glitch=False, p_glitch=0.0, intensity=1):
    if not word or not word.isalnum(): return word
    out=[]
    for i,c in enumerate(word):
        lc=c.lower()
        if lc in vowels_map and rng.random()<p_vowel:
            rep=vowels_map[lc][0]
            out.append(rep.upper() if c.isupper() else rep); continue
        if allow_orn and lc in _CONS_ORN and rng.random()<p_orn:
            if lc=='s' and not(0<i<len(word)-1 and word[i-1].isalnum() and word[i+1].isalnum()):
                pass
            else:
                out.append(_CONS_ORN[lc]); continue
        if allow_glitch and c.isalpha() and rng.random()<p_glitch:
            marks=_ZALGO_H if intensity==3 else _ZALGO_L
            stack=1+int(intensity==3 and rng.random()<0.5)
            out.append(c+"".join(rng.choice(marks) for _ in range(stack))); continue
        out.append(c)
    return "".join(out)

# ========= sentence stylizer (continuous, with your options) =========
def stylize_sentence(sentence:str, corruption:int, *, archaic=False, latinisms=False, glitch_override=False, seed:str|None=None):
    corruption=max(1, min(100, int(corruption)))
    rng=_rng(corruption, sentence, seed)
    toks= TOK_RE.findall(sentence)

    # Optional global flavor pre-pass
    if corruption<=39 and archaic:
        toks = TOK_RE.findall(apply_archaic_pronouns("".join(toks).lower()))
    s="".join(toks)

    if corruption<=39:  # Angelic
        prof=angel_profile(corruption)
        if latinisms:  # harmless on angel side too if desired
            s = sprinkle_latinisms(s, rng, 0.10)
        toks = TOK_RE.findall(s)
        if rng.random()<prof["p_oath"]:
            pos=0 if rng.random()<0.5 else len(toks)
            toks.insert(pos, mark_insert(rng.choice(_OATHS_ANG)))
        if toks and rng.random()<prof["p_pref"]:
            for i,t in enumerate(toks):
                if t.isalnum(): toks[i]=mark_insert(rng.choice(_AFFIX_PRE_ANG))+t; break
        if toks and rng.random()<prof["p_suf"]:
            for i in range(len(toks)-1,-1,-1):
                if toks[i].isalnum(): toks[i]=toks[i]+mark_insert(rng.choice(_AFFIX_SUF_ANG)); break
        s2="".join(toks)
        if rng.random()<prof["p_dg"]:
            for a,b in _DGR_ANGEL: s2=s2.replace(a,b)
        out=[]
        for t in TOK_RE.findall(s2):
            if t.isalnum():
                out.append(_style_word(t, rng, _VOWELS_ANGEL, p_vowel=prof["p_vowel"], intensity=prof["intensity"]))
            else: out.append(t)
        return "".join(out), band_for(corruption), prof["intensity"]

    if corruption<=54:  # Neutral blend
        prof=neutral_profile(corruption)
        s2=s
        if rng.random()<prof["p_dg_ang"]:
            for a,b in _DGR_ANGEL: s2=s2.replace(a,b)
        if rng.random()<prof["p_dg_dem"]:
            for a,b in _DGR_DEMON: s2=s2.replace(a,b)
        out=[]
        for t in TOK_RE.findall(s2):
            if t.isalnum():
                if rng.random()<0.5:
                    out.append(_style_word(t, rng, _VOWELS_ANGEL, p_vowel=prof["p_vowel_ang"]))
                else:
                    out.append(_style_word(t, rng, _VOWELS_DEMON, p_vowel=prof["p_vowel_dem"]))
            else: out.append(t)
        return "".join(out), band_for(corruption), 0

    # Demonic
    prof=demon_profile(corruption)
    if latinisms: s = sprinkle_latinisms(s, rng, 0.16 + 0.04*prof["intensity"])
    toks = TOK_RE.findall(s)
    if rng.random()<prof["p_oath"]:
        pos=0 if rng.random()<0.5 else len(toks)
        toks.insert(pos, mark_insert(rng.choice(_OATHS_DEM)))
    if toks and rng.random()<prof["p_pref"]:
        for i,t in enumerate(toks):
            if t.isalnum(): toks[i]=mark_insert(rng.choice(_AFFIX_PRE_DEM))+t; break
    if toks and rng.random()<prof["p_suf"]:
        for i in range(len(toks)-1,-1,-1):
            if toks[i].isalnum(): toks[i]=toks[i]+mark_insert(rng.choice(_AFFIX_SUF_DEM)); break
    s2="".join(toks)
    if rng.random()<prof["p_dg"]:
        for a,b in _DGR_DEMON: s2=s2.replace(a,b)
    out=[]
    p_glitch = (prof["p_glitch"] if not glitch_override else max(prof["p_glitch"], 0.15))
    for t in TOK_RE.findall(s2):
        if t.isalnum():
            out.append(_style_word(t, rng, _VOWELS_DEMON, p_vowel=prof["p_vowel"],
                                   allow_orn=True, p_orn=prof["p_orn"],
                                   allow_glitch=True, p_glitch=p_glitch,
                                   intensity=prof["intensity"]))
        else: out.append(t)
    return "".join(out), band_for(corruption), prof["intensity"]

# ========= decoder =========
def decode_to_english(text:str, *, decode_archaic=False, strip_latinisms=True)->str:
    s = unicodedata.normalize('NFKC', unmark_all(text))
    # undo digraphs
    back = [
        ('ðe','the'), ('Ðe','The'), ('þ','th'), ('Þ','Th'), ('ʃ','sh'),
        ('Χ','Ch'), ('χ','ch'), ('ƒ','ph'), ('Ƒ','Ph'), ('q͟u','qu'), ('Q͟u','Qu'),
        ('θ','th'), ('Θ','Th'), ('š','sh'), ('Š','Sh'), ('φ','ph'), ('Φ','Ph'),
    ]
    for a,b in back: s = s.replace(a,b)
    # strip ornaments / apostrophes
    for fancy, plain in [('ſ','s'),('†','t'),('ʰ','h'),('ñ','n'),('ŕ','r'),("’","'")]:
        s = s.replace(fancy, plain)
    # remove combining marks
    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
    # de-accent vowels
    s = s.translate(str.maketrans("âêîôûŷāēīōūȳ", "aeiouyaeiouy"))
    if strip_latinisms:
        s = re.sub(r"⟨[^⟩]+⟩", "", s)
    if decode_archaic:
        back_map = {
            "thou art":"you are", "thou shalt":"you will", "shalt not":"shall not",
            "thy":"your", "thine":"yours", "thou":"you", "art":"are"
        }
        for k,v in sorted(back_map.items(), key=lambda x:len(x[0]), reverse=True):
            s = s.replace(k, v).replace(k.capitalize(), v.capitalize())
    return re.sub(r"\s{2,}", " ", s).strip()

# ========= UI =========
st.set_page_config(page_title="Angelic ⇄ Demonic Translator (Combined)", page_icon="🗝️")
st.markdown("<h1 style='font-size:2.25em; font-family:serif;'>🗝️ Angelic ⇄ Demonic Translator</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='small-note'>{to_fraktur('Deterministic. Style changes each slider tick; fonts change every 10 points.')}</div>", unsafe_allow_html=True)

corruption = st.slider("Corruption (1 = angel 😇, 100 = demon 😈)", 1, 100, 35)
colA, colB, colC, colD = st.columns(4)
with colA:
    archaic = st.checkbox("Archaic (Baal-ish)", value=False)
with colB:
    latinisms = st.checkbox("Latinisms (Mephisto-ish)", value=False)
with colC:
    glitch_mode = st.checkbox("Force extra glitch (demon)", value=False)
with colD:
    seed_val = st.text_input("Seed (optional)", value="")

text = st.text_area("Enter English text:", "")

if text:
    stylized, css_band, intensity = stylize_sentence(
        text, corruption,
        archaic=archaic, latinisms=latinisms, glitch_override=glitch_mode,
        seed=(seed_val.strip() or None)
    )
    st.markdown(f"**Band:** `{css_band}` • **Intensity step:** `{intensity}`")
    st.markdown("**Stylized:**")
    st.markdown(f'<div class="{css_band}" style="font-size:1.2em">{stylized}</div>', unsafe_allow_html=True)

    st.markdown("**Reverse-Translated:**")
    st.code(decode_to_english(stylized, decode_archaic=archaic, strip_latinisms=latinisms), language="text")

st.write("---")
st.subheader("🧹 Decode any stylized text to English")
to_decode = st.text_area("Paste stylized text (fonts/𝔣𝔬𝔫𝔱𝔰 okay):", "", key="dec")
if to_decode:
    st.code(decode_to_english(to_decode, decode_archaic=True, strip_latinisms=True), language="text")

