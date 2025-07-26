# PTSD 심리치료 대화 지원 에이전트

## 프로젝트 개요
PTSD 심리치료에서 숙제로 대화의 기술이나 정서적인 표현을 돕는 AI 에이전트입니다.
연구용으로 최대 100명의 참가자가 1-7일간 사용할 예정입니다.

## 🚀 최신 업데이트 (2025-01-26)

### ✅ 완료된 주요 개선사항

#### 1. 데이터베이스 구조 대폭 단순화 및 완전 통합
- **필수 스키마 완성**: `essential_schema.sql`로 단순화된 3테이블 구조 완성
  - 제거: 복잡한 다중 테이블 및 뷰 구조
  - 완성: `participants`, `sessions` (토큰 통합), `messages` (통합 메시지)
- **완전한 CRUD 함수**: 관리자 인터페이스용 15개 필수 함수 구현
  - 참가자 관리: `get_participant_info`, `update_participant`, `delete_participant`
  - 통계 및 목록: `get_all_participants`, `get_research_summary`
  - 세션 지속성: `get_or_create_session_with_token`

#### 2. 세션 지속성 및 중복 문제 해결
- **중복 UI 로딩 해결**: 대화 기록이 두 번 표시되던 문제 완전 수정
- **중복 로그 제거**: "토큰 인증 성공" 로그가 여러 번 출력되던 문제 해결
- **중복 메시지 저장 해결**: DB에 메시지가 두 번 저장되던 치명적 버그 수정
- **세션 지속성 구현**: 브라우저 새로고침 후 대화 내용 자동 복원
- **응답 시간 정확 저장**: 사용자/AI 응답 시간이 정확히 DB에 기록

#### 3. 통합 참가자 CRUD 인터페이스 완성
- **단일 폼 기반 관리**: 로드/등록/수정/삭제를 하나의 직관적 인터페이스로 통합
- **비밀번호 관리**: 관리자용 비밀번호 표시 및 수정 기능
- **스트리밍 위젯 충돌 해결**: Streamlit 폼 위젯 상태 충돌 문제 완전 해결
- **재설정 기능**: 폼 초기화 버튼으로 새 작업 시작

#### 4. 코드 통합 및 중복 제거
- **세션 매니저 통합**: `session_manager.py`와 `simple_session_manager.py` 통합
- **DatabaseMixin 패턴**: 데이터베이스 연결 관리 일원화
- **성능 최적화**: 중복 인증 호출 제거 및 효율적인 세션 관리

## 🏗️ 현재 시스템 아키텍처

### 단순화된 기술 스택
- **프레임워크**: Streamlit (Chainlit 제거)
- **AI 모델**: OpenAI GPT-4.1  
- **데이터베이스**: Supabase PostgreSQL (단순화된 3개 테이블)
- **메모리 시스템**: LangChain ConversationBufferMemory (단순화)
- **세션 관리**: Token 기반 (`simple_session_manager.py`)
- **인증**: PostgreSQL 함수 기반
- **패키지 관리**: UV

### 단순화된 파일 구조
```
src/
├── streamlit_app.py           # 메인 애플리케이션 (세션 지속성 구현)
├── admin_pages.py             # 통합 관리자 CRUD 인터페이스 (완성)
├── session_manager.py         # 통합 세션 관리 (중복 제거 완료)
├── database.py                # 데이터베이스 관리 (DatabaseMixin 패턴)
└── ui_styles.py              # UI 스타일링

sql/
├── essential_schema.sql       # 필수 3테이블 스키마 (15개 함수 포함)
├── cleanup_database.sql       # 데이터베이스 정리 스크립트
└── remove_duplicate_messages.sql # 중복 메시지 제거 스크립트

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

## 🎯 현재 개발 상태

### ✅ 해결 완료된 Critical Issues
1. **Database Schema 완전 통합**: 
   - ✅ `essential_schema.sql`로 통합 완료
   - ✅ 필요한 15개 함수 모두 구현
   - ✅ `database.py`와 스키마 불일치 문제 해결

2. **Session Persistence 완전 구현**:
   - ✅ 브라우저 새로고침 후 자동 로그인 및 대화 복원
   - ✅ URL 기반 토큰 세션 관리
   - ✅ PostgreSQL 백엔드 대화 히스토리 저장

3. **중복 데이터 문제 완전 해결**:
   - ✅ 중복 UI 로딩 문제 수정
   - ✅ 중복 인증 로그 제거
   - ✅ 중복 메시지 저장 방지 및 정리 스크립트 제공

### 📋 개선 요청사항 진행 상황
1. ✅ ~~관리자 기능 모듈화~~ (완료)
2. ✅ ~~UI 스타일링 모듈화~~ (완료)
3. ✅ ~~로그인 세션 지속성 구현~~ (완료)
4. ✅ ~~대화 히스토리 복원 기능~~ (완료)
5. ✅ ~~데이터 구조 버그 수정~~ (완료)
6. ✅ ~~중복 코드 제거 및 통합~~ (완료)
7. 🔄 채팅 폰트 크기 14px 증가
8. 🔄 관리자 인터페이스 버튼 너비 통일  
9. 🔄 컨텍스트 요약 시스템 (LLM 메모리 관리)
10. 🔄 로깅 시스템 개선

## 🎯 향후 개발 계획

### Phase 1: UI/UX 폴리싱 (현재)
- [ ] 채팅 인터페이스 폰트 크기 조정 (14px)
- [ ] 관리자 인터페이스 버튼 너비 통일
- [ ] 반응형 디자인 개선
- [ ] 에러 메시지 및 사용자 피드백 향상

### Phase 2: 고급 기능 구현
- [ ] 컨텍스트 요약 시스템 (장기 대화 메모리 관리)
- [ ] 로깅 시스템 개선 (구조화된 로그)
- [ ] 성능 모니터링 대시보드

### Phase 3: 연구 기능 강화
- [ ] 대화 품질 분석 도구
- [ ] 자동 리포트 생성
- [ ] 중도포기 예측 모델
- [ ] 참가자 engagement 분석

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

# 데이터베이스 스키마 설정 (필수)
psql $DATABASE_URL -f sql/essential_schema.sql

# 기존 중복 메시지 정리 (선택사항)
psql $DATABASE_URL -f sql/remove_duplicate_messages.sql

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

**마지막 업데이트**: 2025-01-26  
**버전**: 2.1.0 (핵심 기능 완성)  
**상태**: 안정화 단계 (UI/UX 개선 진행 중)