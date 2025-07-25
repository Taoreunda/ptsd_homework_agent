# SQL 실행 가이드

## 📋 실행 순서

다음 순서대로 Supabase SQL Editor에서 실행하세요:

### 1단계: 기본 테이블 생성
**파일**: `create_tables.sql`
- sessions 테이블 (세션 정보)
- messages 테이블 (대화 내용)
- 인덱스 생성
- 연구 분석용 뷰 및 함수

### 2단계: 참가자 테이블 생성  
**파일**: `create_participants.sql`
- participants 테이블 (단순화 버전)
- 관리자 계정 자동 생성 (admin/CHANGE_THIS_PASSWORD)
- 참가자 관리 함수들

**⚠️ 중요**: SQL 실행 전에 `CHANGE_THIS_PASSWORD`를 실제 비밀번호로 변경하세요!

## 🔍 실행 확인 쿼리

SQL 실행 후 다음 쿼리로 확인:

```sql
-- 1. 테이블 생성 확인
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 2. participants 테이블 구조 확인
\d participants

-- 3. 관리자 계정 확인 (비밀번호 설정 후)
SELECT user_id, name, group_type, status 
FROM participants 
WHERE user_id = 'admin';

-- 4. 함수 생성 확인
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_type = 'FUNCTION';
```

## 🎯 기대 결과

### 생성되는 테이블들
- `participants` - 참가자 정보
- `sessions` - 세션 메타데이터  
- `messages` - 대화 내용
- `schema_version` - 스키마 버전 관리

### 생성되는 함수들
- `authenticate_participant()` - 참가자 인증
- `add_participant()` - 참가자 등록
- `update_participant_status()` - 상태 변경
- `get_research_summary()` - 연구 통계

### 생성되는 뷰
- `participant_summary` - 참가자별 통계

## ❗ 문제 해결

### 오류 발생시
```sql
-- 모든 테이블 삭제 후 재시작
DROP TABLE IF EXISTS participants CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS schema_version CASCADE;

-- 그 후 다시 1단계부터 실행
```

### 관리자 계정 재생성
```sql
-- 관리자 계정 비밀번호 설정/변경
UPDATE participants 
SET password = 'YOUR_SECURE_PASSWORD' 
WHERE user_id = 'admin';
```

## ✅ 완료 체크리스트

- [ ] `create_tables.sql` 실행 완료
- [ ] `create_participants.sql` 실행 완료  
- [ ] 테이블 3개 생성 확인 (participants, sessions, messages)
- [ ] 관리자 계정 비밀번호 설정 완료
- [ ] 함수 4개 생성 확인
- [ ] 뷰 1개 생성 확인

모든 체크리스트가 완료되면 Streamlit 앱에서 admin으로 로그인 가능합니다!

## 🔒 보안 주의사항

- SQL 파일의 `CHANGE_THIS_PASSWORD`를 실제 사용할 강력한 비밀번호로 변경 후 실행
- 관리자 비밀번호는 절대 GitHub에 커밋하지 마세요
- 실제 배포 시 환경변수나 별도 설정 파일로 관리 권장