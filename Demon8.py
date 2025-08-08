#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# angel_demon_translator_corruption_fonts.py
import re, unicodedata, random
import streamlit as st

# ---------- helpers ----------
TOK_RE = re.compile(r"(\w+|\s+|[^\w\s]+)", re.UNICODE)  # words | spaces | punctuation
INV = "\u2063"  # invisible wrapper for inserts

def mark_insert(s):   return INV + s + INV
def unmark_all(s):    return s.replace(INV, "")

# ---------- FONT & STYLE ladder by corruption bands ----------
# We load a bunch of Google fonts and define 10 classes (.band1 .. .band10)
FONT_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=EB+Garamond:wght@400;600&family=Spectral+SC:wght@400;600&family=Playfair+Display:wght@400;700&family=Tenor+Sans&family=UnifrakturMaguntia&family=Fruktur&family=Metal+Mania&family=Nosifer&family=Creepster&display=swap" rel="stylesheet">
<style>
  .band1  { font-family: "Cinzel","EB Garamond",serif; letter-spacing:0.1px; }
  .band2  { font-family: "EB Garamond","Playfair Display",serif; letter-spacing:0.15px; }
  .band3  { font-family: "Spectral SC","Playfair Display",serif; letter-spacing:0.2px; }
  .band4  { font-family: "Tenor Sans","Spectral SC",serif; letter-spacing:0.25px; }
  /* transition into gothic */
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

def band_for(corruption:int) -> str:
    # 1–10 -> band1, 11–20 -> band2, ..., 91–100 -> band10
    idx = (max(1, min(100, corruption)) - 1) // 10 + 1
    return f"band{idx}"

# ---------- reversible glyph sets ----------
V_ANGEL = {'a':['ā','a'],'e':['ē','e'],'i':['ī','i'],'o':['ō','o'],'u':['ū','u'],'y':['ȳ','y']}
DGR_ANGEL = [('the','θe'),('The','Θe'),('sh','š'),('Sh','Š'),('ph','φ'),('Ph','Φ')]
AFFX_ANGEL_PRE = ["el’","sa’","’el"]
AFFX_ANGEL_SUF = ["-iel","-ael","-hosanna"]
OATHS_ANGEL = ["⟨amen⟩","⟨selah⟩","⟨gloria⟩","⟨hallelujah⟩"]

V_DEMON = {'a':['â','a'],'e':['ê','e'],'i':['î','i'],'o':['ô','o'],'u':['û','u'],'y':['ŷ','y']}
DGR_DEMON = [('the','ðe'),('The','Ðe'),('th','þ'),('Th','Þ'),('sh','ʃ'),('Sh','ʃ'),
             ('ch','χ'),('Ch','Χ'),('ph','ƒ'),('Ph','Ƒ'),('qu','q͟u'),('Qu','Q͟u')]
AFFX_DEMON_PRE = ["ba’","’ba","me’","’me","za’","ka’","’za"]
AFFX_DEMON_SUF = ["-oth","-’rim","-az","-ius","-orum","-atrix","-zik","-gob","-’hii"]
OATHS_DEMON = ["⟨behold⟩","⟨thus bound⟩","⟨by pact⟩","⟨ipso facto⟩","⟨inter alia⟩"]

CONS_ORN = {'s':'ſ','t':'†','h':'ʰ','n':'ñ','r':'ŕ'}
ZALGO_L = [u"\u0301", u"\u0302", u"\u0308", u"\u0336", u"\u034f"]
ZALGO_H = ZALGO_L + [u"\u0317", u"\u0316", u"\u0352", u"\u035B", u"\u0360", u"\u0362"]

# ---------- deterministic RNG ----------
def _rng(corruption:int, text:str):
    return random.Random(f"{corruption}|{len(text)}|{text[:128]}")

# ---------- stylizers ----------
def _style_word(word, rng, *, angel=False, intensity=2, allow_ornaments=True, allow_glitch=False):
    if not word or not word.isalnum(): return word
    vowels = V_ANGEL if angel else V_DEMON
    out = []
    for i, c in enumerate(word):
        lc = c.lower()
        if lc in vowels and rng.random() < (0.45 if angel else 0.5) + 0.1*intensity:
            rep = vowels[lc][0]
            out.append(rep.upper() if c.isupper() else rep); continue
        if allow_ornaments and not angel:
            if lc == 's' and 0 < i < len(word)-1 and word[i-1].isalnum() and word[i+1].isalnum():
                if rng.random() < 0.4 + 0.1*intensity:
                    out.append('ſ' if c.islower() else 'S'); continue
            if lc in ('t','h','n','r') and rng.random() < (0.18 + 0.08*intensity):
                out.append(CONS_ORN[lc]); continue
        if allow_glitch and not angel and rng.random() < (0.08 + 0.06*intensity):
            marks = ZALGO_H if intensity == 3 else ZALGO_L
            stack = 1 + int(intensity == 3 and rng.random() < 0.5)
            out.append(c + "".join(rng.choice(marks) for _ in range(stack))); continue
        out.append(c)
    return "".join(out)

