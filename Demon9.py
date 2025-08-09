#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# angel_demon_translator_corruption_fonts_continuous.py
import re, unicodedata, random
import streamlit as st

# ---------- helpers ----------
TOK_RE = re.compile(r"(\w+|\s+|[^\w\s]+)", re.UNICODE)  # words | spaces | punctuation
INV = "\u2063"  # invisible wrapper for inserts (so we can strip perfectly)
def mark_insert(s): return INV + s + INV
def unmark_all(s):  return s.replace(INV, "")

# ---------- FONT & STYLE ladder by 10-point corruption bands ----------
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
    idx = (max(1, min(100, c)) - 1) // 10 + 1
    return f"band{idx}"

# ---------- reversible glyph sets ----------
# Angel
V_ANGEL = {'a':['ā','a'],'e':['ē','e'],'i':['ī','i'],'o':['ō','o'],'u':['ū','u'],'y':['ȳ','y']}
DGR_ANGEL = [('the','θe'),('The','Θe'),('sh','š'),('Sh','Š'),('ph','φ'),('Ph','Φ')]
AFFX_ANGEL_PRE = ["el’","sa’","’el"]
AFFX_ANGEL_SUF = ["-iel","-ael","-hosanna"]
OATHS_ANGEL = ["⟨amen⟩","⟨selah⟩","⟨gloria⟩","⟨hallelujah⟩"]

# Demon
V_DEMON = {'a':['â','a'],'e':['ê','e'],'i':['î','i'],'o':['ô','o'],'u':['û','u'],'y':['ŷ','y']}
DGR_DEMON = [('the','ðe'),('The','Ðe'),('th','þ'),('Th','Þ'),('sh','ʃ'),('Sh','ʃ'),
             ('ch','χ'),('Ch','Χ'),('ph','ƒ'),('Ph','Ƒ'),('qu','q͟u'),('Qu','Q͟u')]
AFFX_DEMON_PRE = ["ba’","’ba","me’","’me","za’","ka’","’za"]
AFFX_DEMON_SUF = ["-oth","-’rim","-az","-ius","-orum","-atrix","-zik","-gob","-’hii"]
OATHS_DEMON = ["⟨behold⟩","⟨thus bound⟩","⟨by pact⟩","⟨ipso facto⟩","⟨inter alia⟩"]

# Demon ornaments
CONS_ORN = {'s':'ſ','t':'†','h':'ʰ','n':'ñ','r':'ŕ'}
ZALGO_L = [u"\u0301", u"\u0302", u"\u0308", u"\u0336", u"\u034f"]
ZALGO_H = ZALGO_L + [u"\u0317", u"\u0316", u"\u0352", u"\u035B", u"\u0360", u"\u0362"]

# ---------- deterministic RNG ----------
def _rng(corruption:int, text:str):
    return random.Random(f"{corruption}|{len(text)}|{text[:128]}")

# ---------- continuous profiles ----------
def lerp(a,b,t): return a + (b-a)*t

def angel_profile(c:int):
    # c in [1..39] → t in [1..0] (more angelic at low c)
    t = 1 - (min(39, max(1, c)) - 1)/38.0
    return {
        "p_vowel":  lerp(0.25, 0.55, t),
        "p_dg":     lerp(0.08, 0.22, t),
        "p_oath":   lerp(0.02, 0.10, t),
        "p_pref":   lerp(0.02, 0.10, t),
        "p_suf":    lerp(0.02, 0.09, t),
        "orn":      0.0,
        "glitch":   0.0,
        "intensity": 1 + int(t > 0.33) + int(t > 0.66),  # 1..3
    }

def demon_profile(c:int):
    # c in [55..100] → t in [0..1] (more demonic at high c)
    t = (min(100, max(55, c)) - 55)/45.0
    return {
        "p_vowel":  lerp(0.30, 0.65, t),
        "p_dg":     lerp(0.20, 0.45, t),
        "p_oath":   lerp(0.05, 0.16, t),
        "p_pref":   lerp(0.06, 0.18, t),
        "p_suf":    lerp(0.05, 0.16, t),
        "orn":      lerp(0.12, 0.35, t),   # consonant ornaments prob
        "glitch":   lerp(0.00, 0.12, t),  # combining marks
        "intensity": 1 + int(t > 0.33) + int(t > 0.66),  # 1..3
    }

