# 영어·일본어 학습 앱 (Streamlit)

| 앱 | 메인 파일 |
|---|---|
| Liam 영어 튜터 | `std-eng/liam_bot.py` |
| Yui 일본어 튜터 | `std-jpn/yui_bot.py` |

API 키는 코드에 없습니다. `GEMINI_API_KEY`를 Streamlit Secrets(배포) 또는 환경변수(로컬)로 넣어야 동작합니다.

## 배포 순서 (스마트폰에서 쓰기)

1. **새 Gemini API 키 발급** — https://aistudio.google.com/apikey (기존 키는 파일에 평문으로 남아 있었으니 폐기 권장)
2. **GitHub에 비공개(Private) 저장소 생성** 후 이 폴더 내용을 올린다.
3. https://share.streamlit.io 에 GitHub로 로그인 → `Create app`
   - Repository: 위 저장소 / Branch: `main`
   - Main file path: `std-eng/liam_bot.py` (일본어 앱은 `std-jpn/yui_bot.py`로 한 번 더 생성)
   - `Advanced settings` → `Secrets` 에 다음을 붙여넣기:
     ```
     GEMINI_API_KEY = "새로_발급한_키"
     ```
4. `Deploy` 후 생성된 `https://....streamlit.app` 주소를 스마트폰 브라우저에서 열고, 홈 화면에 추가하면 앱처럼 쓸 수 있다.
   - 비공개 저장소의 앱은 기본적으로 로그인한 본인만 볼 수 있다. (Share 설정에서 변경 가능)

## 로컬 테스트

```
set GEMINI_API_KEY=새로_발급한_키
py -m streamlit run std-eng/liam_bot.py
```

## 주의

- 단어장 CSV(`*_vocabulary.csv`)는 클라우드에서 앱이 잠들거나 재시작되면 사라진다. 사이드바의 **Download CSV / 단어장 추출** 버튼으로 가끔 백업할 것.
- `.streamlit/secrets.toml`, `.env` 등 키 파일은 `.gitignore`로 제외되어 있다. 키를 코드에 직접 쓰지 말 것.
