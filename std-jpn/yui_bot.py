import streamlit as st
import requests
import json
from gtts import gTTS
import io
import os
import pandas as pd

st.set_page_config(page_title="Yui Japanese Tutor", page_icon="🌸", layout="wide")

DB_FILE = "jp_vocabulary.csv"

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
    return None


def generate_dialogue(situation):
    prompt = f"""아래 상황에서 일어날 수 있는 자연스러운 일본어 회화 대본을 만들어줘.
상황: {situation}

다음 형식으로 8~10줄의 대화를 작성해.
각 줄 형식: 화자|일본어문장|히라가나읽기|한국어뜻

예시:
A|いらっしゃいませ。|いらっしゃいませ。|어서오세요.
B|すみません、おにぎりはどこですか。|すみません、おにぎりはどこですか。|저기요, 주먹밥은 어디 있나요?
A|あちらです。|あちらです。|저쪽에 있습니다.

규칙:
- 화자는 A와 B만 사용 (A는 직원/상대방, B는 여행자/손님)
- 파이프(|)로 정확히 구분 — 각 줄에 | 기호 정확히 3개
- 자연스럽고 실용적인 표현 위주
- 대화 줄만 출력하고 다른 설명이나 머리말 없음"""

    text = call_gemini(prompt)
    if not text:
        return []
    lines = []
    for raw in text.strip().split('\n'):
        raw = raw.strip()
        parts = raw.split('|')
        if len(parts) == 4:
            lines.append([p.strip() for p in parts])
    return lines


def make_tts_bytes(text):
    tts = gTTS(text=text, lang='ja')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()


# ==========================================
# 사이드바 — 단어장
# ==========================================
with st.sidebar:
    st.title("📝 유이의 단어장")
    st.caption(f"💾 파일: {DB_FILE}")

    if st.session_state.vocab_list:
        for i, word in enumerate(st.session_state.vocab_list):
            st.info(f"{i+1}. {word}")

        df_dl = pd.DataFrame(st.session_state.vocab_list, columns=['word'])
        csv_data = df_dl.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("단어장 추출", data=csv_data, file_name="jp_vocab.csv", mime="text/csv")
    else:
        st.write("아직 저장된 단어가 없어요.")

    if st.button("전체 삭제"):
        st.session_state.vocab_list = []
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.rerun()


# ==========================================
# 메인 화면
# ==========================================
st.title("🌸 유이 선생님의 일본어 교실")

tab1, tab2 = st.tabs(["💬 유이와 자유 대화", "🎧 상황별 회화 듣고 따라하기"])


# ------------------------------------------
# Tab 1: 자유 대화 (기존 기능)
# ------------------------------------------
with tab1:
    mode = st.selectbox(
        "어떤 상황에서 대화할까요?",
        ["일상 대화", "편의점에서", "식당에서 주문하기", "길 찾기"],
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("유이 선생님에게 일본어로 말을 걸어보세요!"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        system_instruction = f"""
너는 친절한 일본어 선생님 '유이'야. 현재 상황: {mode}.
반드시 아래 형식을 정확히 지켜서 답변해줘:
[교정]: (사용자의 일본어가 틀렸다면 자연스럽게 고쳐주고 한국어로 이유 설명)
[대화]: (선생님의 일본어 답변) / (히라가나 읽기) / (한국어 뜻)
[새 단어]: (오늘 대화에서 배울 중요한 일본어 단어 하나. '단어 (발음) : 뜻' 형식으로 작성)
"""

        try:
            ans_text = call_gemini(f"{system_instruction}\n\nUser: {user_input}")

            if ans_text:
                with st.chat_message("assistant"):
                    st.markdown(ans_text)

                    try:
                        if "[대화]:" in ans_text:
                            speech_text = ans_text.split("[대화]:")[1].split("/")[0].strip()
                        else:
                            speech_text = ans_text
                        st.audio(make_tts_bytes(speech_text), format='audio/mp3')
                    except:
                        pass

                    if "[새 단어]:" in ans_text:
                        new_word = ans_text.split("[새 단어]:")[-1].strip().replace("*", "")
                        if new_word and new_word not in st.session_state.vocab_list:
                            st.session_state.vocab_list.append(new_word)
                            save_vocab(st.session_state.vocab_list)
                            st.toast(f"단어 저장 완료: {new_word}")

                st.session_state.messages.append({"role": "assistant", "content": ans_text})
            else:
                st.error("API 에러가 발생했습니다.")

        except Exception as e:
            st.error(f"시스템 에러: {e}")


# ------------------------------------------
# Tab 2: 상황별 회화 듣고 따라하기 (신규)
# ------------------------------------------
with tab2:
    st.subheader("🎧 상황별 회화 듣고 따라하기")
    st.caption("상황을 선택하고 대화를 불러온 뒤, ▶ 버튼으로 듣고 따라 말해보세요!")

    SITUATIONS = [
        "편의점에서",
        "식당에서 주문하기",
        "카페에서 주문하기",
        "길 묻기",
        "전철역에서 티켓 구매",
        "호텔 체크인",
        "쇼핑몰에서 옷 구매",
        "약국에서",
    ]

    selected = st.selectbox("상황 선택", SITUATIONS, key="dialogue_situation_select")

    if st.button("📖 대화 불러오기", type="primary"):
        with st.spinner("대화를 생성하는 중... 잠시만 기다려 주세요."):
            lines = generate_dialogue(selected)

        if lines:
            progress = st.progress(0, text="음성 생성 중...")
            audio_list = []
            for idx, line in enumerate(lines):
                audio_list.append(make_tts_bytes(line[1]))
                progress.progress((idx + 1) / len(lines), text=f"음성 생성 중... ({idx + 1}/{len(lines)})")
            progress.empty()

            st.session_state.dialogue_lines = lines
            st.session_state.dialogue_audio = audio_list
            st.session_state.dialogue_situation = selected
        else:
            st.error("대화 생성에 실패했습니다. 다시 시도해 주세요.")

    if st.session_state.dialogue_lines:
        st.markdown(f"### 📍 {st.session_state.dialogue_situation}")
        st.divider()

        for line, audio_bytes in zip(st.session_state.dialogue_lines, st.session_state.dialogue_audio):
            speaker, japanese, reading, korean = line

            col_icon, col_text, col_audio = st.columns([1, 7, 3])

            with col_icon:
                icon = "🧑" if speaker == "A" else "👩"
                st.markdown(f"<div style='font-size:2rem; text-align:center'>{icon}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center; color:gray; font-size:0.8rem'>{speaker}</div>", unsafe_allow_html=True)

            with col_text:
                st.markdown(f"**{japanese}**")
                st.caption(reading)
                st.caption(f"🇰🇷 {korean}")

            with col_audio:
                st.audio(audio_bytes, format='audio/mp3')

            st.divider()