def neutral_profile(c:int):
    # c in [40..54] → very light, symmetric
    t = (min(54, max(40, c)) - 40)/14.0  # 0..1
    return {
        "p_vowel_ang": lerp(0.04, 0.07, 1-t),
        "p_vowel_dem": lerp(0.04, 0.07, t),
        "p_dg_ang":    lerp(0.02, 0.05, 1-t),
        "p_dg_dem":    lerp(0.02, 0.05, t),
    }

# ---------- stylizers ----------
def _style_word(word, rng, vowels_map, p_vowel, allow_orn=False, p_orn=0.0, allow_glitch=False, p_glitch=0.0, intensity=1):
    if not word or not word.isalnum(): return word
    out = []
    for i, c in enumerate(word):
        lc = c.lower()
        if lc in vowels_map and rng.random() < p_vowel:
            rep = vowels_map[lc][0]
            out.append(rep.upper() if c.isupper() else rep); continue
        if allow_orn and lc in CONS_ORN and rng.random() < p_orn:
            if lc=='s' and not(0 < i < len(word)-1 and word[i-1].isalnum() and word[i+1].isalnum()):
                pass  # only medial s becomes ſ
            else:
                out.append(CONS_ORN[lc]); continue
        if allow_glitch and rng.random() < p_glitch and c.isalpha():
            marks = ZALGO_H if intensity==3 else ZALGO_L
            stack = 1 + int(intensity==3 and rng.random()<0.5)
            out.append(c + "".join(rng.choice(marks) for _ in range(stack))); continue
        out.append(c)
    return "".join(out)

def stylize_sentence_corruption(sentence:str, corruption:int):
    corruption = max(1, min(100, int(corruption)))
    rng = _rng(corruption, sentence)
    toks = TOK_RE.findall(sentence)

    # Angelic side
    if corruption <= 39:
        prof = angel_profile(corruption)
        # oath / affixes (deterministic, based on rng)
        if rng.random() < prof["p_oath"]:
            pos = 0 if rng.random()<0.5 else len(toks)
            toks.insert(pos, mark_insert(rng.choice(OATHS_ANGEL)))
        if toks and rng.random() < prof["p_pref"]:
            for i,t in enumerate(toks):
                if t.isalnum(): toks[i] = mark_insert(rng.choice(AFFX_ANGEL_PRE)) + t; break
        if toks and rng.random() < prof["p_suf"]:
            for i in range(len(toks)-1,-1,-1):
                if toks[i].isalnum(): toks[i] = toks[i] + mark_insert(rng.choice(AFFX_ANGEL_SUF)); break
        s2 = "".join(toks)
        # digraphs
        if rng.random() < prof["p_dg"]:
            for a,b in DGR_ANGEL: s2 = s2.replace(a,b)
        out = []
        for t in TOK_RE.findall(s2):
            out.append(_style_word(t, rng, V_ANGEL, p_vowel=prof["p_vowel"], allow_orn=False, intensity=prof["intensity"]) if t.isalnum() else t)
        return "".join(out), band_for(corruption), prof["intensity"]

    # Neutral band
    if corruption <= 54:
        prof = neutral_profile(corruption)
        s2 = "".join(toks)
        if rng.random() < prof["p_dg_ang"]:
            for a,b in DGR_ANGEL: s2 = s2.replace(a,b)
        if rng.random() < prof["p_dg_dem"]:
            for a,b in DGR_DEMON: s2 = s2.replace(a,b)
        out = []
        for t in TOK_RE.findall(s2):
            if t.isalnum():
                # split probability between angel/demon vowels
                if rng.random() < 0.5:
                    out.append(_style_word(t, rng, V_ANGEL, p_vowel=prof["p_vowel_ang"]))
                else:
                    out.append(_style_word(t, rng, V_DEMON, p_vowel=prof["p_vowel_dem"]))
            else:
                out.append(t)
        return "".join(out), band_for(corruption), 0

    # Demonic side
    prof = demon_profile(corruption)
    if rng.random() < prof["p_oath"]:
        pos = 0 if rng.random()<0.5 else len(toks)
        toks.insert(pos, mark_insert(rng.choice(OATHS_DEMON)))
    if toks and rng.random() < prof["p_pref"]:
        for i,t in enumerate(toks):
            if t.isalnum(): toks[i] = mark_insert(rng.choice(AFFX_DEMON_PRE)) + t; break
    if toks and rng.random() < prof["p_suf"]:
        for i in range(len(toks)-1,-1,-1):
            if toks[i].isalnum(): toks[i] = toks[i] + mark_insert(rng.choice(AFFX_DEMON_SUF)); break
    s2 = "".join(toks)
    if rng.random() < prof["p_dg"]:
        for a,b in DGR_DEMON: s2 = s2.replace(a,b)
    out = []
    for t in TOK_RE.findall(s2):
        out.append(_style_word(
            t, rng, V_DEMON, p_vowel=prof["p_vowel"],
            allow_orn=True, p_orn=prof["orn"],
            allow_glitch=True, p_glitch=prof["glitch"],
            intensity=prof["intensity"]
        ) if t.isalnum() else t)
    return "".join(out), band_for(corruption), prof["intensity"]

