-- 세션 지속성을 위한 추가 테이블들
-- LangChain 기반 PostgreSQL 백엔드 메모리 시스템

-- 1. 사용자 세션 토큰 테이블
CREATE TABLE IF NOT EXISTS user_sessions (
    session_token UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES participants(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '7 days',
    last_accessed TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

-- 2. 대화 스레드 테이블 (LangChain 메모리 백엔드)
CREATE TABLE IF NOT EXISTS conversation_threads (
    thread_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES participants(user_id) ON DELETE CASCADE,
    session_token UUID REFERENCES user_sessions(session_token) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    summary TEXT,  -- 대화 요약 (ConversationSummaryMemory)
    message_count INTEGER DEFAULT 0
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_conversation_threads_user_id ON conversation_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_session ON conversation_threads(session_token);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_active ON conversation_threads(is_active);

-- 3. 대화 메시지 상세 테이블 (기존 messages 테이블 확장)
CREATE TABLE IF NOT EXISTS conversation_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(thread_id) ON DELETE CASCADE,
    session_id TEXT,  -- 기존 sessions 테이블과의 호환성
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    message_order INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',  -- 추가 메타데이터 (응답시간, 길이 등)
    is_summarized BOOLEAN DEFAULT FALSE  -- 요약에 포함되었는지 여부
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_conversation_messages_thread ON conversation_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_order ON conversation_messages(thread_id, message_order);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_timestamp ON conversation_messages(timestamp);

-- 4. 세션 관리 함수들

-- 새 세션 토큰 생성
CREATE OR REPLACE FUNCTION create_user_session(input_user_id TEXT)
RETURNS UUID AS $$
DECLARE
    new_token UUID;
BEGIN
    -- 기존 활성 세션 비활성화
    UPDATE user_sessions 
    SET is_active = FALSE 
    WHERE user_id = input_user_id AND is_active = TRUE;
    
    -- 새 세션 토큰 생성
    INSERT INTO user_sessions (user_id)
    VALUES (input_user_id)
    RETURNING session_token INTO new_token;
    
    RETURN new_token;
END;
$$ LANGUAGE plpgsql;

-- 세션 토큰으로 사용자 인증
CREATE OR REPLACE FUNCTION authenticate_by_session(input_token UUID)
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
    -- 세션 유효성 검사 및 마지막 접근 시간 업데이트
    UPDATE user_sessions 
    SET last_accessed = NOW()
    WHERE session_token = input_token 
    AND expires_at > NOW() 
    AND is_active = TRUE;
    
    -- 사용자 정보 반환
    RETURN QUERY
    SELECT p.user_id, p.name, p.group_type, p.status, p.phone, p.gender, p.age
    FROM participants p
    JOIN user_sessions s ON p.user_id = s.user_id
    WHERE s.session_token = input_token 
    AND s.expires_at > NOW() 
    AND s.is_active = TRUE
    AND p.status = 'active';
END;
$$ LANGUAGE plpgsql;

-- 대화 스레드 생성
CREATE OR REPLACE FUNCTION create_conversation_thread(
    input_user_id TEXT,
    input_session_token UUID
)
RETURNS UUID AS $$
DECLARE
    thread_id UUID;
BEGIN
    -- 기존 활성 스레드 비활성화
    UPDATE conversation_threads 
    SET is_active = FALSE, updated_at = NOW()
    WHERE user_id = input_user_id AND is_active = TRUE;
    
    -- 새 스레드 생성
    INSERT INTO conversation_threads (user_id, session_token)
    VALUES (input_user_id, input_session_token)
    RETURNING conversation_threads.thread_id INTO thread_id;
    
    RETURN thread_id;
END;
$$ LANGUAGE plpgsql;

-- 대화 메시지 저장
CREATE OR REPLACE FUNCTION save_conversation_message(
    input_thread_id UUID,
    input_role TEXT,
    input_content TEXT,
    input_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    msg_id UUID;
    next_order INTEGER;
BEGIN
    -- 다음 메시지 순서 계산
    SELECT COALESCE(MAX(message_order), 0) + 1 
    INTO next_order
    FROM conversation_messages 
    WHERE thread_id = input_thread_id;
    
    -- 메시지 저장
    INSERT INTO conversation_messages (
        thread_id, role, content, message_order, metadata
    )
    VALUES (
        input_thread_id, input_role, input_content, next_order, input_metadata
    )
    RETURNING message_id INTO msg_id;
    
    -- 스레드 메시지 카운트 업데이트
    UPDATE conversation_threads 
    SET message_count = message_count + 1, updated_at = NOW()
    WHERE thread_id = input_thread_id;
    
    RETURN msg_id;
END;
$$ LANGUAGE plpgsql;

-- 대화 히스토리 조회
CREATE OR REPLACE FUNCTION get_conversation_history(input_thread_id UUID)
RETURNS TABLE(
    role TEXT,
    content TEXT,
    msg_timestamp TIMESTAMP,
    message_order INTEGER,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT cm.role, cm.content, cm.timestamp, cm.message_order, cm.metadata
    FROM conversation_messages cm
    WHERE cm.thread_id = input_thread_id
    ORDER BY cm.message_order ASC;
END;
$$ LANGUAGE plpgsql;

-- 사용자의 활성 스레드 조회
CREATE OR REPLACE FUNCTION get_active_thread(input_user_id TEXT)
RETURNS UUID AS $$
DECLARE
    active_thread_id UUID;
BEGIN
    SELECT thread_id INTO active_thread_id
    FROM conversation_threads
    WHERE user_id = input_user_id 
    AND is_active = TRUE
    ORDER BY created_at DESC
    LIMIT 1;
    
    RETURN active_thread_id;
END;
$$ LANGUAGE plpgsql;

-- 만료된 세션 정리 (주기적 실행용)
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    cleaned_count INTEGER;
BEGIN
    -- 만료된 세션 비활성화
    UPDATE user_sessions 
    SET is_active = FALSE
    WHERE expires_at < NOW() AND is_active = TRUE;
    
    GET DIAGNOSTICS cleaned_count = ROW_COUNT;
    
    -- 비활성 스레드도 정리
    UPDATE conversation_threads
    SET is_active = FALSE
    WHERE session_token IN (
        SELECT session_token FROM user_sessions WHERE is_active = FALSE
    ) AND is_active = TRUE;
    
    RETURN cleaned_count;
END;
$$ LANGUAGE plpgsql;

-- 테이블 설명 추가
COMMENT ON TABLE user_sessions IS '사용자 세션 토큰 관리 (브라우저 새로고침 대응)';
COMMENT ON TABLE conversation_threads IS '대화 스레드 관리 (LangChain 메모리 백엔드)';
COMMENT ON TABLE conversation_messages IS '대화 메시지 상세 저장';

COMMENT ON FUNCTION create_user_session IS '새 사용자 세션 토큰 생성';
COMMENT ON FUNCTION authenticate_by_session IS '세션 토큰으로 사용자 인증';
COMMENT ON FUNCTION create_conversation_thread IS '새 대화 스레드 생성';
COMMENT ON FUNCTION save_conversation_message IS '대화 메시지 저장';
COMMENT ON FUNCTION get_conversation_history IS '대화 히스토리 조회';
COMMENT ON FUNCTION get_active_thread IS '사용자의 활성 대화 스레드 조회';
COMMENT ON FUNCTION cleanup_expired_sessions IS '만료된 세션 정리';

-- 초기 데이터 검증
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_sessions') THEN
        RAISE EXCEPTION 'user_sessions 테이블 생성 실패';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversation_threads') THEN
        RAISE EXCEPTION 'conversation_threads 테이블 생성 실패';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversation_messages') THEN
        RAISE EXCEPTION 'conversation_messages 테이블 생성 실패';
    END IF;
    
    RAISE NOTICE '세션 지속성 테이블 생성 완료';
END $$;