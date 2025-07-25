# PTSD 심리치료 대화 지원 에이전트

## 프로젝트 개요
PTSD 심리치료에서 숙제로 대화의 기술이나 정서적인 표현을 돕는 AI 에이전트입니다.
연구용으로 최대 100명의 참가자가 1-7일간 사용할 예정입니다.

## 🚀 최신 업데이트 (2025-01-25)

### ✅ 완료된 주요 개선사항

#### 1. 코드 모듈화 완료 (97,000줄 → 1,311줄, 98.7% 감소)
- **관리자 기능 분리**: `src/admin_pages.py` 생성
  - 참가자 등록, 관리, 통계 대시보드 분리
  - 150줄 → 별도 모듈로 이동하여 가독성 향상
- **UI 스타일링 모듈화**: `src/ui_styles.py` 생성
  - 모바일 최적화, 관리자 페이지, 채팅 인터페이스, 로그인 페이지별 스타일 분리
  - 컨텍스트별 스타일 적용으로 성능 최적화

#### 2. 데이터베이스 아키텍처 전환
- **Firebase → Supabase PostgreSQL** 완전 이전
- **JSON → Database 기반** 참가자 관리
- **세션 연결 풀링** 설정으로 안정성 향상
- **단순화된 스키마** (username 제거, 인구통계학적 정보 추가)

#### 3. 보안 강화
- 기본 관리자 비밀번호 `CHANGE_THIS_PASSWORD`로 변경
- API 키 관리 개선 (`.env` 파일 우선순위 정리)
- 환경변수 하드코딩으로 배포 안정성 확보

## 🏗️ 현재 시스템 아키텍처

### 기술 스택
- **프레임워크**: Streamlit + Chainlit
- **AI 모델**: OpenAI GPT-4.1
- **데이터베이스**: Supabase PostgreSQL
- **메모리 시스템**: LangChain ConversationBufferMemory
- **인증**: PostgreSQL 함수 기반 (`authenticate_participant`)
- **패키지 관리**: UV

### 핵심 파일 구조
```
src/
├── app.py                 # 메인 Streamlit 애플리케이션 (357줄)
├── admin_pages.py         # 관리자 인터페이스 모듈 (220줄)
├── ui_styles.py          # UI 스타일링 모듈 (187줄)
├── database.py           # 데이터베이스 관리 (657줄)
├── config.py             # 환경변수 설정
└── auth.py               # 인증 시스템

sql/
└── create_participants.sql # PostgreSQL 스키마 (222줄)

prompts/
├── therapy_system_prompt.md
└── summary_prompt.md
```

### 데이터베이스 스키마 (단순화 버전 2.0.0)
```sql
participants (
    user_id TEXT PRIMARY KEY,     -- P001, P002, admin
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    group_type TEXT CHECK (group_type IN ('treatment', 'control', 'admin')),
    status TEXT DEFAULT 'active',
    phone TEXT,                   -- 연구자 연락용
    gender TEXT,                  -- 인구통계학적 분석
    age INTEGER,                  -- 성인 연구 대상
    created_at TIMESTAMP DEFAULT NOW()
)
```

## 🐛 발견된 이슈 및 개선 필요사항

### 🚨 Critical Issues
1. **Database Schema Mismatch**: 
   - `database.py:453` - `get_participant_info()` 함수가 존재하지 않는 `username` 컬럼 참조
   - `database.py:525` - `get_participant_stats()`가 없는 `participant_stats` 뷰 참조
   - `database.py:570` - 없는 `get_participant_summary()` 함수 호출

2. **Session Persistence Issues**:
   - 브라우저 새로고침 시 로그인 세션 및 대화 히스토리 손실
   - Streamlit session state 한계로 인한 사용자 경험 저하