def stylize_sentence_corruption(sentence:str, corruption:int):
    """
    corruption: 1..100 (1=angelic, 100=demonic). Deterministic & reversible.
    """
    corruption = max(1, min(100, int(corruption)))
    rng = _rng(corruption, sentence)
    toks = TOK_RE.findall(sentence)

    # Angelic zone
    if corruption <= 39:
        intensity = 3 if corruption <= 13 else 2 if corruption <= 27 else 1
        if rng.random() < 0.06 * intensity:
            pos = 0 if rng.random() < 0.5 else len(toks)
            toks.insert(pos, mark_insert(rng.choice(OATHS_ANGEL)))
        if toks and rng.random() < 0.08 * intensity:
            for i,t in enumerate(toks):
                if t.isalnum():
                    toks[i] = mark_insert(rng.choice(AFFX_ANGEL_PRE)) + t; break
        if toks and rng.random() < 0.07 * intensity:
            for i in range(len(toks)-1,-1,-1):
                if toks[i].isalnum():
                    toks[i] = toks[i] + mark_insert(rng.choice(AFFX_ANGEL_SUF)); break
        s2 = "".join(toks)
        for a,b in DGR_ANGEL: s2 = s2.replace(a,b)
        out = []
        for t in TOK_RE.findall(s2):
            out.append(_style_word(t, rng, angel=True, intensity=intensity, allow_ornaments=False, allow_glitch=False) if t.isalnum() else t)
        return "".join(out), band_for(corruption), intensity

    # Neutral zone
    if corruption <= 54:
        return sentence, band_for(corruption), 0

    # Demonic zone
    intensity = 1 if corruption <= 69 else 2 if corruption <= 84 else 3
    if rng.random() < 0.10 * intensity:
        pos = 0 if rng.random() < 0.5 else len(toks)
        toks.insert(pos, mark_insert(rng.choice(OATHS_DEMON)))
    if toks and rng.random() < 0.12 * intensity:
        for i,t in enumerate(toks):
            if t.isalnum():
                toks[i] = mark_insert(rng.choice(AFFX_DEMON_PRE)) + t; break
    if toks and rng.random() < 0.10 * intensity:
        for i in range(len(toks)-1,-1,-1):
            if toks[i].isalnum():
                toks[i] = toks[i] + mark_insert(rng.choice(AFFX_DEMON_SUF)); break
    s2 = "".join(toks)
    for a,b in DGR_DEMON: s2 = s2.replace(a,b)
    out = []
    for t in TOK_RE.findall(s2):
        out.append(_style_word(t, rng, angel=False, intensity=intensity, allow_ornaments=True, allow_glitch=(intensity==3)) if t.isalnum() else t)
    return "".join(out), band_for(corruption), intensity

# ---------- decoder ----------
def decode_to_english(text:str) -> str:
    # 0) remove markers, fold font-like codepoints
    s = unicodedata.normalize('NFKC', unmark_all(text))
    # 1) reverse digraphs
    for a,b in [
        ('ðe','the'), ('Ðe','The'), ('þ','th'), ('Þ','Th'), ('ʃ','sh'),
        ('Χ','Ch'), ('χ','ch'), ('ƒ','ph'), ('Ƒ','Ph'), ('q͟u','qu'), ('Q͟u','Qu'),
        ('θ','th'), ('Θ','Th'), ('š','sh'), ('Š','Sh'), ('φ','ph'), ('Φ','Ph'),
    ]: s = s.replace(a,b)
    # 2) ornaments + curly quotes
    for fancy, plain in [('ſ','s'), ('†','t'), ('ʰ','h'), ('ñ','n'), ('ŕ','r'), ("’","'")]:
        s = s.replace(fancy, plain)
    # 3) strip combining marks, deaccent
    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
    s = s.translate(str.maketrans("âêîôûŷāēīōūȳ", "aeiouyaeiouy"))
    # 4) drop any oath tokens and clean spaces
    s = re.sub(r"⟨[^⟩]+⟩", "", s)
    return re.sub(r"\s{2,}", " ", s).strip()

# ---------- UI ----------
st.set_page_config(page_title="Angelic ⇄ Demonic Translator (Corruption Fonts)", page_icon="🗝️")
st.markdown("<h1 style='font-size:2.25em; font-family:serif;'>🗝️ Angelic ⇄ Demonic Translator</h1>", unsafe_allow_html=True)
st.markdown('<div class="small-note">Deterministic output. Display fonts change every 10 corruption points for a progressively cursed look.</div>', unsafe_allow_html=True)

corruption = st.slider("Corruption (1 = angel 😇, 100 = demon 😈)", 1, 100, 35)
text = st.text_area("Enter English text:", "")

if text:
    stylized, css_band, inten = stylize_sentence_corruption(text, corruption)
    st.markdown(f"**Band:** `{css_band}` • **Intensity:** `{inten}`")
    st.markdown("**Stylized (visual corruption via fonts):**")
    st.markdown(f'<div class="{css_band}" style="font-size:1.2em">{stylized}</div>', unsafe_allow_html=True)

    st.markdown("**Reverse-Translated:**")
    st.code(decode_to_english(stylized), language="text")

st.write("---")
st.subheader("🧹 Decode any stylized text to English")
to_decode = st.text_area("Paste stylized text (even if it uses fancy fonts/𝔣𝔬𝔫𝔱𝔰):", "", key="dec")
if to_decode:
    st.code(decode_to_english(to_decode), language="text")

