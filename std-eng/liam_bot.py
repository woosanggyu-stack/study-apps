import streamlit as st
import requests
import json
from gtts import gTTS
import io
import os
import pandas as pd

st.set_page_config(page_title="Liam English Tutor", page_icon="🇺🇸", layout="wide")

DB_FILE = "my_vocabulary.csv"

def load_vocab():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            return df['word'].dropna().unique().tolist()
        except:
            return []
    return []

def save_vocab(word_list):
    df = pd.DataFrame(word_list, columns=['word'])
    df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = load_vocab()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "dialogue_lines" not in st.session_state:
    st.session_state.dialogue_lines = []
if "dialogue_audio" not in st.session_state:
    st.session_state.dialogue_audio = []
if "dialogue_situation" not in st.session_state:
    st.session_state.dialogue_situation = ""

def _get_api_key():
    """Streamlit Secrets(배포) 또는 환경변수(로컬)에서 Gemini API 키를 읽는다. 코드에 키를 적지 않는다."""
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.environ.get("GEMINI_API_KEY", "")


MY_API_KEY = _get_api_key()
if not MY_API_KEY:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다. Streamlit Cloud의 Settings → Secrets에 등록하세요.")
    st.stop()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={MY_API_KEY}"
HEADERS = {'Content-Type': 'application/json'}


