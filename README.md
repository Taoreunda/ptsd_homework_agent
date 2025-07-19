# PTSD 심리치료 대화 지원 에이전트

PTSD 환자의 심리치료에서 대화 기술과 정서 표현을 돕는 연구용 AI 챗봇입니다.

## 🚀 빠른 시작

### 1. 설치
```bash
git clone <repository-url>
cd ptsd_homework_agent
uv sync
```

### 2. 환경설정
```bash
cp .env.example .env
# .env 파일에서 OpenAI API 키 설정
```

### 3. 실행
```bash
# 로컬 실행
uv run streamlit run streamlit_app.py

# 모바일 포함 (네트워크 접속 허용)
uv run streamlit run streamlit_app.py --server.address 0.0.0.0
```

접속: http://localhost:8501

## ⚙️ 설정

### 환경변수 (.env)
```env
OPENAI_API_KEY="your_api_key_here"
OPENAI_MODEL_NAME="gpt-4o-mini"
THERAPY_SYSTEM_PROMPT_PATH="prompts/therapy_system_prompt.md"
PARTICIPANTS_JSON_PATH="data/participants.json"
```

### 참가자 등록 (data/participants.json)
```json
{
  "participants": {
    "P001": {
      "username": "test_user",
      "password": "test_pass",
      "name": "테스트 사용자",
      "group": "treatment",
      "status": "active"
    }
  }
}
```

## 📱 기능

- **AI 대화**: OpenAI GPT-4o-mini 기반 치료 대화
- **참가자 인증**: JSON 기반 사전 등록 시스템  
- **세션 관리**: 대화 기록 및 메모리 유지
- **모바일 최적화**: 스마트폰 친화적 UI
- **테마 적용**: 심리치료에 적합한 색상

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **AI Model**: OpenAI GPT-4o-mini
- **Memory**: LangChain ConversationBufferMemory
- **Package**: UV

## 📁 구조

```
ptsd_homework_agent/
├── streamlit_app.py         # 메인 애플리케이션
├── .streamlit/config.toml   # 테마 설정
├── data/participants.json   # 참가자 데이터
├── prompts/                 # AI 프롬프트
├── utils/                   # 유틸리티
└── .env                     # 환경변수
```

## 📋 요구사항

- Python 3.11+
- UV 패키지 매니저
- OpenAI API 키

## 🚀 Streamlit Community Cloud 배포

### 1. 배포 준비
```bash
# 의존성 확인
cat requirements.txt

# 환경변수 템플릿 확인  
cat .streamlit/secrets.toml
```

### 2. Streamlit Cloud에서 앱 생성
1. [Streamlit Community Cloud](https://share.streamlit.io)에 로그인
2. "New app" 클릭
3. GitHub 저장소 연결: `https://github.com/Taoreunda/ptsd_homework_agent`
4. Main file path: `streamlit_app.py`
5. Advanced settings > Python version: 3.11

### 3. 환경변수 설정
**App Settings > Secrets**에서 다음 설정:
```toml
OPENAI_API_KEY = "sk-your_actual_api_key_here"
OPENAI_MODEL_NAME = "gpt-4o-mini"
THERAPY_SYSTEM_PROMPT_PATH = "prompts/therapy_system_prompt.md"
PARTICIPANTS_JSON_PATH = "data/participants.json"
LOG_LEVEL = "INFO"
```

### 4. 배포 완료
- Deploy 버튼 클릭
- 빌드 로그 확인
- 앱 URL 확인 (예: `https://your-app-name.streamlit.app`)

## ⚠️ 주의사항

- **연구 목적**: 실제 치료를 대체하지 않습니다
- **데이터 보안**: 참가자 정보 보호 필수
- **윤리 준수**: 연구 윤리 위원회 승인 필요
- **API 비용**: OpenAI API 사용량 모니터링 필요

## 🔧 개발

### 로그 확인
```bash
tail -f logs/*.log
```

### 설정 변경
- 테마: `.streamlit/config.toml`
- 프롬프트: `prompts/therapy_system_prompt.md`
- 참가자: `data/participants.json`
- 배포 환경변수: `.streamlit/secrets.toml` (템플릿)