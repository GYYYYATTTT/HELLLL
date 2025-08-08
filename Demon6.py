#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# angel_demon_translator_deterministic.py
import re, unicodedata, random
import streamlit as st

# ---------- helpers ----------
TOK_RE = re.compile(r"(\w+|\s+|[^\w\s]+)", re.UNICODE)  # words | spaces | punctuation
INV = "\u2063"  # invisible wrapper for inserts (kept deterministic, easy to strip)

def mark_insert(s):   return INV + s + INV
def unmark_all(s):    return s.replace(INV, "")

def to_fraktur(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    fraktur = [
        "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷"
    ]
    return ''.join({c:f for c,f in zip(normal, ''.join(fraktur))}.get(ch, ch) for ch in text)

# ---------- reversible glyph sets ----------
_VOWELS_ANGEL = {'a':['ā','a'],'e':['ē','e'],'i':['ī','i'],'o':['ō','o'],'u':['ū','u'],'y':['ȳ','y']}
_VOWELS_DEMON = {'a':['â','a'],'e':['ê','e'],'i':['î','i'],'o':['ô','o'],'u':['û','u'],'y':['ŷ','y']}

_DIGRAPHS_ANGEL = [('the','θe'),('The','Θe'),('sh','š'),('Sh','Š'),('ph','φ'),('Ph','Φ')]
_DIGRAPHS_DEMON = [('the','ðe'),('The','Ðe'),('th','þ'),('Th','Þ'),('sh','ʃ'),('Sh','ʃ'),
                   ('ph','ƒ'),('Ph','Ƒ'),('qu','q͟u'),('Qu','Q͟u')]

# ---------- deterministic stylizer ----------
def _rng(corruption:int, text:str):
    # Seeded only by corruption + plain text, to be reproducible and guessable with the same slider.
    return random.Random(f"{corruption}|{len(text)}|{text[:128]}")

def _style_word(word, rng, angel=False, intensity=2):
    if not word or not word.isalnum():
        return word
    vowels = _VOWELS_ANGEL if angel else _VOWELS_DEMON
    out = []
    for c in word:
        lc = c.lower()
        if lc in vowels and rng.random() < (0.35 + 0.12*intensity):
            rep = vowels[lc][0]
            out.append(rep.upper() if c.isupper() else rep)
        else:
            out.append(c)
    return "".join(out)

def stylize_sentence_corruption(sentence:str, corruption:int):
    """
    corruption: 1..100 (1=most angelic, 100=most demonic)
    Deterministic output for a given (sentence, corruption).
    """
    corruption = max(1, min(100, int(corruption)))
    rng = _rng(corruption, sentence)
    tokens = TOK_RE.findall(sentence)

    if corruption <= 39:
        # Angelic side
        intensity = 3 if corruption <= 13 else 2 if corruption <= 27 else 1
        # optional oath (deterministic position)
        if rng.random() < 0.06 * intensity:
            pos = 0 if (rng.random() < 0.5) else len(tokens)
            tokens.insert(pos, mark_insert("⟨amen⟩"))
        out = []
        for t in tokens:
            out.append(_style_word(t, rng, angel=True, intensity=intensity) if t.isalnum() else t)
        voice = "Angel"; voice_int = intensity
        return "".join(out), voice, voice_int

    if corruption <= 54:
        return sentence, "Neutral", 0

    # Demonic side
    intensity = 1 if corruption <= 69 else 2 if corruption <= 84 else 3
    if rng.random() < 0.09 * intensity:
        pos = 0 if (rng.random() < 0.5) else len(tokens)
        tokens.insert(pos, mark_insert("⟨by pact⟩"))

    s2 = "".join(tokens)
    # deterministic digraph pass
    for a,b in _DIGRAPHS_DEMON:
        s2 = s2.replace(a,b)

    out = []
    for t in TOK_RE.findall(s2):
        out.append(_style_word(t, rng, angel=False, intensity=intensity) if t.isalnum() else t)
    voice = "Demon"; voice_int = intensity
    return "".join(out), voice, voice_int

# ---------- decoder (does NOT need the slider) ----------
def _decore_word(w):
    back = [
        ('ðe','the'), ('Ðe','The'), ('þ','th'), ('Þ','Th'), ('ʃ','sh'), ('ƒ','ph'), ('Ƒ','Ph'),
        ('q͟u','qu'), ('Q͟u','Qu'), ('θ','th'), ('Θ','Th'), ('š','sh'), ('Š','Sh'), ('φ','ph'), ('Φ','Ph'),
    ]
    for a,b in back:
        w = w.replace(a,b)
    # remove diacritics / accents
    w = ''.join(c for c in unicodedata.normalize('NFD', w) if unicodedata.category(c) != 'Mn')
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
            # drop oath insertions
            continue
        else:
            out.append(p)
    return re.sub(r"\s{2,}", " ", "".join(out)).strip()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Angelic ⇄ Demonic Translator (Deterministic)", page_icon="🗝️")
st.markdown("<h1 style='font-size:2.2em; font-family:serif;'>🗝️ Angelic ⇄ Demonic Translator</h1>", unsafe_allow_html=True)
st.markdown(f"<div style='font-size:1.2em; color:#5b0a0a; margin-bottom:16px'>{to_fraktur('Purity or Perdition—your words decide.')}</div>", unsafe_allow_html=True)

corruption = st.slider("Corruption (1 = angel 😇, 100 = demon 😈)", 1, 100, 35)
text = st.text_area("Enter English text:", "")

if text:
    stylized, voice_used, voice_int = stylize_sentence_corruption(text, corruption)
    st.markdown(f"**Mode:** `{voice_used}` • **Intensity:** `{voice_int}`")
    st.markdown("**Stylized (deterministic at this slider value):**")
    st.markdown(f"<div style='font-size:1.2em'>{stylized}</div>", unsafe_allow_html=True)

    st.markdown("**Reverse-Translated (no slider needed):**")
    st.code(reverse_translate(stylized), language="text")

st.write("---")
st.subheader("🔎 Find the slider value that produced a stylized text")

col1, col2 = st.columns(2)
with col1:
    original_eng = st.text_area("Original English (what you think was encoded)", "", key="orig2")
with col2:
    given_stylized = st.text_area("Given stylized text to match", "", key="sty2")

if st.button("Find corruption value (1..100)"):
    if not original_eng or not given_stylized:
        st.warning("Provide both the original English and the stylized text.")
    else:
        match_val = None
        for k in range(1, 101):
            gen, _, _ = stylize_sentence_corruption(original_eng, k)
            if gen == given_stylized:
                match_val = k
                break
        if match_val is not None:
            st.success(f"Found exact match at corruption **{match_val}**.")
        else:
            st.error("No exact match in 1..100 (different text or different algorithm).")

# Decode any stylized text (works regardless of slider)
st.write("---")
st.subheader("🧹 Decode any stylized text to English")
to_decode = st.text_area("Paste stylized text:", "", key="dec")
if to_decode:
    st.code(reverse_translate(to_decode), language="text")

