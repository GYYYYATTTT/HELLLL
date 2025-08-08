#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import random
import unicodedata
import streamlit as st

# ================== Fancy header helper you already had ==================
def to_fraktur(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    fraktur = [
        "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷"
    ]
    mapping = {c: f for c, f in zip(normal, fraktur[0] + fraktur[1])}
    return ''.join(mapping.get(ch, ch) for ch in text)

# ================== Demon core ==================
DEMON_PERSONAS = ("Baal", "Mephisto", "Imp")

_VOWELS = {
    'a': ['â','à','ä','á','a'],
    'e': ['ê','è','ë','é','e'],
    'i': ['î','ï','ì','í','i'],
    'o': ['ô','ö','ò','ó','o'],
    'u': ['û','ü','ù','ú','u'],
    'y': ['ŷ','ÿ','y'],
}
_DIGRAPHS = [
    ('the','ðe'), ('The','Ðe'),
    ('th','þ'),   ('Th','Þ'),
    ('sh','ʃ'),   ('Sh','ʃ'),
    ('ch','χ'),   ('Ch','Χ'),
    ('ph','ƒ'),   ('Ph','Ƒ'),
    ('qu','q͟u'), ('Qu','Q͟u')
]
_AFFIXES = {
    'Baal': (["ba’","’ba"], ["-oth","-’rim","-az"]),
    'Mephisto': (["me’","’me"], ["-ius","-orum","-atrix"]),
    'Imp': (["za’","ka’","’za"], ["-zik","-gob","-’hii"])
}
_OATHS = {
    'Baal': ["⟨behold⟩","⟨thus bound⟩"],
    'Mephisto': ["⟨by pact⟩","⟨ipso facto⟩","⟨inter alia⟩"],
    'Imp': ["⟨khkh⟩","⟨hehe⟩"]
}

# Light → heavy Zalgo sets; decoder strips all combining marks anyway
_ZALGO_LIGHT = [u"\u0301", u"\u0302", u"\u0308", u"\u0336", u"\u034f"]
_ZALGO_HEAVY = _ZALGO_LIGHT + [u"\u0317", u"\u0316", u"\u0352", u"\u035B", u"\u0360", u"\u0362"]

# ===== Optional add-ons (encoding-time) =====
ARCHAIC_MAP = {
    # order matters: longer tokens first
    "you are": "thou art",
    "you will": "thou shalt",
    "shall not": "shalt not",
    "your": "thy",
    "yours": "thine",
    "you": "thou",
    "are": "art",   # be careful, only used in Baal mode and coarse
}
LATINISMS = ["ergo", "inter alia", "ipso facto", "sine die", "ad infinitum", "mutatis mutandis"]

def apply_archaic_pronouns(text):
    # very lightweight, phrase-level replacements
    s = text
    for k in sorted(ARCHAIC_MAP.keys(), key=len, reverse=True):
        s = s.replace(k, ARCHAIC_MAP[k]).replace(k.capitalize(), ARCHAIC_MAP[k].capitalize())
    return s

def sprinkle_latinisms(sentence, rate=0.18):
    """Insert short Latinisms at comma/space boundaries; decoder can remove them."""
    tokens = sentence.split()
    out = []
    for i, t in enumerate(tokens):
        out.append(t)
        if random.random() < rate and t[-1].isalnum():
            out.append("⟨" + random.choice(LATINISMS) + "⟩")
    return " ".join(out)

def demon_style(word, persona="Mephisto", intensity=2, glitch_mode=False):
    if not word:
        return word

    pre_opts, suf_opts = _AFFIXES.get(persona, _AFFIXES['Mephisto'])

    # affixes (scale by intensity)
    if random.random() < 0.12*intensity and word[0].isalnum():
        word = random.choice(pre_opts) + word
    if random.random() < 0.10*intensity and word[-1].isalnum():
        word = word + random.choice(suf_opts)

    # digraph swaps
    w2 = word
    for a,b in _DIGRAPHS:
        if a in w2:
            w2 = w2.replace(a,b)

    # per-char tweaks
    out = []
    for i, c in enumerate(w2):
        lc = c.lower()

        # vowels (darken)
        if lc in _VOWELS and random.random() < (0.5 + 0.15*intensity):
            pool = _VOWELS[lc]
            rep = random.choice(pool[:-1])  # prefer diacritics
            rep = rep.upper() if c.isupper() else rep
            out.append(rep)
            continue

        # medial s → ſ
        if lc == 's' and 0 < i < len(w2)-1 and w2[i-1].isalnum() and w2[i+1].isalnum():
            if random.random() < (0.45 + 0.15*intensity):
                out.append('ſ' if c.islower() else 'S')
                continue

        # r, t, h, n spices
        if lc == 'r' and random.random() < 0.35:
            out.append('ŕ' if c.islower() else 'R'); continue
        if lc == 't' and random.random() < 0.25:
            out.append('†'); continue
        if lc == 'h' and random.random() < 0.25:
            out.append('ʰ'); continue
        if lc == 'n' and random.random() < 0.20:
            out.append('ñ'); continue

        if c == "'":
            out.append(random.choice(["'", "’"])); continue

        # glitch mode or intensity 3: add combining marks
        if (glitch_mode or intensity >= 3) and c.isalpha() and random.random() < (0.12 if glitch_mode else 0.18):
            marks = _ZALGO_HEAVY if glitch_mode else _ZALGO_LIGHT
            # maybe stack 1–2 marks when glitch_mode
            stack = 1 + int(glitch_mode and random.random() < 0.5)
            out.append(c + "".join(random.choice(marks) for _ in range(stack)))
            continue

        out.append(c)

    return "".join(out)

def demon_stylize_sentence(sentence, persona="Mephisto", intensity=2, archaic=False, latinisms=False, glitch_mode=False):
    s = sentence

    # persona-based pre-style
    if persona == "Baal" and archaic:
        s = apply_archaic_pronouns(s.lower())

    # optional oath insert
    tokens = s.split()
    if tokens and random.random() < 0.12*intensity:
        oath = random.choice(_OATHS.get(persona, []))
        if oath:
            where = random.choice([0, len(tokens)])
            tokens.insert(where, oath)
    s = " ".join(tokens)

    # optional Latinisms sprinkle
    if persona == "Mephisto" and latinisms:
        s = sprinkle_latinisms(s, rate=0.16 + 0.04*intensity)

    # word-level styling
    out = []
    for w in s.split():
        if w == "I" and persona != "Imp":
            out.append("Ì")
        else:
            out.append(demon_style(w, persona, intensity, glitch_mode=glitch_mode))
    return " ".join(out)

# ================== Decoder (adds options to undo add-ons) ==================
def de_demonify_word(word):
    # strip known affixes (both directions)
    prefixes = set(sum([v[0] for v in _AFFIXES.values()], []))
    suffixes = set(sum([v[1] for v in _AFFIXES.values()], []))
    for pre in sorted(prefixes, key=len, reverse=True):
        if word.startswith(pre):
            word = word[len(pre):]; break
    for suf in sorted(suffixes, key=len, reverse=True):
        if word.endswith(suf):
            word = word[:-len(suf)]; break

    # undo digraphs
    back = [
        ('ðe','the'), ('Ðe','The'),
        ('þ','th'),   ('Þ','Th'),
        ('ʃ','sh'),   ('Χ','Ch'), ('χ','ch'),
        ('ƒ','ph'),   ('Ƒ','Ph'),
        ('q͟u','qu'), ('Q͟u','Qu'),
    ]
    for a,b in back:
        word = word.replace(a,b)

    # strip ornaments
    word = (word
            .replace('ſ','s')
            .replace('ŕ','r')
            .replace('†','t')
            .replace('ʰ','h')
            .replace('ñ','n')
            .replace('Ì','I')
            .replace("’","'"))

    # remove combining marks (covers glitch/zalgo)
    word = ''.join(c for c in unicodedata.normalize('NFD', word)
                   if unicodedata.category(c) != 'Mn')

    # de-accent vowels
    trans = str.maketrans("âàäáêèëéîïìíôöòóûüùúŷÿ",
                          "aaaaeeeeiiiioooouuuuyy")
    word = word.translate(trans)
    return word

def de_demonify_sentence(sentence, decode_archaic=False, strip_latinisms=False):
    # remove ⟨latinism⟩ tokens if requested
    if strip_latinisms:
        sentence = " ".join(t for t in sentence.split() if not (t.startswith("⟨") and t.endswith("⟩")))

    # per-word cleanup
    s = " ".join(de_demonify_word(w) for w in sentence.split())

    if decode_archaic:
        # map common archaic → modern
        back_map = {
            "thou art": "you are",
            "thou shalt": "you will",
            "shalt not": "shall not",
            "thy": "your",
            "thine": "yours",
            "thou": "you",
            "art": "are",
        }
        for k in sorted(back_map.keys(), key=len, reverse=True):
            s = s.replace(k, back_map[k]).replace(k.capitalize(), back_map[k].capitalize())
    return s

# ================== Streamlit UI ==================
st.set_page_config(page_title="Infernal Translator", page_icon="🔥")
st.markdown("<h1 style='font-size:2.7em; font-family:serif;'>🔥 Infernal Translator</h1>", unsafe_allow_html=True)
headline = "By Pact, Speak Thou Plain"
st.markdown(f"<div style='font-size:2em; color:#5b0a0a; margin-bottom:16px'>{to_fraktur(headline)}</div>", unsafe_allow_html=True)

# Controls
persona = st.selectbox("Choose your demon persona:", DEMON_PERSONAS, index=1)
intensity = st.slider("Corruption intensity", 1, 3, 2)
colA, colB, colC, colD = st.columns(4)
with colA:
    archaic = st.checkbox("Archaic mode (Baal)", value=(persona=="Baal"))
with colB:
    latinisms = st.checkbox("Latinisms (Mephisto)", value=(persona=="Mephisto"))
with colC:
    glitch_mode = st.checkbox("Glitch mode (extra Zalgo)", value=False)
with colD:
    seed_val = st.text_input("Seed (optional)", value="")

# Seed control for reproducibility
if seed_val.strip():
    try:
        random.seed(int(seed_val.strip()))
    except ValueError:
        random.seed(seed_val.strip())  # fallback: hash string

st.write("Type English below to see Infernal text and the reverse translation:")

text = st.text_area("Enter English text:", "")

if text:
    infernal = demon_stylize_sentence(
        text,
        persona=persona,
        intensity=intensity,
        archaic=archaic,
        latinisms=latinisms,
        glitch_mode=glitch_mode
    )
    st.markdown("**Infernal:**")
    st.markdown(f"<div style='font-size:1.4em'>{infernal}</div>", unsafe_allow_html=True)
    st.markdown("**Infernal (Fraktur):**")
    st.markdown(f"<div style='font-size:1.1em'>{to_fraktur(infernal)}</div>", unsafe_allow_html=True)

    english_guess = de_demonify_sentence(
        infernal,
        decode_archaic=archaic and persona=="Baal",
        strip_latinisms=latinisms and persona=="Mephisto"
    )
    st.markdown("**Reverse-Translated (guess):**")
    st.markdown(f"<div style='font-size:1.1em'>{english_guess}</div>", unsafe_allow_html=True)

st.write("---")
st.write("Or paste Infernal text below to decode back to English:")

infernal_input = st.text_area("Paste Infernal here:", "")
if infernal_input:
    english_decoded = de_demonify_sentence(
        infernal_input,
        decode_archaic=st.checkbox("Decode archaic pronouns", value=True, key="dec_arch"),
        strip_latinisms=st.checkbox("Strip Latinisms", value=True, key="dec_lat")
    )
    st.markdown("**Reverse-Translated:**")
    st.markdown(f"<div style='font-size:1.2em'>{english_decoded}</div>", unsafe_allow_html=True)