### 📋 개선 요청사항
1. ✅ ~~관리자 기능 모듈화~~ (완료)
2. ✅ ~~UI 스타일링 모듈화~~ (완료)
3. 🔄 로그인 세션 지속성 구현
4. 🔄 대화 히스토리 복원 기능
5. 🔄 데이터 구조 버그 수정
6. 🔄 중복 ID 검증 경고 개선
7. 🔄 채팅 폰트 크기 14px 증가
8. 🔄 관리자 인터페이스 버튼 너비 통일
9. 🔄 컨텍스트 요약 시스템 (LLM 메모리 관리)
10. 🔄 로깅 시스템 개선

## 🎯 향후 개발 계획

### Phase 1: 긴급 버그 수정
- [ ] Database schema와 코드 간 불일치 해결
- [ ] 관리자 통계 대시보드 정상 작동
- [ ] 중복 ID 검증 개선

### Phase 2: 사용자 경험 개선  
- [ ] LangChain 기반 세션 지속성 (LangGraph 없이)
- [ ] PostgreSQL 백엔드 대화 히스토리 저장
- [ ] 브라우저 새로고침 후 자동 복원

### Phase 3: UI/UX 폴리싱
- [ ] 채팅 인터페이스 폰트 크기 조정
- [ ] 반응형 디자인 개선
- [ ] 에러 메시지 및 사용자 피드백 향상

### Phase 4: 연구 기능 강화
- [ ] 대화 품질 분석 도구
- [ ] 자동 리포트 생성
- [ ] 중도포기 예측 모델

## 🔧 개발 환경 설정

### 필수 환경변수 (.env)
```bash
DATABASE_URL=postgresql://username:password@host:port/database
OPENAI_API_KEY=your_openai_api_key
```

### 실행 방법
```bash
# 의존성 설치
uv sync

# 데이터베이스 스키마 설정
psql -f sql/create_participants.sql

# 애플리케이션 실행
uv run streamlit run streamlit_app.py
```

## 📊 연구 데이터 분석 계획

### 수집 데이터
- **세션 데이터**: 시작/종료 시간, 총 메시지 수, 응답 시간
- **메시지 데이터**: 역할(user/assistant), 내용, 길이, 타임스탬프
- **참가자 데이터**: 그룹(treatment/control), 인구통계학적 정보, 참여 상태

### 분석 지표
- **참여도**: 세션 빈도, 지속 시간, 메시지 교환 수
- **대화 품질**: 메시지 길이, 감정 표현, 개방성
- **치료적 진전**: 감정 변화, 자기 성찰, 문제 해결 언급

## 🔒 보안 및 프라이버시

- ✅ API 키 환경변수 관리
- ✅ 사용자 대화 데이터 PostgreSQL 암호화 저장
- ✅ 참가자 익명성 보장 (ID 기반 시스템)
- ✅ 로그에 민감한 정보 출력 방지
- ⚠️ 기본 관리자 비밀번호 변경 필요

## 📝 개발 가이드라인

### 코드 스타일
- **주석**: 모든 주석은 한글로 작성
- **함수명/변수명**: 영어 사용, snake_case 일관성 유지
- **타입 힌트**: Python 타입 힌트 필수 사용
- **문서화**: 중요한 함수는 docstring으로 설명

### 커밋 메시지 규칙
- `feat:` 새로운 기능 추가
- `fix:` 버그 수정
- `refactor:` 코드 리팩토링
- `docs:` 문서 업데이트
- `style:` 코드 스타일 변경

## 🤝 기여 가이드

1. 이슈 생성 또는 기존 이슈 확인
2. 기능 브랜치 생성 (`feature/기능명`)
3. 개발 및 테스트
4. Pull Request 생성
5. 코드 리뷰 후 병합

## 📞 연락처

- **연구 책임자**: [연구자 정보]
- **개발팀**: [개발팀 연락처]
- **기술 지원**: GitHub Issues 활용

---

**마지막 업데이트**: 2025-01-25  
**버전**: 2.0.0 (단순화 완료)  
**상태**: 개발 진행 중 (버그 수정 단계)