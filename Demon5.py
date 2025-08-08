#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# angel_demon_translator_tts_final.py
import random, re, unicodedata, json
import requests
import streamlit as st

# ================== Tokenizer & helpers ==================
TOK_RE = re.compile(r"(\w+|\s+|[^\w\s]+)", re.UNICODE)  # words | whitespace | punctuation
INV = "\u2063"  # Invisible Separator to mark inserts (prefix/suffix)

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

# ================== Simple angel/demon styling (reversible) ==================
_VOWELS_ANGEL = {'a':['ā','a'],'e':['ē','e'],'i':['ī','i'],'o':['ō','o'],'u':['ū','u'],'y':['ȳ','y']}
_DIGRAPHS_ANGEL = [('the','θe'),('The','Θe'),('sh','š'),('Sh','Š'),('ph','φ'),('Ph','Φ')]

_VOWELS_DEMON = {'a':['â','a'],'e':['ê','e'],'i':['î','i'],'o':['ô','o'],'u':['û','u'],'y':['ŷ','y']}
_DIGRAPHS_DEMON = [('the','ðe'),('The','Ðe'),('th','þ'),('Th','Þ'),('sh','ʃ'),('Sh','ʃ'),
                   ('ph','ƒ'),('Ph','Ƒ'),('qu','q͟u'),('Qu','Q͟u')]

def _style_word(word, angel=False, intensity=2):
    if not word or not word.isalnum():
        return word
    vowels = _VOWELS_ANGEL if angel else _VOWELS_DEMON
    out = []
    for c in word:
        lc = c.lower()
        if lc in vowels and random.random() < (0.35 + 0.12*intensity):
            rep = vowels[lc][0]
            out.append(rep.upper() if c.isupper() else rep); continue
        out.append(c)
    return "".join(out)

def stylize_sentence_corruption(sentence, corruption=35, seed=None):
    """
    corruption: 0..100 (0=angel, 100=demon)
    Returns stylized_text, voice_mode ('Angel'|'Neutral'|'Demon'), voice_intensity (1..3)
    """
    if seed:
        random.seed(seed)

    s = sentence
    tokens = TOK_RE.findall(s)

    if corruption < 40:
        angel = True
        intensity = max(1, 3 - int(corruption/14))  # 0-13→3, 14-27→2, 28-39→1
        if random.random() < 0.06 * intensity:
            tokens.insert(0 if random.random() < 0.5 else len(tokens), mark_insert("⟨amen⟩"))
        out = []
        for t in tokens:
            out.append(_style_word(t, angel=True, intensity=intensity) if t.isalnum() else t)
        return "".join(out), "Angel", intensity

    if corruption < 55:
        return s, "Neutral", 0

    # Demon side
    intensity = min(3, 1 + int((corruption-55)/15))  # 55-69→1, 70-84→2, 85-100→3
    if random.random() < 0.09 * intensity:
        tokens.insert(0 if random.random() < 0.5 else len(tokens), mark_insert("⟨by pact⟩"))

    s2 = "".join(tokens)
    for a,b in _DIGRAPHS_DEMON:
        s2 = s2.replace(a,b)
    out = []
    for t in TOK_RE.findall(s2):
        out.append(_style_word(t, angel=False, intensity=intensity) if t.isalnum() else t)
    return "".join(out), "Demon", intensity

# ================== Decoder (for the display “Reverse-Translated”) ==================
def decore_word(w):
    back = [
        ('ðe','the'), ('Ðe','The'), ('þ','th'), ('Þ','Th'), ('ʃ','sh'), ('ƒ','ph'), ('Ƒ','Ph'),
        ('q͟u','qu'), ('Q͟u','Qu'), ('θ','th'), ('Θ','Th'), ('š','sh'), ('Š','Sh'), ('φ','ph'), ('Φ','Ph'),
    ]
    for a,b in back:
        w = w.replace(a,b)
    w = ''.join(c for c in unicodedata.normalize('NFD', w) if unicodedata.category(c) != 'Mn')
    w = w.translate(str.maketrans("âêîôûŷāēīōūȳ", "aeiouyaeiouy"))
    return w

def reverse_translate(text):
    s = unmark_all(text)
    tokens = TOK_RE.findall(s)
    out = []
    for t in tokens:
        if t.isalnum():
            out.append(decore_word(t))
        elif t.startswith("⟨") and t.endswith("⟩"):
            continue
        else:
            out.append(t)
    return re.sub(r"\s{2,}", " ", "".join(out)).strip()