def call_gemini(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(GEMINI_URL, headers=HEADERS, data=json.dumps(payload).encode('utf-8'))
    result = resp.json()
    if 'candidates' in result:
        return result['candidates'][0]['content']['parts'][0]['text']
    err = result.get('error', result) if isinstance(result, dict) else result
    msg = err.get('message', err) if isinstance(err, dict) else err
    st.session_state['last_api_error'] = f"HTTP {resp.status_code}: {str(msg)[:300]}"
    return None


def generate_dialogue(situation):
    prompt = f"""Create a natural English conversation script for the following situation.
Situation: {situation}

Write 8 to 10 lines of dialogue in exactly this format:
Speaker|English sentence|Korean translation

Example:
A|Welcome! What can I get for you today?|어서오세요! 무엇을 드릴까요?
B|Hi, I'd like a medium latte, please.|안녕하세요, 미디엄 라떼 한 잔 주세요.
A|Sure! Would you like that hot or iced?|네! 따뜻하게 드릴까요, 아이스로 드릴까요?

Rules:
- Use only A and B as speakers (A = staff/other person, B = learner/customer/visitor)
- Separate fields with exactly one pipe (|) — each line must have exactly 2 pipe characters
- Use natural, practical everyday expressions
- Output dialogue lines only — no headings, explanations, or extra text"""

    text = call_gemini(prompt)
    if not text:
        return []
    lines = []
    for raw in text.strip().split('\n'):
        raw = raw.strip()
        parts = raw.split('|')
        if len(parts) == 3:
            lines.append([p.strip() for p in parts])
    return lines


def make_tts_bytes(text):
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()


# ==========================================
# 사이드바 — 단어장
# ==========================================
with st.sidebar:
    st.title("📝 My Vocabulary")
    st.caption(f"저장된 파일: {DB_FILE}")

    if st.session_state.vocab_list:
        for i, word in enumerate(st.session_state.vocab_list):
            st.info(f"{i+1}. {word}")

        df_dl = pd.DataFrame(st.session_state.vocab_list, columns=['word'])
        csv_data = df_dl.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("Download CSV", data=csv_data, file_name="my_words.csv", mime="text/csv")
    else:
        st.write("No words saved yet.")

    if st.button("Clear All Vocabulary"):
        st.session_state.vocab_list = []
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.rerun()


# ==========================================
# 메인 화면
# ==========================================
st.title("🇺🇸 Liam's English Class")

tab1, tab2 = st.tabs(["💬 Free Chat with Liam", "🎧 Situational Dialogue Practice"])


# ------------------------------------------
# Tab 1: 자유 대화 (기존 기능)
# ------------------------------------------
with tab1:
    mode = st.selectbox(
        "Choose a Situation:",
        ["Daily Conversation", "Job Interview", "In a Coffee Shop", "At the Airport"],
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("Talk to Liam..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        system_instruction = f"""
You are Liam, a friendly American English tutor. Current setting: {mode}.
Always structure your response exactly like this:
[Correction]: (Correct the user's grammar if needed, if not, say 'Great!')
[Dialogue]: (Your natural response in English)
[New Word]: (One essential English word or idiom from this chat)
"""

        try:
            ans_text = call_gemini(f"{system_instruction}\n\nUser: {user_input}")

            if ans_text:
                with st.chat_message("assistant"):
                    st.markdown(ans_text)

                    try:
                        if "[Dialogue]:" in ans_text:
                            speech_text = ans_text.split("[Dialogue]:")[1].split("[New Word]")[0].strip()
                        else:
                            speech_text = ans_text
                        st.audio(make_tts_bytes(speech_text), format='audio/mp3')
                    except:
                        pass

                    if "[New Word]:" in ans_text:
                        new_word = ans_text.split("[New Word]:")[-1].strip().replace(".", "").replace("*", "")
                        if new_word and new_word not in st.session_state.vocab_list:
                            st.session_state.vocab_list.append(new_word)
                            save_vocab(st.session_state.vocab_list)
                            st.toast(f"Saved to vocab: {new_word}")

                st.session_state.messages.append({"role": "assistant", "content": ans_text})
            else:
                st.error(f"API Error: Check your API Key or Model Name. ({st.session_state.get('last_api_error', '')})")

        except Exception as e:
            st.error(f"System Error: {e}")


# ------------------------------------------
# Tab 2: 상황별 회화 듣고 따라하기 (신규)
# ------------------------------------------
with tab2:
    st.subheader("🎧 Situational Dialogue Practice")
    st.caption("Choose a situation, load the dialogue, then press ▶ to listen and repeat each line!")

    SITUATIONS = [
        "At a Coffee Shop",
        "At a Restaurant",
        "At the Airport (Check-in)",
        "At a Hotel (Check-in)",
        "Job Interview",
        "Shopping at a Store",
        "At the Doctor's Office",
        "Making a Phone Call",
    ]

    selected = st.selectbox("Choose a Situation:", SITUATIONS, key="dialogue_situation_select")

    if st.button("📖 Load Dialogue", type="primary"):
        with st.spinner("Generating dialogue... Please wait."):
            lines = generate_dialogue(selected)

        if lines:
            progress = st.progress(0, text="Generating audio...")
            audio_list = []
            for idx, line in enumerate(lines):
                audio_list.append(make_tts_bytes(line[1]))
                progress.progress((idx + 1) / len(lines), text=f"Generating audio... ({idx + 1}/{len(lines)})")
            progress.empty()

            st.session_state.dialogue_lines = lines
            st.session_state.dialogue_audio = audio_list
            st.session_state.dialogue_situation = selected
        else:
            st.error(f"Failed to generate dialogue. Please try again. ({st.session_state.get('last_api_error', '')})")

    if st.session_state.dialogue_lines:
        st.markdown(f"### 📍 {st.session_state.dialogue_situation}")
        st.divider()

        for line, audio_bytes in zip(st.session_state.dialogue_lines, st.session_state.dialogue_audio):
            speaker, english, korean = line

            col_icon, col_text, col_audio = st.columns([1, 7, 3])

            with col_icon:
                icon = "🧑" if speaker == "A" else "👩"
                st.markdown(f"<div style='font-size:2rem; text-align:center'>{icon}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center; color:gray; font-size:0.8rem'>{speaker}</div>", unsafe_allow_html=True)

            with col_text:
                st.markdown(f"**{english}**")
                st.caption(f"🇰🇷 {korean}")

            with col_audio:
                st.audio(audio_bytes, format='audio/mp3')

            st.divider()
