-- PTSD 심리치료 연구용 필수 스키마
-- 단순화된 3테이블 구조로 최소한의 기능만 제공

-- ==============================================
-- 0. 필수 확장 기능 활성화
-- ==============================================

-- UUID 생성을 위한 확장 (gen_random_uuid 사용)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================
-- 1. 참가자 테이블 (핵심)
-- ==============================================

CREATE TABLE participants (
    user_id TEXT PRIMARY KEY,                    -- 참가자 ID (P001, admin 등)
    password TEXT NOT NULL,                      -- 비밀번호 (해시되지 않음, 연구용)
    name TEXT NOT NULL,                          -- 참가자명
    group_type TEXT NOT NULL CHECK (group_type IN ('treatment', 'control', 'admin')), -- 연구 그룹
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'completed', 'dropout')), -- 참가 상태
    phone TEXT,                                  -- 전화번호 (SMS용)
    gender TEXT CHECK (gender IN ('남성', '여성', '기타')), -- 성별
    age INTEGER CHECK (age >= 18 AND age <= 100), -- 나이
    created_at TIMESTAMP DEFAULT NOW(),          -- 등록일시
    updated_at TIMESTAMP DEFAULT NOW()           -- 수정일시
);

-- 기본 관리자 계정 생성
INSERT INTO participants (user_id, password, name, group_type, status)
VALUES ('admin', 'CHANGE_THIS_PASSWORD', '관리자', 'admin', 'active')
ON CONFLICT (user_id) DO NOTHING;

-- ==============================================
-- 2. 세션 테이블 (토큰 기능 통합)
-- ==============================================

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,                 -- 세션 ID (UUID)
    user_id TEXT NOT NULL REFERENCES participants(user_id) ON DELETE CASCADE, -- 참가자 ID
    session_token UUID UNIQUE DEFAULT gen_random_uuid(), -- 브라우저 새로고침 대응 토큰
    start_time TIMESTAMP DEFAULT NOW(),          -- 세션 시작 시간
    end_time TIMESTAMP,                          -- 세션 종료 시간 (NULL=진행중)
    last_accessed TIMESTAMP DEFAULT NOW(),       -- 마지막 접근 시간
    total_messages INTEGER DEFAULT 0,            -- 세션 메시지 수
    session_count INTEGER DEFAULT 1,             -- 사용자 누적 세션 수
    is_active BOOLEAN DEFAULT TRUE,              -- 세션 활성 상태
    created_at TIMESTAMP DEFAULT NOW()           -- 생성일시
);

-- ==============================================
-- 3. 메시지 테이블 (모든 대화 통합)
-- ==============================================

CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 메시지 ID
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE, -- 세션 ID
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')), -- 발신자
    content TEXT NOT NULL,                        -- 메시지 내용
    timestamp TIMESTAMP DEFAULT NOW(),            -- 전송 시간
    message_order INTEGER NOT NULL,               -- 세션 내 순서
    message_length INTEGER,                       -- 글자 수 (자동 계산)
    response_time_seconds FLOAT,                  -- 응답 시간 (초)
    metadata JSONB DEFAULT '{}',                  -- 추가 정보
    created_at TIMESTAMP DEFAULT NOW()            -- 생성일시
);

-- ==============================================
-- 4. 성능 최적화 인덱스
-- ==============================================

-- 참가자 테이블 인덱스
CREATE INDEX idx_participants_group ON participants(group_type);
CREATE INDEX idx_participants_status ON participants(status);

-- 세션 테이블 인덱스
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_sessions_active ON sessions(is_active, last_accessed);
CREATE INDEX idx_sessions_start_time ON sessions(start_time DESC);

-- 메시지 테이블 인덱스
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_order ON messages(session_id, message_order);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_messages_role ON messages(role);

-- ==============================================
-- 5. 자동 계산 트리거 함수들
-- ==============================================