# ================== ElevenLabs TTS ==================
def tts_elevenlabs(text, api_key, voice_id, stability=0.5, similarity=0.8, style=0.3):
    """
    Returns bytes (mp3). Raises on error.
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity,
            "style": style,
            "use_speaker_boost": True
        }
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    return r.content

# ================== UI ==================
st.set_page_config(page_title="Angelic ⇄ Demonic Translator (Real Voices)", page_icon="🔊")
st.markdown("<h1 style='font-size:2.4em; font-family:serif;'>🔊 Angelic ⇄ Demonic Translator</h1>", unsafe_allow_html=True)
st.markdown(f"<div style='font-size:1.4em; color:#5b0a0a; margin-bottom:16px'>{to_fraktur('Purity or Perdition—your words decide.')}</div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔐 ElevenLabs (real voices)")
    api_key = st.text_input("ElevenLabs API Key", value="sk_09c439f46b32383ce61f4ddb237a6d270868b76f28490284")
    angel_voice = st.text_input("Angelic Voice ID", value="kJKMPwrIKzwVkMKOfRtr")
    demon_voice = st.text_input("Demonic Voice ID", value="si0svtk05vPEuvwAW93c")

# Controls
corruption = st.slider("Corruption (😇 → 😈)", 0, 100, 35)
seed_val = st.text_input("Seed (optional for consistent styling)", "")

# Input
text = st.text_area("Enter English text:", "")

stylized = ""
voice_used = "Neutral"
voice_int = 0

if text:
    stylized, voice_used, voice_int = stylize_sentence_corruption(
        text,
        corruption=corruption,
        seed=(seed_val.strip() or None),
    )
    st.markdown(f"**Voice:** `{voice_used}`  •  **Intensity:** `{voice_int}`")
    st.markdown("**Stylized (this is what will be spoken):**")
    st.markdown(f"<div style='font-size:1.3em'>{stylized}</div>", unsafe_allow_html=True)

    st.markdown("**Reverse-Translated (for reference):**")
    st.code(reverse_translate(stylized), language="text")

st.write("---")
st.subheader("🔈 Speak (reads the stylized text only)")

use_eleven = bool(api_key and ((voice_used == "Angel" and angel_voice) or (voice_used == "Demon" and demon_voice) or (voice_used == "Neutral" and (angel_voice or demon_voice))))

def default_tts_params_for(voice_used, corruption):
    if voice_used == "Angel":
        return dict(stability=0.5, similarity=0.8, style=0.35)
    if voice_used == "Demon":
        # darker style; lower stability for rasp/texture at high corruption
        return dict(stability=(0.35 if corruption >= 85 else 0.45),
                    similarity=0.75,
                    style=(0.65 if corruption >= 85 else 0.5))
    return dict(stability=0.5, similarity=0.8, style=0.4)

if not text:
    st.info("Type some text above first.")
else:
    if use_eleven:
        vid = angel_voice if voice_used == "Angel" else demon_voice if voice_used == "Demon" else (angel_voice or demon_voice)
        params = default_tts_params_for(voice_used, corruption)

        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            if st.button("🔊 Generate Voice (ElevenLabs)"):
                try:
                    audio = tts_elevenlabs(stylized, api_key, vid, **params)
                    st.session_state["last_audio"] = audio
                    st.success("Audio generated from stylized text.")
                except Exception as e:
                    st.error(f"TTS failed: {e}")

        with c2:
            if st.button("⚡ Quick Test (very short sample)"):
                try:
                    sample_text = "Amen." if voice_used == "Angel" else "Speak."
                    audio = tts_elevenlabs(sample_text, api_key, vid, **params)
                    st.session_state["last_audio"] = audio
                    st.success("Quick test audio generated.")
                except Exception as e:
                    st.error(f"TTS test failed: {e}")

        with c3:
            if st.button("🗑️ Clear last audio"):
                st.session_state.pop("last_audio", None)

        audio_bytes = st.session_state.get("last_audio")
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button("Download MP3", data=audio_bytes, file_name="voice.mp3", mime="audio/mpeg")

    else:
        # Fallback: Browser speech API (reads STYLIZED text as well)
        st.caption("No ElevenLabs config — using browser speech (quality depends on your device).")
        if voice_used == "Angel":
            rate, pitch = 1.05, 1.25
        elif voice_used == "Demon":
            rate, pitch = (0.85 if corruption >= 85 else 0.95), (0.75 if corruption >= 85 else 0.9)
        else:
            rate, pitch = 1.0, 1.0

        st.write("Click **Speak** to hear the stylized text. Works best in Chrome/Edge.")
        payload = {"text": stylized or "", "rate": rate, "pitch": pitch, "volume": 1.0}
        html = f"""
        <div style="display:flex;gap:8px;align-items:center;margin:6px 0 12px;">
          <button id="speakBtn" style="padding:8px 14px;border-radius:8px;border:1px solid #555;cursor:pointer;">Speak</button>
          <button id="stopBtn" style="padding:8px 14px;border-radius:8px;border:1px solid #555;cursor:pointer;">Stop</button>
          <span id="voiceStatus" style="margin-left:8px;color:#666;font-size:0.9em;"></span>
        </div>
        <script>
        (function() {{
          const data = {json.dumps(payload)};
          const synth = window.speechSynthesis;
          const status = document.getElementById("voiceStatus");
          const speakBtn = document.getElementById("speakBtn");
          const stopBtn = document.getElementById("stopBtn");
          const txt = data.text || "";
          const rate = Number(data.rate) || 1.0;
          const pitch = Number(data.pitch) || 1.0;
          const volume = Number(data.volume) || 1.0;

          function pickVoice() {{
            const voices = synth.getVoices() || [];
            const en = voices.filter(v => /en(-|_|\\b)/i.test(v.lang) || /English/i.test(v.name));
            return en[0] || voices[0] || null;
          }}

          function speakNow() {{
            if (!('speechSynthesis' in window)) {{
              status.textContent = "Not supported in this browser.";
              return;
            }}
            synth.cancel();
            const u = new SpeechSynthesisUtterance(txt);
            u.rate = rate; u.pitch = pitch; u.volume = volume;
            const v = pickVoice();
            if (v) u.voice = v;
            synth.speak(u);
            status.textContent = "Speaking" + (v ? " with " + v.name : "") + "...";
            u.onend = () => status.textContent = "Done.";
            u.onerror = () => status.textContent = "Speech error.";
          }}

          speakBtn.onclick = speakNow;
          stopBtn.onclick = () => {{ synth.cancel(); status.textContent = "Stopped."; }};
        }})();
        </script>
        """
        st.components.v1.html(html, height=70)

# --- Decoder box ---
st.write("---")
st.write("Or paste any stylized text (angelic/demonic) to decode:")
stylized_input = st.text_area("Paste stylized here:", "")
if stylized_input:
    st.markdown("**Reverse-Translated:**")
    st.code(reverse_translate(stylized_input), language="text")