# ---------- decoder ----------
def decode_to_english(text:str) -> str:
    s = unicodedata.normalize('NFKC', unmark_all(text))
    # digraphs back (both sides)
    for a,b in [
        ('ðe','the'), ('Ðe','The'), ('þ','th'), ('Þ','Th'), ('ʃ','sh'),
        ('Χ','Ch'), ('χ','ch'), ('ƒ','ph'), ('Ƒ','Ph'), ('q͟u','qu'), ('Q͟u','Qu'),
        ('θ','th'), ('Θ','Th'), ('š','sh'), ('Š','Sh'), ('φ','ph'), ('Φ','Ph'),
    ]: s = s.replace(a,b)
    # ornaments + curly quotes
    for fancy, plain in [('ſ','s'), ('†','t'), ('ʰ','h'), ('ñ','n'), ('ŕ','r'), ("’","'")]:
        s = s.replace(fancy, plain)
    # strip combining marks and deaccent
    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
    s = s.translate(str.maketrans("âêîôûŷāēīōūȳ", "aeiouyaeiouy"))
    # drop ⟨oaths⟩ and clean spaces
    s = re.sub(r"⟨[^⟩]+⟩", "", s)
    return re.sub(r"\s{2,}", " ", s).strip()

# ---------- UI ----------
st.set_page_config(page_title="Angelic ⇄ Demonic Translator (Continuous Styles + Fonts)", page_icon="🗝️")
st.markdown("<h1 style='font-size:2.25em; font-family:serif;'>🗝️ Angelic ⇄ Demonic Translator</h1>", unsafe_allow_html=True)
st.markdown('<div class="small-note">Deterministic. Style intensity updates every single slider tick; fonts change every 10 points.</div>', unsafe_allow_html=True)

corruption = st.slider("Corruption (1 = angel 😇, 100 = demon 😈)", 1, 100, 35)
text = st.text_area("Enter English text:", "")

if text:
    stylized, css_band, inten = stylize_sentence_corruption(text, corruption)
    st.markdown(f"**Band:** `{css_band}` • **Intensity step:** `{inten}`")
    st.markdown("**Stylized (progressively corrupted style + banded fonts):**")
    st.markdown(f'<div class="{css_band}" style="font-size:1.2em">{stylized}</div>', unsafe_allow_html=True)

    st.markdown("**Reverse-Translated:**")
    st.code(decode_to_english(stylized), language="text")

st.write("---")
st.subheader("🧹 Decode any stylized text to English")
to_decode = st.text_area("Paste stylized text (even if it uses fancy fonts/𝔣𝔬𝔫𝔱𝔰):", "", key="dec")
if to_decode:
    st.code(decode_to_english(to_decode), language="text")