-- 메시지 길이 자동 계산
CREATE OR REPLACE FUNCTION calculate_message_length()
RETURNS TRIGGER AS $$
BEGIN
    NEW.message_length := LENGTH(NEW.content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 메시지 순서 자동 설정
CREATE OR REPLACE FUNCTION set_message_order()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.message_order IS NULL THEN
        SELECT COALESCE(MAX(message_order), 0) + 1 
        INTO NEW.message_order
        FROM messages 
        WHERE session_id = NEW.session_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 세션 메시지 수 자동 업데이트
CREATE OR REPLACE FUNCTION update_session_message_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE sessions 
        SET total_messages = total_messages + 1,
            last_accessed = NOW()
        WHERE session_id = NEW.session_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE sessions 
        SET total_messages = GREATEST(total_messages - 1, 0)
        WHERE session_id = OLD.session_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 참가자 수정 시간 자동 업데이트
CREATE OR REPLACE FUNCTION update_participant_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==============================================
-- 6. 트리거 생성
-- ==============================================

-- 메시지 길이 자동 계산
CREATE TRIGGER trigger_calculate_message_length
    BEFORE INSERT OR UPDATE ON messages
    FOR EACH ROW
    EXECUTE FUNCTION calculate_message_length();

-- 메시지 순서 자동 설정
CREATE TRIGGER trigger_set_message_order
    BEFORE INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION set_message_order();

-- 세션 메시지 수 자동 업데이트
CREATE TRIGGER trigger_update_message_count
    AFTER INSERT OR DELETE ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_message_count();

-- 참가자 수정 시간 자동 업데이트
CREATE TRIGGER trigger_update_participant_timestamp
    BEFORE UPDATE ON participants
    FOR EACH ROW
    EXECUTE FUNCTION update_participant_timestamp();

-- ==============================================
-- 7. 필수 관리 함수들
-- ==============================================

-- 기존 활성 세션 조회 또는 새 세션 생성 (토큰 포함)
CREATE OR REPLACE FUNCTION get_or_create_session_with_token(input_user_id TEXT)
RETURNS TABLE(session_id TEXT, session_token UUID, is_new_session BOOLEAN) AS $$
DECLARE
    existing_session_id TEXT;
    existing_token UUID;
    new_session_id TEXT;
    new_token UUID;
    session_count_val INTEGER;
BEGIN
    -- 기존 활성 세션 확인 (최근 접근한 세션)
    SELECT s.session_id, s.session_token
    INTO existing_session_id, existing_token
    FROM sessions s
    WHERE s.user_id = input_user_id 
    AND s.is_active = TRUE
    ORDER BY s.last_accessed DESC
    LIMIT 1;
    
    -- 기존 세션이 있으면 반환
    IF existing_session_id IS NOT NULL THEN
        -- 마지막 접근 시간 업데이트
        UPDATE sessions 
        SET last_accessed = NOW()
        WHERE session_id = existing_session_id;
        
        RETURN QUERY SELECT existing_session_id, existing_token, FALSE;
        RETURN;
    END IF;
    
    -- 기존 세션이 없으면 새 세션 생성
    new_session_id := gen_random_uuid()::TEXT;
    
    -- 사용자의 누적 세션 수 계산
    SELECT COALESCE(MAX(s.session_count), 0) + 1 
    INTO session_count_val
    FROM sessions s 
    WHERE s.user_id = input_user_id;
    
    -- 새 세션 생성
    INSERT INTO sessions (session_id, user_id, session_count)
    VALUES (new_session_id, input_user_id, session_count_val)
    RETURNING sessions.session_token INTO new_token;
    
    RETURN QUERY SELECT new_session_id, new_token, TRUE;
END;
$$ LANGUAGE plpgsql;

-- 새 세션 생성 (토큰 포함) - 기존 함수 유지 (호환성)
CREATE OR REPLACE FUNCTION create_session_with_token(input_user_id TEXT)
RETURNS TABLE(session_id TEXT, session_token UUID) AS $$
DECLARE
    new_session_id TEXT;
    new_token UUID;
    session_count_val INTEGER;
BEGIN
    -- 새 세션 ID 생성
    new_session_id := gen_random_uuid()::TEXT;
    
    -- 사용자의 누적 세션 수 계산
    SELECT COALESCE(MAX(s.session_count), 0) + 1 
    INTO session_count_val
    FROM sessions s 
    WHERE s.user_id = input_user_id;
    
    -- 새 세션 생성
    INSERT INTO sessions (session_id, user_id, session_count)
    VALUES (new_session_id, input_user_id, session_count_val)
    RETURNING sessions.session_token INTO new_token;
    
    RETURN QUERY SELECT new_session_id, new_token;
END;
$$ LANGUAGE plpgsql;

-- 세션 토큰으로 인증
CREATE OR REPLACE FUNCTION authenticate_by_token(input_token UUID)
RETURNS TABLE(
    user_id TEXT,
    session_id TEXT,
    name TEXT,
    group_type TEXT,
    status TEXT,
    phone TEXT,
    gender TEXT,
    age INTEGER
) AS $$
BEGIN
    -- 세션 마지막 접근 시간 업데이트
    UPDATE sessions 
    SET last_accessed = NOW()
    WHERE session_token = input_token 
    AND is_active = TRUE;
    
    -- 사용자 정보 반환
    RETURN QUERY
    SELECT s.user_id, s.session_id, p.name, p.group_type, p.status, p.phone, p.gender, p.age
    FROM sessions s
    JOIN participants p ON s.user_id = p.user_id
    WHERE s.session_token = input_token 
    AND s.is_active = TRUE
    AND p.status = 'active';
END;
$$ LANGUAGE plpgsql;

-- 참가자 인증 (로그인용)
CREATE OR REPLACE FUNCTION authenticate_participant(input_user_id TEXT, input_password TEXT)
RETURNS TABLE(
    user_id TEXT,
    name TEXT,
    group_type TEXT,
    status TEXT,
    phone TEXT,
    gender TEXT,
    age INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.user_id, p.name, p.group_type, p.status, p.phone, p.gender, p.age
    FROM participants p
    WHERE p.user_id = input_user_id 
    AND p.password = input_password
    AND p.status = 'active';
END;
$$ LANGUAGE plpgsql;

-- 참가자 추가
CREATE OR REPLACE FUNCTION add_participant(
    input_user_id TEXT,
    input_password TEXT,
    input_name TEXT,
    input_group_type TEXT,
    input_phone TEXT DEFAULT NULL,
    input_gender TEXT DEFAULT NULL,
    input_age INTEGER DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO participants (user_id, password, name, group_type, phone, gender, age)
    VALUES (input_user_id, input_password, input_name, input_group_type, input_phone, input_gender, input_age);
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- 메시지 저장
CREATE OR REPLACE FUNCTION save_message(
    input_session_id TEXT,
    input_role TEXT,
    input_content TEXT,
    input_response_time FLOAT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    msg_id UUID;
BEGIN
    INSERT INTO messages (session_id, role, content, response_time_seconds)
    VALUES (input_session_id, input_role, input_content, input_response_time)
    RETURNING message_id INTO msg_id;
    
    RETURN msg_id;
END;
$$ LANGUAGE plpgsql;

-- 세션 종료
CREATE OR REPLACE FUNCTION end_session(input_session_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE sessions 
    SET end_time = NOW(), is_active = FALSE
    WHERE session_id = input_session_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 세션 메시지 조회 (LangChain 호환)
CREATE OR REPLACE FUNCTION get_session_messages(input_session_id TEXT)
RETURNS TABLE(
    role TEXT,
    content TEXT,
    msg_timestamp TIMESTAMP,
    message_order INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT m.role, m.content, m.timestamp, m.message_order
    FROM messages m
    WHERE m.session_id = input_session_id
    ORDER BY m.message_order ASC;
END;
$$ LANGUAGE plpgsql;

-- 비활성 세션 정리 (7일 이상 미접속)
CREATE OR REPLACE FUNCTION cleanup_inactive_sessions()
RETURNS INTEGER AS $$
DECLARE
    cleaned_count INTEGER;
BEGIN
    UPDATE sessions 
    SET is_active = FALSE
    WHERE last_accessed < NOW() - INTERVAL '7 days' 
    AND is_active = TRUE;
    
    GET DIAGNOSTICS cleaned_count = ROW_COUNT;
    RETURN cleaned_count;
END;
$$ LANGUAGE plpgsql;

-- 참가자 정보 조회 (관리자 로드 기능용)
CREATE OR REPLACE FUNCTION get_participant_info(input_user_id TEXT)
RETURNS TABLE(
    user_id TEXT,
    password TEXT,
    name TEXT,
    group_type TEXT,
    status TEXT,
    phone TEXT,
    gender TEXT,
    age INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.user_id, p.password, p.name, p.group_type, p.status, 
           p.phone, p.gender, p.age, p.created_at, p.updated_at
    FROM participants p
    WHERE p.user_id = input_user_id;
END;
$$ LANGUAGE plpgsql;

-- 참가자 정보 수정 (관리자 수정 기능용)
CREATE OR REPLACE FUNCTION update_participant(
    input_user_id TEXT,
    input_name TEXT DEFAULT NULL,
    input_password TEXT DEFAULT NULL,
    input_phone TEXT DEFAULT NULL,
    input_gender TEXT DEFAULT NULL,
    input_age INTEGER DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    update_count INTEGER := 0;
BEGIN
    -- 참가자 존재 확인
    IF NOT EXISTS (SELECT 1 FROM participants WHERE user_id = input_user_id) THEN
        RETURN FALSE;
    END IF;
    
    -- 동적 업데이트 (NULL이 아닌 값만 업데이트)
    UPDATE participants SET
        name = COALESCE(input_name, name),
        password = COALESCE(input_password, password),
        phone = COALESCE(input_phone, phone),
        gender = COALESCE(input_gender, gender),
        age = COALESCE(input_age, age),
        updated_at = NOW()
    WHERE user_id = input_user_id;
    
    GET DIAGNOSTICS update_count = ROW_COUNT;
    RETURN update_count > 0;
END;
$$ LANGUAGE plpgsql;

-- 참가자 삭제 (관리자 삭제 기능용, CASCADE로 관련 데이터 모두 삭제)
CREATE OR REPLACE FUNCTION delete_participant(input_user_id TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    delete_count INTEGER := 0;
BEGIN
    -- 관리자 계정 삭제 방지
    IF input_user_id = 'admin' THEN
        RETURN FALSE;
    END IF;
    
    -- 참가자 존재 확인
    IF NOT EXISTS (SELECT 1 FROM participants WHERE user_id = input_user_id) THEN
        RETURN FALSE;
    END IF;
    
    -- CASCADE 삭제 (foreign key로 자동 처리되지만 명시적으로)
    -- 1. 메시지 삭제
    DELETE FROM messages 
    WHERE session_id IN (
        SELECT session_id FROM sessions WHERE user_id = input_user_id
    );
    
    -- 2. 세션 삭제
    DELETE FROM sessions WHERE user_id = input_user_id;
    
    -- 3. 참가자 삭제
    DELETE FROM participants WHERE user_id = input_user_id;
    
    GET DIAGNOSTICS delete_count = ROW_COUNT;
    RETURN delete_count > 0;
END;
$$ LANGUAGE plpgsql;

-- 모든 참가자 목록 조회 (관리자 목록 표시용)
CREATE OR REPLACE FUNCTION get_all_participants()
RETURNS TABLE(
    user_id TEXT,
    password TEXT,
    name TEXT,
    group_type TEXT,
    status TEXT,
    phone TEXT,
    gender TEXT,
    age INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.user_id, p.password, p.name, p.group_type, p.status,
           p.phone, p.gender, p.age, p.created_at, p.updated_at
    FROM participants p
    ORDER BY 
        CASE 
            WHEN p.group_type = 'admin' THEN 0
            WHEN p.group_type = 'treatment' THEN 1
            WHEN p.group_type = 'control' THEN 2
            ELSE 3
        END,
        p.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- 참가자 상태 업데이트 (관리자 상태 변경용)
CREATE OR REPLACE FUNCTION update_participant_status(
    input_user_id TEXT,
    input_status TEXT
)
RETURNS BOOLEAN AS $$
BEGIN
    -- 유효한 상태값 확인
    IF input_status NOT IN ('active', 'inactive', 'completed', 'dropout') THEN
        RETURN FALSE;
    END IF;
    
    -- 참가자 존재 확인 및 상태 업데이트
    UPDATE participants 
    SET status = input_status, updated_at = NOW()
    WHERE user_id = input_user_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ==============================================
-- 8. 연구용 분석 뷰 (최소한만)
-- ==============================================

-- 사용자별 세션 요약
CREATE OR REPLACE VIEW user_session_summary AS
SELECT 
    user_id,
    COUNT(*) as total_sessions,
    MIN(start_time) as first_session,
    MAX(start_time) as last_session,
    SUM(total_messages) as total_messages,
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_sessions
FROM sessions 
GROUP BY user_id;

-- 일별 활동 요약
CREATE OR REPLACE VIEW daily_activity AS
SELECT 
    DATE(start_time) as activity_date,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_sessions,
    SUM(total_messages) as total_messages
FROM sessions
GROUP BY DATE(start_time)
ORDER BY activity_date DESC;

-- 연구 통계 요약 (관리자 대시보드용)
CREATE OR REPLACE FUNCTION get_research_summary()
RETURNS TABLE(
    total_participants INTEGER,
    active_participants INTEGER,
    treatment_group INTEGER,
    control_group INTEGER,
    completed_participants INTEGER,
    dropout_participants INTEGER,
    total_sessions INTEGER,
    total_messages INTEGER,
    avg_age NUMERIC,
    male_participants INTEGER,
    female_participants INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        -- 전체 참가자 수 (관리자 제외)
        (SELECT COUNT(*)::INTEGER FROM participants WHERE group_type != 'admin') as total_participants,
        
        -- 활성 참가자 수
        (SELECT COUNT(*)::INTEGER FROM participants WHERE status = 'active' AND group_type != 'admin') as active_participants,
        
        -- Treatment 그룹 수
        (SELECT COUNT(*)::INTEGER FROM participants WHERE group_type = 'treatment') as treatment_group,
        
        -- Control 그룹 수  
        (SELECT COUNT(*)::INTEGER FROM participants WHERE group_type = 'control') as control_group,
        
        -- 완료 참가자 수
        (SELECT COUNT(*)::INTEGER FROM participants WHERE status = 'completed' AND group_type != 'admin') as completed_participants,
        
        -- 드롭아웃 참가자 수
        (SELECT COUNT(*)::INTEGER FROM participants WHERE status = 'dropout' AND group_type != 'admin') as dropout_participants,
        
        -- 전체 세션 수
        (SELECT COUNT(*)::INTEGER FROM sessions WHERE user_id != 'admin') as total_sessions,
        
        -- 전체 메시지 수
        (SELECT COUNT(*)::INTEGER FROM messages m 
         JOIN sessions s ON m.session_id = s.session_id 
         WHERE s.user_id != 'admin') as total_messages,
        
        -- 평균 나이
        (SELECT COALESCE(AVG(age), 0)::NUMERIC(5,1) FROM participants WHERE group_type != 'admin' AND age IS NOT NULL) as avg_age,
        
        -- 남성 참가자 수
        (SELECT COUNT(*)::INTEGER FROM participants WHERE gender = '남성' AND group_type != 'admin') as male_participants,
        
        -- 여성 참가자 수
        (SELECT COUNT(*)::INTEGER FROM participants WHERE gender = '여성' AND group_type != 'admin') as female_participants;
END;
$$ LANGUAGE plpgsql;

-- ==============================================
-- 9. 데이터 제약조건 및 검증
-- ==============================================

-- 세션 시간 검증
ALTER TABLE sessions ADD CONSTRAINT check_session_times 
    CHECK (end_time IS NULL OR end_time >= start_time);

-- 메시지 수 검증
ALTER TABLE sessions ADD CONSTRAINT check_total_messages 
    CHECK (total_messages >= 0);

-- 메시지 길이 검증
ALTER TABLE messages ADD CONSTRAINT check_message_length 
    CHECK (message_length >= 0);

-- 응답 시간 검증
ALTER TABLE messages ADD CONSTRAINT check_response_time 
    CHECK (response_time_seconds IS NULL OR response_time_seconds >= 0);

-- 세션 카운트 검증
ALTER TABLE sessions ADD CONSTRAINT check_session_count 
    CHECK (session_count > 0);

-- ==============================================
-- 10. 테이블 설명
-- ==============================================

COMMENT ON TABLE participants IS 'PTSD 연구 참가자 정보';
COMMENT ON TABLE sessions IS '사용자 세션 (토큰 기반 지속성)';
COMMENT ON TABLE messages IS '모든 대화 메시지 통합 저장';

COMMENT ON FUNCTION get_or_create_session_with_token IS '기존 활성 세션 조회 또는 새 세션 생성 (세션 지속성)';
COMMENT ON FUNCTION create_session_with_token IS '토큰 포함 새 세션 생성';
COMMENT ON FUNCTION authenticate_by_token IS '토큰 기반 사용자 인증';
COMMENT ON FUNCTION authenticate_participant IS '로그인용 참가자 인증';
COMMENT ON FUNCTION add_participant IS '새 참가자 등록';
COMMENT ON FUNCTION save_message IS '메시지 저장 (자동 순서)';
COMMENT ON FUNCTION get_session_messages IS '세션 메시지 조회';
COMMENT ON FUNCTION get_participant_info IS '참가자 정보 조회 (관리자 로드용)';
COMMENT ON FUNCTION update_participant IS '참가자 정보 수정 (관리자 수정용)';
COMMENT ON FUNCTION delete_participant IS '참가자 삭제 (관리자 삭제용, CASCADE)';
COMMENT ON FUNCTION get_all_participants IS '모든 참가자 목록 조회 (관리자 목록용)';
COMMENT ON FUNCTION get_research_summary IS '연구 통계 요약 (관리자 대시보드용)';
COMMENT ON FUNCTION update_participant_status IS '참가자 상태 업데이트 (관리자 상태 변경용)';

-- ==============================================
-- 11. 설정 완료 확인
-- ==============================================

DO $$
DECLARE
    table_count INTEGER;
    function_count INTEGER;
    view_count INTEGER;
    participant_count INTEGER;
BEGIN
    -- 생성된 테이블 수 확인
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
    
    -- 생성된 함수 수 확인
    SELECT COUNT(*) INTO function_count
    FROM information_schema.routines 
    WHERE routine_schema = 'public' 
    AND routine_type = 'FUNCTION'
    AND routine_name IN (
        'get_or_create_session_with_token',
        'create_session_with_token',
        'authenticate_by_token', 
        'authenticate_participant',
        'add_participant',
        'save_message',
        'end_session',
        'get_session_messages',
        'cleanup_inactive_sessions',
        'get_participant_info',
        'update_participant',
        'delete_participant',
        'get_all_participants',
        'get_research_summary',
        'update_participant_status'
    );
    
    -- 생성된 뷰 수 확인
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views 
    WHERE table_schema = 'public';
    
    -- 참가자 수 확인
    SELECT COUNT(*) INTO participant_count
    FROM participants;
    
    RAISE NOTICE '=== 필수 스키마 설정 완료 (CRUD 함수 포함) ===';
    RAISE NOTICE '생성된 테이블: %개 (예상: 3개)', table_count;
    RAISE NOTICE '생성된 함수: %개 (예상: 15개)', function_count;
    RAISE NOTICE '생성된 뷰: %개 (예상: 2개)', view_count;
    RAISE NOTICE '등록된 참가자: %명 (기본 관리자 포함)', participant_count;
    RAISE NOTICE '=============================';
    
    IF table_count >= 3 AND function_count >= 15 AND participant_count >= 1 THEN
        RAISE NOTICE '✅ 필수 스키마가 성공적으로 설정되었습니다!';
        RAISE NOTICE '기본 관리자: admin / CHANGE_THIS_PASSWORD';
        RAISE NOTICE '이제 애플리케이션을 실행할 수 있습니다.';
    ELSE
        RAISE NOTICE '⚠️  일부 설정이 누락되었을 수 있습니다.';
    END IF;
END $$;