#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# angel_demon_translator_complex_deterministic.py
import re, unicodedata, random
import streamlit as st

# ---------- helpers ----------
TOK_RE = re.compile(r"(\w+|\s+|[^\w\s]+)", re.UNICODE)  # words | spaces | punctuation
INV = "\u2063"  # invisible wrapper for inserts (so we can strip them perfectly)

def mark_insert(s):   return INV + s + INV
def unmark_all(s):    return s.replace(INV, "")

def to_fraktur(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    fraktur = [
        "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷"
    ]
    mapping = {c:f for c,f in zip(normal, fraktur[0]+fraktur[1])}
    return ''.join(mapping.get(ch, ch) for ch in text)

# ---------- reversible glyph sets ----------
# Angelic (soft)
V_ANGEL = {'a':['ā','a'],'e':['ē','e'],'i':['ī','i'],'o':['ō','o'],'u':['ū','u'],'y':['ȳ','y']}
DGR_ANGEL = [('the','θe'),('The','Θe'),('sh','š'),('Sh','Š'),('ph','φ'),('Ph','Φ')]
AFFX_ANGEL_PRE = ["el’","sa’","’el"]
AFFX_ANGEL_SUF = ["-iel","-ael","-hosanna"]
OATHS_ANGEL = ["⟨amen⟩","⟨selah⟩","⟨gloria⟩","⟨hallelujah⟩"]

# Demonic (harsher)
V_DEMON = {'a':['â','a'],'e':['ê','e'],'i':['î','i'],'o':['ô','o'],'u':['û','u'],'y':['ŷ','y']}
DGR_DEMON = [('the','ðe'),('The','Ðe'),('th','þ'),('Th','Þ'),('sh','ʃ'),('Sh','ʃ'),
             ('ch','χ'),('Ch','Χ'),('ph','ƒ'),('Ph','Ƒ'),('qu','q͟u'),('Qu','Q͟u')]
AFFX_DEMON_PRE = ["ba’","’ba","me’","’me","za’","ka’","’za"]
AFFX_DEMON_SUF = ["-oth","-’rim","-az","-ius","-orum","-atrix","-zik","-gob","-’hii"]
OATHS_DEMON = ["⟨behold⟩","⟨thus bound⟩","⟨by pact⟩","⟨ipso facto⟩","⟨inter alia⟩"]

# Reversible consonant ornaments (we’ll undo these in decoder)
CONS_ORN = {
    's':'ſ',  # medial only
    't':'†',
    'h':'ʰ',
    'n':'ñ',
    'r':'ŕ',
}

# Light/Heavy combining marks (get stripped on decode)
ZALGO_L = [u"\u0301", u"\u0302", u"\u0308", u"\u0336", u"\u034f"]
ZALGO_H = ZALGO_L + [u"\u0317", u"\u0316", u"\u0352", u"\u035B", u"\u0360", u"\u0362"]

# ---------- deterministic RNG ----------
def _rng(corruption:int, text:str):
    # Deterministic seed from corruption + the raw text
    return random.Random(f"{corruption}|{len(text)}|{text[:128]}")

# ---------- stylizers ----------
def _style_word(word, rng, angel=False, intensity=2, allow_ornaments=True, allow_glitch=False):
    if not word or not word.isalnum():
        return word
    vowels = V_ANGEL if angel else V_DEMON
    out = []
    for i, c in enumerate(word):
        lc = c.lower()
        # vowels first
        if lc in vowels and rng.random() < (0.45 if angel else 0.5) + 0.1*intensity:
            rep = vowels[lc][0]
            out.append(rep.upper() if c.isupper() else rep); continue
        # optional ornaments (demon side mostly)
        if allow_ornaments and not angel:
            if lc == 's' and 0 < i < len(word)-1 and word[i-1].isalnum() and word[i+1].isalnum():
                if rng.random() < 0.4 + 0.1*intensity:
                    out.append('ſ' if c.islower() else 'S'); continue
            if lc in ('t','h','n','r') and rng.random() < (0.18 + 0.08*intensity):
                mapped = CONS_ORN[lc]
                out.append(mapped if c.islower() else mapped)  # ornaments don’t have uppercase variants here
                continue
        # glitch (combining marks) at high demon intensity
        if allow_glitch and not angel and rng.random() < (0.08 + 0.06*intensity):
            marks = ZALGO_H if intensity == 3 else ZALGO_L
            stack = 1 + int(intensity == 3 and rng.random() < 0.5)
            out.append(c + "".join(rng.choice(marks) for _ in range(stack))); continue
        out.append(c)
    return "".join(out)

def stylize_sentence_corruption(sentence:str, corruption:int):
    """
    corruption: 1..100 (1=most angelic, 100=most demonic)
    Deterministic, reversible.
    """
    corruption = max(1, min(100, int(corruption)))
    rng = _rng(corruption, sentence)
    toks = TOK_RE.findall(sentence)

    # Angelic zone
    if corruption <= 39:
        intensity = 3 if corruption <= 13 else 2 if corruption <= 27 else 1
        # maybe oath
        if rng.random() < 0.06 * intensity:
            pos = 0 if rng.random() < 0.5 else len(toks)
            toks.insert(pos, mark_insert(rng.choice(OATHS_ANGEL)))
        # maybe angelic affixes
        if toks and rng.random() < 0.08 * intensity:
            # affix first alnum token only
            for i,t in enumerate(toks):
                if t.isalnum():
                    toks[i] = mark_insert(rng.choice(AFFX_ANGEL_PRE)) + t
                    break
        if toks and rng.random() < 0.07 * intensity:
            for i in range(len(toks)-1,-1,-1):
                if toks[i].isalnum():
                    toks[i] = toks[i] + mark_insert(rng.choice(AFFX_ANGEL_SUF))
                    break
        s2 = "".join(toks)
        for a,b in DGR_ANGEL:
            s2 = s2.replace(a,b)
        out = []
        for t in TOK_RE.findall(s2):
            out.append(_style_word(t, rng, angel=True, intensity=intensity, allow_ornaments=False, allow_glitch=False) if t.isalnum() else t)
        return "".join(out), "Angel", intensity

    # Neutral zone
    if corruption <= 54:
        return sentence, "Neutral", 0

    # Demonic zone
    intensity = 1 if corruption <= 69 else 2 if corruption <= 84 else 3
    # oath
    if rng.random() < 0.10 * intensity:
        pos = 0 if rng.random() < 0.5 else len(toks)
        toks.insert(pos, mark_insert(rng.choice(OATHS_DEMON)))
    # affixes (prefix/suffix around one token)
    if toks and rng.random() < 0.12 * intensity:
        for i,t in enumerate(toks):
            if t.isalnum():
                toks[i] = mark_insert(rng.choice(AFFX_DEMON_PRE)) + t
                break
    if toks and rng.random() < 0.10 * intensity:
        for i in range(len(toks)-1,-1,-1):
            if toks[i].isalnum():
                toks[i] = toks[i] + mark_insert(rng.choice(AFFX_DEMON_SUF))
                break

    s2 = "".join(toks)
    for a,b in DGR_DEMON:
        s2 = s2.replace(a,b)
    out = []
    for t in TOK_RE.findall(s2):
        out.append(_style_word(t, rng, angel=False, intensity=intensity, allow_ornaments=True, allow_glitch=(intensity==3)) if t.isalnum() else t)
    return "".join(out), "Demon", intensity

# ---------- decoder ----------
def _decore_word(w):
    # reverse digraphs (both sides)
    back = [
        ('ðe','the'), ('Ðe','The'), ('þ','th'), ('Þ','Th'), ('ʃ','sh'),
        ('Χ','Ch'), ('χ','ch'), ('ƒ','ph'), ('Ƒ','Ph'), ('q͟u','qu'), ('Q͟u','Qu'),
        ('θ','th'), ('Θ','Th'), ('š','sh'), ('Š','Sh'), ('φ','ph'), ('Φ','Ph'),
    ]
    for a,b in back: w = w.replace(a,b)
    # strip ornaments
    w = (w.replace('ſ','s')
           .replace('†','t')
           .replace('ʰ','h')
           .replace('ñ','n')
           .replace('ŕ','r'))
    # remove combining marks (zalgo/macrons etc.)
    w = ''.join(c for c in unicodedata.normalize('NFD', w) if unicodedata.category(c) != 'Mn')
    # de-accent vowels
    w = w.translate(str.maketrans("âêîôûŷāēīōūȳ", "aeiouyaeiouy"))
    return w

def reverse_translate(text):
    s = unmark_all(text)
    parts = TOK_RE.findall(s)
    out = []
    for p in parts:
        if p.isalnum():
            out.append(_decore_word(p))
        elif p.startswith("⟨") and p.endswith("⟩"):
            # drop inserted oaths
            continue
        else:
            out.append(p)
    return re.sub(r"\s{2,}", " ", "".join(out)).strip()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Angelic ⇄ Demonic Translator (Complex, Deterministic)", page_icon="🗝️")
st.markdown("<h1 style='font-size:2.25em; font-family:serif;'>🗝️ Angelic ⇄ Demonic Translator</h1>", unsafe_allow_html=True)
st.markdown(f"<div style='font-size:1.2em; color:#5b0a0a; margin-bottom:16px'>{to_fraktur('Purity or Perdition—your words decide.')}</div>", unsafe_allow_html=True)

corruption = st.slider("Corruption (1 = angel 😇, 100 = demon 😈)", 1, 100, 35)
text = st.text_area("Enter English text:", "")

if text:
    stylized, mode, inten = stylize_sentence_corruption(text, corruption)
    st.markdown(f"**Mode:** `{mode}` • **Intensity:** `{inten}`")
    st.markdown("**Stylized (deterministic at this slider value):**")
    st.markdown(f"<div style='font-size:1.2em'>{stylized}</div>", unsafe_allow_html=True)

    st.markdown("**Stylized (Fraktur):**")
    st.markdown(f"<div style='font-size:1.0em'>{to_fraktur(stylized)}</div>", unsafe_allow_html=True)

    st.markdown("**Reverse-Translated:**")
    st.code(reverse_translate(stylized), language="text")

st.write("---")
st.subheader("🧹 Decode any stylized text to English")
to_decode = st.text_area("Paste stylized text:", "", key="dec")
if to_decode:
    st.code(reverse_translate(to_decode), language="text")

