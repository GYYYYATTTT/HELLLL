#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# infernal_angel_translator_app.py
import random, re, unicodedata
import streamlit as st

# ================== Tokenizer & helpers ==================
TOK_RE = re.compile(r"(\w+|\s+|[^\w\s]+)", re.UNICODE)  # words | whitespace | punctuation
INV = "\u2063"  # Invisible Separator to mark inserts (prefix/suffix/oaths/latinisms)

def mark_insert(s):   return INV + s + INV
def unmark_all(s):    return s.replace(INV, "")

def to_fraktur(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    fraktur = [
        "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷"
    ]
    mapping = {c: f for c, f in zip(normal, fraktur[0] + fraktur[1])}
    return ''.join(mapping.get(ch, ch) for ch in text)

# ================== Style tables ==================
DEMON_PERSONAS = ("Baal", "Mephisto", "Imp")

# shared vowels (dark = demon; bright = angel) – decoder strips diacritics
_VOWELS_DEMON = {
    'a': ['â','à','ä','á','a'],
    'e': ['ê','è','ë','é','e'],
    'i': ['î','ï','ì','í','i'],
    'o': ['ô','ö','ò','ó','o'],
    'u': ['û','ü','ù','ú','u'],
    'y': ['ŷ','ÿ','y'],
}
_VOWELS_ANGEL = {
    'a': ['ā','a'],
    'e': ['ē','e'],
    'i': ['ī','i'],
    'o': ['ō','o'],
    'u': ['ū','u'],
    'y': ['ȳ','y'],
}

# reversible digraph swaps
_DIGRAPHS_DEMON = [
    ('the','ðe'), ('The','Ðe'),
    ('th','þ'),   ('Th','Þ'),
    ('sh','ʃ'),   ('Sh','ʃ'),
    ('ch','χ'),   ('Ch','Χ'),
    ('ph','ƒ'),   ('Ph','Ƒ'),
    ('qu','q͟u'), ('Qu','Q͟u')
]
# angelic set keeps it gentle & readable (also fully reversible)
_DIGRAPHS_ANGEL = [
    ('the','θe'), ('The','Θe'),
    ('sh','š'),   ('Sh','Š'),
    ('ph','φ'),   ('Ph','Φ'),
    # (skip ch to avoid looking too harsh; leave qu alone)
]

_AFFIXES = {
    'Baal': (["ba’","’ba"], ["-oth","-’rim","-az"]),
    'Mephisto': (["me’","’me"], ["-ius","-orum","-atrix"]),
    'Imp': (["za’","ka’","’za"], ["-zik","-gob","-’hii"]),
    'Angel': (["el’","sa’","’el"], ["-iel","-ael","-hosanna"]),
}
_OATHS = {
    'Baal': ["⟨behold⟩","⟨thus bound⟩"],
    'Mephisto': ["⟨by pact⟩","⟨ipso facto⟩","⟨inter alia⟩"],
    'Imp': ["⟨khkh⟩","⟨hehe⟩"],
    'Angel': ["⟨amen⟩","⟨selah⟩","⟨gloria⟩","⟨hallelujah⟩"],
}

_ZALGO_LIGHT = [u"\u0301", u"\u0302", u"\u0308", u"\u0336", u"\u034f"]
_ZALGO_HEAVY = _ZALGO_LIGHT + [u"\u0317", u"\u0316", u"\u0352", u"\u035B", u"\u0360", u"\u0362"]

# ================== Optional add-ons kept from before ==================
ARCHAIC_PAIRS = [
    ("you are","thou art"),
    ("you will","thou shalt"),
    ("shall not","shalt not"),
    ("your","thy"),
    ("yours","thine"),
    ("you","thou"),
]
def replace_ci_bound(text, src, dst):
    def repl(m):
        g = m.group(0)
        if g.isupper():         return dst.upper()
        if g[0].isupper():      return dst.capitalize()
        return dst
    return re.sub(rf"\b{re.escape(src)}\b", repl, text, flags=re.IGNORECASE)

def apply_archaic_pronouns(text):
    s = text
    for a,b in sorted(ARCHAIC_PAIRS, key=lambda x: len(x[0]), reverse=True):
        s = replace_ci_bound(s, a, b)
    return s

LATINISMS = ["ergo", "inter alia", "ipso facto", "sine die", "ad infinitum", "mutatis mutandis"]
def sprinkle_latinisms(sentence, rate=0.18):
    tokens = TOK_RE.findall(sentence)
    out = []
    for t in tokens:
        out.append(t)
        if t.strip() and t[-1:].isalnum() and random.random() < rate:
            out.append(mark_insert("⟨" + random.choice(LATINISMS) + "⟩"))
    return "".join(out)

# ================== Encoders ==================
def _style_word_demon(word, persona="Mephisto", intensity=2, glitch_mode=False, strict=False):
    if not word or not word.isalnum():
        return word
    pre_opts, suf_opts = _AFFIXES[persona]

    if random.random() < 0.12*intensity:
        word = mark_insert(random.choice(pre_opts)) + word
    if random.random() < 0.10*intensity:
        word = word + mark_insert(random.choice(suf_opts))

    for a,b in _DIGRAPHS_DEMON:
        word = word.replace(a,b)

    out = []
    for c in word:
        lc = c.lower()
        if lc in _VOWELS_DEMON and random.random() < (0.5 + 0.15*intensity):
            rep = random.choice(_VOWELS_DEMON[lc][:-1])
            out.append(rep.upper() if c.isupper() else rep); continue
        if strict:
            out.append(c); continue
        if lc == 's' and random.random() < 0.5:
            out.append('ſ' if c.islower() else 'S'); continue
        if lc == 't' and random.random() < 0.25:
            out.append('†'); continue
        if lc == 'h' and random.random() < 0.25:
            out.append('ʰ'); continue
        if lc == 'n' and random.random() < 0.20:
            out.append('ñ'); continue
        if c == "'":
            out.append(random.choice(["'", "’"])); continue
        if (glitch_mode or intensity >= 3) and c.isalpha() and random.random() < (0.12 if glitch_mode else 0.18):
            marks = _ZALGO_HEAVY if glitch_mode else _ZALGO_LIGHT
            stack = 1 + int(glitch_mode and random.random() < 0.5)
            out.append(c + "".join(random.choice(marks) for _ in range(stack))); continue
        out.append(c)
    return "".join(out)

def _style_word_angel(word, intensity=2, strict=False):
    if not word or not word.isalnum():
        return word
    pre_opts, suf_opts = _AFFIXES['Angel']

    if random.random() < 0.10*intensity:
        word = mark_insert(random.choice(pre_opts)) + word
    if random.random() < 0.08*intensity:
        word = word + mark_insert(random.choice(suf_opts))

    for a,b in _DIGRAPHS_ANGEL:
        word = word.replace(a,b)

    out = []
    for c in word:
        lc = c.lower()
        if lc in _VOWELS_ANGEL and random.random() < (0.45 + 0.12*intensity):
            rep = _VOWELS_ANGEL[lc][0]  # macron form
            out.append(rep.upper() if c.isupper() else rep); continue
        # keep strict ≈ same meaning: avoid extra ornaments
        out.append(c)
    return "".join(out)

def stylize_sentence_corruption(sentence, demon_persona="Mephisto", corruption=35, archaic=False, latinisms=False, glitch_mode=False, strict=False):
    """
    corruption: 0..100  (0=angel, 100=demon)
    """
    s = sentence
    tokens = TOK_RE.findall(s)

    # decide voice & intensity from slider
    if corruption < 40:
        # Angelic
        intensity_ang = max(1, 3 - int(corruption/14))  # 0-13→3, 14-27→2, 28-39→1
        # oath insert (gentle)
        if random.random() < 0.08*intensity_ang:
            tokens.insert(0 if random.random()<0.5 else len(tokens), mark_insert(random.choice(_OATHS['Angel'])))
        out = []
        for t in tokens:
            if t.isalnum():
                out.append(_style_word_angel(t, intensity=intensity_ang, strict=strict))
            else:
                out.append(t)
        return "".join(out), "Angel", intensity_ang

    # Middle band: slight touch only (pass-through, no oaths)
    if corruption < 55:
        return s, "Neutral", 0

    # Demon side
    intensity_dem = min(3, 1 + int((corruption-55)/15))  # 55-69→1, 70-84→2, 85-100→3
    if demon_persona == "Baal" and archaic:
        s = apply_archaic_pronouns(s)

    tokens = TOK_RE.findall(s)
    if random.random() < 0.12*intensity_dem:
        oath = random.choice(_OATHS.get(demon_persona, []))
        if oath:
            tokens.insert(0 if random.random()<0.5 else len(tokens), mark_insert(oath))

    out = []
    for t in tokens:
        if t.isalnum():
            if t == "I" and demon_persona != "Imp":
                out.append("Ì")
            else:
                out.append(_style_word_demon(t, persona=demon_persona, intensity=intensity_dem, glitch_mode=(glitch_mode or corruption>=85), strict=strict))
        else:
            out.append(t)
    if demon_persona == "Mephisto" and latinisms:
        return sprinkle_latinisms("".join(out), rate=0.16 + 0.04*intensity_dem), demon_persona, intensity_dem
    return "".join(out), demon_persona, intensity_dem

# ================== Decoder ==================
def decore_word(w):
    # undo both angelic & demonic digraphs
    back = [
        # demon
        ('ðe','the'), ('Ðe','The'),
        ('þ','th'),   ('Þ','Th'),
        ('ʃ','sh'),   ('Χ','Ch'), ('χ','ch'),
        ('ƒ','ph'),   ('Ƒ','Ph'),
        ('q͟u','qu'), ('Q͟u','Qu'),
        # angel
        ('θ','th'),   ('Θ','Th'),
        ('š','sh'),   ('Š','Sh'),
        ('φ','ph'),   ('Φ','Ph'),
    ]
    for a,b in back:
        w = w.replace(a,b)

    # strip ornaments (demon) + normalize apostrophe char
    w = (w.replace('ſ','s')
           .replace('ŕ','r')
           .replace('†','t')
           .replace('ʰ','h')
           .replace('ñ','n')
           .replace('Ì','I')
           .replace("’","'"))

    # remove combining marks (covers zalgo & macrons)
    w = ''.join(c for c in unicodedata.normalize('NFD', w)
                if unicodedata.category(c) != 'Mn')

    # de-accent vowels (in case any remain)
    w = w.translate(str.maketrans("âàäáêèëéîïìíôöòóûüùúŷÿāēīōūȳ",
                                  "aaaaeeeeiiiioooouuuuyyaeiouy"))
    return w

def de_demonify_sentence(text, decode_archaic=False, strip_latinisms=True):
    s = unmark_all(text)

    if strip_latinisms:
        s = re.sub(r"⟨[^⟩]+⟩", "", s)

    tokens = TOK_RE.findall(s)
    # strip all known affixes (angel + demon)
    prefixes = set(sum([v[0] for v in _AFFIXES.values()], []))
    suffixes = set(sum([v[1] for v in _AFFIXES.values()], []))

    def strip_affixes_token(tok):
        for pre in sorted(prefixes, key=len, reverse=True):
            if tok.startswith(pre):
                tok = tok[len(pre):]; break
        for suf in sorted(suffixes, key=len, reverse=True):
            if tok.endswith(suf):
                tok = tok[:-len(suf)]; break
        return tok

    cleaned = []
    for t in tokens:
        if t.isalnum():
            w = strip_affixes_token(decore_word(t))
            cleaned.append(w)
        else:
            cleaned.append(t)

    s2 = "".join(cleaned)

    if decode_archaic:
        back_pairs = [
            ("thou art","you are"),
            ("thou shalt","you will"),
            ("shalt not","shall not"),
            ("thy","your"),
            ("thine","yours"),
            ("thou","you"),
        ]
        for a,b in sorted(back_pairs, key=lambda x: len(x[0]), reverse=True):
            s2 = replace_ci_bound(s2, a, b)

    s2 = re.sub(r"\s{2,}", " ", s2).strip()
    return s2

# ================== Streamlit UI ==================
st.set_page_config(page_title="Angelic ⇄ Infernal Translator", page_icon="😇")

st.markdown("<h1 style='font-size:2.6em; font-family:serif;'>😇 Angelic ⇄ Infernal Translator 😈</h1>", unsafe_allow_html=True)
headline = "Purity or Perdition—your words decide."
st.markdown(f"<div style='font-size:1.9em; color:#5b0a0a; margin-bottom:16px'>{to_fraktur(headline)}</div>", unsafe_allow_html=True)
st.write("Slide the **Corruption** control: left speaks like an angel, right speaks like a demon. Middle keeps it mostly plain.")

# Controls
corruption = st.slider("Corruption (😇 → 😈)", 0, 100, 35)
demon_persona = st.selectbox("Demon persona (used when corrupted):", DEMON_PERSONAS, index=1)

c1, c2, c3, c4 = st.columns([1.2,1.2,1.6,1.4])
with c1:
    archaic = st.checkbox("Archaic (Baal)", value=(demon_persona=="Baal"))
with c2:
    latinisms = st.checkbox("Latinisms (Mephisto)", value=(demon_persona=="Mephisto"))
with c3:
    glitch_mode = st.checkbox("Glitch mode (extra Zalgo)", value=False)
with c4:
    strict = st.checkbox("Strict reversible mode", value=False)

seed_val = st.text_input("Seed (optional)", value="")
if seed_val.strip():
    try: random.seed(int(seed_val.strip()))
    except ValueError: random.seed(seed_val.strip())

# --- Box 1: English → Stylized ---
text = st.text_area("Enter English text:", "")

if text:
    stylized, voice_used, voice_int = stylize_sentence_corruption(
        text,
        demon_persona=demon_persona,
        corruption=corruption,
        archaic=archaic,
        latinisms=latinisms,
        glitch_mode=glitch_mode,
        strict=strict
    )
    st.markdown(f"**Voice:** `{voice_used}`  •  **Intensity:** `{voice_int}`")
    st.markdown("**Stylized:**")
    st.markdown(f"<div style='font-size:1.35em'>{stylized}</div>", unsafe_allow_html=True)

    st.markdown("**Stylized (Fraktur):**")
    st.markdown(f"<div style='font-size:1.05em'>{to_fraktur(stylized)}</div>", unsafe_allow_html=True)

    english_guess = de_demonify_sentence(
        stylized,
        decode_archaic=(voice_used=='Baal' or (demon_persona=='Baal' and corruption>=55)),
        strip_latinisms=True
    )
    st.markdown("**Reverse-Translated (guess):**")
    st.markdown(f"<div style='font-size:1.05em'>{english_guess}</div>", unsafe_allow_html=True)

st.write("---")
st.write("Or paste any stylized text (angelic or infernal) to decode:")

stylized_input = st.text_area("Paste stylized here:", "")
if stylized_input:
    colx, coly = st.columns(2)
    with colx:
        dec_arch = st.checkbox("Decode archaic pronouns", value=True, key="dec_arch")
    with coly:
        dec_lat = st.checkbox("Strip Latinisms", value=True, key="dec_lat")

    english_decoded = de_demonify_sentence(
        stylized_input,
        decode_archaic=dec_arch,
        strip_latinisms=dec_lat
    )
    st.markdown("**Reverse-Translated:**")
    st.markdown(f"<div style='font-size:1.15em'>{english_decoded}</div>", unsafe_allow_html=True)

