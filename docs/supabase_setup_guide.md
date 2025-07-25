# Supabase 설정 가이드 - PTSD 심리치료 연구용

## 1. Supabase 계정 생성 및 프로젝트 설정

### 1.1 계정 생성
1. [Supabase 공식 사이트](https://supabase.com) 방문
2. "Start your project" 클릭하여 회원가입
3. GitHub, Google 계정으로 간편 가입 가능

### 1.2 새 프로젝트 생성
1. 대시보드에서 "New Project" 클릭
2. 프로젝트 설정:
   - **Organization**: 기본값 사용
   - **Name**: `ptsd-chat-research`
   - **Database Password**: 강력한 비밀번호 설정 (반드시 기록해두세요!)
   - **Region**: `Asia Northeast (Seoul)` 선택
3. "Create new project" 클릭 (1-2분 소요)

## 2. 데이터베이스 연결 정보 확인

### 2.1 연결 정보 찾는 방법 (2가지)

#### 방법 1: Connect 버튼 사용 (추천)
1. Supabase 대시보드에서 프로젝트 선택
2. **"Connect" 버튼** 클릭 (대시보드 상단)
3. 팝업에서 **"Database connection string"** 찾기

#### 방법 2: Settings 메뉴 사용
1. 프로젝트 대시보드 → **Settings** → **Database**
2. **"Connection Info"** 섹션에서 연결 정보 확인:
   - **Host**: `db.[your-project-id].supabase.co`
   - **Database**: `postgres`
   - **Port**: `5432`
   - **User**: `postgres`
   - **Password**: 생성시 설정한 비밀번호

### 2.2 연결 문자열 형식
```
postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres
```

**실제 예시**:
```
postgresql://postgres:MySecurePassword123@db.abcdefghijk.supabase.co:5432/postgres
```

### 2.3 중요 참고사항
- Supabase는 **IPv6를 기본**으로 사용합니다
- IPv4 연결이 필요한 경우 **Session Pooler** 또는 **Transaction Pooler** 사용
- 연결 문자열에서 비밀번호는 URL 인코딩이 필요할 수 있습니다

## 3. 데이터베이스 테이블 생성

### 3.1 SQL Editor 접근
1. Supabase 대시보드 → SQL Editor
2. "New query" 클릭

### 3.2 테이블 생성 SQL 실행
다음 SQL을 복사하여 실행:

```sql
-- 세션 정보 테이블
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 메시지 상세 테이블
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    message_length INTEGER,
    response_time_seconds FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_start_time ON sessions(start_time);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
```

### 3.3 테이블 생성 확인
1. SQL Editor에서 위 쿼리 실행
2. Table Editor에서 `sessions`, `messages` 테이블 확인

## 4. 환경 변수 설정

### 4.1 프로젝트 API 키 확인
1. Supabase 대시보드 → Settings → API
2. 다음 정보 복사:
   - **Project URL**: `https://[your-project-id].supabase.co`
   - **anon public key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### 4.2 .env 파일 설정
프로젝트 루트의 `.env` 파일에 추가:

```env
# Supabase 설정
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_anon_public_key_here
DATABASE_URL=postgresql://postgres:your_password@your-project-id.supabase.co:5432/postgres

# 기존 설정은 그대로 유지
OPENAI_API_KEY=your_openai_key
PARTICIPANTS_JSON_PATH=data/participants.json
THERAPY_SYSTEM_PROMPT_PATH=prompts/therapy_system_prompt.md
```

## 5. Python 패키지 설치

### 5.1 필수 패키지
`requirements.txt`에 다음 추가:
```
psycopg2-binary
langchain-postgres
```

### 5.2 설치 명령
```bash
uv add psycopg2-binary langchain-postgres
```

## 6. 연결 테스트

### 6.1 기본 연결 테스트
```python
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    print("✅ Supabase 연결 성공!")
    
    # 테이블 존재 확인
    cursor = conn.cursor()
    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
    tables = cursor.fetchall()
    print(f"📋 생성된 테이블: {[table[0] for table in tables]}")
    
    conn.close()
except Exception as e:
    print(f"❌ 연결 실패: {e}")
```

### 6.2 데이터 삽입 테스트
```python
import uuid
from datetime import datetime

# 테스트 세션 생성
session_id = str(uuid.uuid4())
user_id = "test_user"

cursor.execute("""
    INSERT INTO sessions (session_id, user_id, start_time, session_count)
    VALUES (%s, %s, %s, %s)
""", (session_id, user_id, datetime.now(), 1))

# 테스트 메시지 저장
cursor.execute("""
    INSERT INTO messages (session_id, role, content, message_length)
    VALUES (%s, %s, %s, %s)
""", (session_id, "user", "안녕하세요!", 5))

conn.commit()
print("✅ 테스트 데이터 저장 성공!")
```

## 7. 데이터 확인 및 관리

### 7.1 Table Editor 사용
1. Supabase 대시보드 → Table Editor
2. `sessions`, `messages` 테이블 선택
3. 실시간 데이터 확인 가능

### 7.2 연구 데이터 내보내기
```sql
-- 모든 세션 데이터 조회
SELECT * FROM sessions ORDER BY start_time DESC;

-- 특정 사용자의 대화 내역
SELECT s.user_id, s.start_time, m.role, m.content, m.timestamp
FROM sessions s
JOIN messages m ON s.session_id = m.session_id
WHERE s.user_id = 'user_123'
ORDER BY m.timestamp;

-- CSV 내보내기 (Table Editor에서 Export 버튼 사용)
```

## 8. 보안 설정 (선택사항)

### 8.1 Row Level Security (RLS) 설정
연구 데이터 보호를 위해:

```sql
-- RLS 활성화
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- 기본 정책 (모든 접근 허용 - 연구용)
CREATE POLICY "Allow all access" ON sessions FOR ALL USING (true);
CREATE POLICY "Allow all access" ON messages FOR ALL USING (true);
```

## 9. 문제 해결

### 9.1 일반적인 오류
- **연결 실패**: DATABASE_URL 형식 확인
- **테이블 없음**: SQL Editor에서 테이블 생성 쿼리 재실행
- **권한 오류**: Supabase 프로젝트 설정에서 API 키 확인

### 9.2 성능 최적화
- 많은 데이터 누적시 인덱스 추가
- 주기적 백업 설정
- 쿼리 성능 모니터링

## 10. 참가자 데이터 마이그레이션

### 10.1 JSON → DB 마이그레이션 실행
```bash
# 1. 테이블 생성 후 마이그레이션 스크립트 실행
python scripts/migrate_participants.py

# 2. 마이그레이션 결과 확인
# - 성공/실패 개수 표시
# - 자동 백업 파일 생성
```

### 10.2 마이그레이션 검증
Supabase Table Editor에서 확인:
1. **participants** 테이블: 모든 사용자 데이터 확인
2. **sessions** 테이블: 세션 데이터 자동 생성 확인
3. **messages** 테이블: 대화 데이터 저장 확인

## 11. 연구 종료 후 데이터 처리

### 11.1 데이터 백업
1. Table Editor → Export to CSV
2. SQL 덤프 생성:
   ```bash
   pg_dump $DATABASE_URL > research_backup.sql
   ```

### 11.2 데이터 분석 준비
- CSV 파일을 Python pandas로 로드
- 시간대별, 사용자별 분석 수행
- 드랍아웃 패턴 분석 코드 실행

### 11.3 연구 통계 조회
```sql
-- 전체 참가자 요약
SELECT * FROM get_participant_summary();

-- 참가자별 상세 통계
SELECT * FROM participant_stats ORDER BY user_id;

-- 드랍아웃 위험도 계산
SELECT user_id, calculate_dropout_risk(user_id) as risk_score
FROM participants WHERE group_type IN ('treatment', 'control');
```

---

**⚠️ 중요 사항**
- DATABASE_URL과 API 키는 절대 공개하지 마세요
- 연구 데이터는 IRB 승인에 따라 관리하세요
- Supabase 무료 티어는 500MB 제한이 있습니다
- 백업을 정기적으로 수행하세요