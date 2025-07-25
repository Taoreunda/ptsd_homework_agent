-- PTSD 심리치료 연구용 데이터베이스 스키마
-- Supabase PostgreSQL용 테이블 생성 스크립트

-- 1. 세션 정보 테이블
-- 사용자의 각 접속 세션에 대한 메타데이터 저장
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,           -- 고유 세션 식별자 (UUID)
    user_id TEXT NOT NULL,                -- 참가자 ID (participants.json과 연동)
    start_time TIMESTAMP DEFAULT NOW(),   -- 세션 시작 시간
    end_time TIMESTAMP,                   -- 세션 종료 시간 (NULL이면 진행중)
    total_messages INTEGER DEFAULT 0,     -- 해당 세션의 총 메시지 수
    session_count INTEGER DEFAULT 1,      -- 해당 사용자의 누적 접속 횟수
    created_at TIMESTAMP DEFAULT NOW()    -- 레코드 생성 시간
);

-- 2. 메시지 상세 테이블  
-- 모든 대화 메시지의 상세 정보 저장
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,                          -- 자동 증가 ID
    session_id TEXT NOT NULL,                       -- 세션 ID (외래키)
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),  -- 메시지 발신자
    content TEXT NOT NULL,                          -- 메시지 내용
    timestamp TIMESTAMP DEFAULT NOW(),              -- 메시지 전송 시간
    message_length INTEGER,                         -- 메시지 글자 수
    response_time_seconds FLOAT,                    -- 이전 메시지로부터 응답 시간 (초)
    created_at TIMESTAMP DEFAULT NOW(),             -- 레코드 생성 시간
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- 3. 성능 최적화를 위한 인덱스 생성
-- 자주 사용되는 쿼리 패턴에 대한 인덱스

-- 사용자별 세션 조회용
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- 시간순 세션 정렬용
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time DESC);

-- 세션별 메시지 조회용 (가장 중요)
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);

-- 시간순 메시지 정렬용
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

-- 사용자별 전체 메시지 조회용 (복합 인덱스)
CREATE INDEX IF NOT EXISTS idx_messages_user_session ON messages(session_id, timestamp);

-- 4. 연구 분석용 뷰 생성
-- 자주 사용되는 분석 쿼리를 뷰로 미리 정의

-- 사용자별 세션 통계 뷰
CREATE OR REPLACE VIEW user_session_stats AS
SELECT 
    user_id,
    COUNT(*) as total_sessions,
    MIN(start_time) as first_session,
    MAX(start_time) as last_session,
    AVG(total_messages) as avg_messages_per_session,
    SUM(total_messages) as total_messages,
    AVG(EXTRACT(EPOCH FROM (end_time - start_time))/60) as avg_session_duration_minutes
FROM sessions 
WHERE end_time IS NOT NULL
GROUP BY user_id;

-- 일별 활동 통계 뷰
CREATE OR REPLACE VIEW daily_activity_stats AS
SELECT 
    DATE(start_time) as activity_date,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_sessions,
    AVG(total_messages) as avg_messages_per_session,
    SUM(total_messages) as total_messages
FROM sessions
GROUP BY DATE(start_time)
ORDER BY activity_date DESC;

-- 메시지 분석용 뷰 (응답 시간, 길이 통계)
CREATE OR REPLACE VIEW message_analysis AS
SELECT 
    s.user_id,
    s.session_id,
    m.role,
    COUNT(*) as message_count,
    AVG(m.message_length) as avg_message_length,
    AVG(m.response_time_seconds) as avg_response_time_seconds,
    MIN(m.timestamp) as first_message,
    MAX(m.timestamp) as last_message
FROM sessions s
JOIN messages m ON s.session_id = m.session_id
GROUP BY s.user_id, s.session_id, m.role;

-- 5. 데이터 정합성을 위한 트리거 함수
-- 세션의 total_messages 자동 업데이트

CREATE OR REPLACE FUNCTION update_session_message_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- 새 메시지 추가시 세션의 total_messages 증가
        UPDATE sessions 
        SET total_messages = total_messages + 1
        WHERE session_id = NEW.session_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        -- 메시지 삭제시 세션의 total_messages 감소
        UPDATE sessions 
        SET total_messages = total_messages - 1
        WHERE session_id = OLD.session_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성 (메시지 추가/삭제시 자동 실행)
CREATE TRIGGER trigger_update_message_count
    AFTER INSERT OR DELETE ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_message_count();

-- 6. 연구 데이터 분석용 함수들

-- 특정 사용자의 드랍아웃 위험도 계산 함수
CREATE OR REPLACE FUNCTION calculate_dropout_risk(input_user_id TEXT)
RETURNS FLOAT AS $$
DECLARE
    days_since_last_session INTEGER;
    session_frequency FLOAT;
    avg_response_time FLOAT;
    risk_score FLOAT := 0;
BEGIN
    -- 마지막 세션 이후 경과 일수
    SELECT EXTRACT(DAYS FROM (NOW() - MAX(start_time)))
    INTO days_since_last_session
    FROM sessions WHERE user_id = input_user_id;
    
    -- 주간 세션 빈도 계산
    SELECT COUNT(*)::FLOAT / 
           GREATEST(EXTRACT(DAYS FROM (MAX(start_time) - MIN(start_time))) / 7, 1)
    INTO session_frequency
    FROM sessions WHERE user_id = input_user_id;
    
    -- 평균 응답 시간 계산
    SELECT AVG(response_time_seconds)
    INTO avg_response_time
    FROM messages m
    JOIN sessions s ON m.session_id = s.session_id
    WHERE s.user_id = input_user_id AND m.role = 'user';
    
    -- 위험도 점수 계산 (0-1 범위)
    risk_score := 0;
    
    -- 접속 간격이 길수록 위험 증가
    IF days_since_last_session > 3 THEN
        risk_score := risk_score + 0.4;
    ELSIF days_since_last_session > 7 THEN
        risk_score := risk_score + 0.7;
    END IF;
    
    -- 세션 빈도가 낮을수록 위험 증가
    IF session_frequency < 1 THEN
        risk_score := risk_score + 0.3;
    END IF;
    
    -- 응답 시간이 길수록 위험 증가
    IF avg_response_time > 30 THEN
        risk_score := risk_score + 0.2;
    END IF;
    
    RETURN LEAST(risk_score, 1.0);  -- 최대 1.0으로 제한
END;
$$ LANGUAGE plpgsql;

-- 7. 데이터 정리 및 백업용 함수

-- 오래된 세션 데이터 아카이브 함수 (선택적 사용)
CREATE OR REPLACE FUNCTION archive_old_sessions(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- 지정된 일수 이전의 완료된 세션을 별도 테이블로 이동
    -- (실제 운영에서는 신중하게 사용)
    
    SELECT COUNT(*) INTO archived_count
    FROM sessions 
    WHERE end_time IS NOT NULL 
    AND end_time < NOW() - INTERVAL '1 day' * days_old;
    
    -- 여기서는 개수만 반환 (실제 아카이브는 주석 처리)
    -- CREATE TABLE IF NOT EXISTS sessions_archive AS SELECT * FROM sessions WHERE ...
    -- DELETE FROM sessions WHERE ...
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- 8. 데이터 검증용 제약조건 추가

-- 메시지 길이는 0 이상이어야 함
ALTER TABLE messages ADD CONSTRAINT check_message_length 
    CHECK (message_length >= 0);

-- 응답 시간은 0 이상이어야 함
ALTER TABLE messages ADD CONSTRAINT check_response_time 
    CHECK (response_time_seconds >= 0);

-- 세션의 total_messages는 0 이상이어야 함
ALTER TABLE sessions ADD CONSTRAINT check_total_messages 
    CHECK (total_messages >= 0);

-- 세션 종료 시간은 시작 시간보다 나중이어야 함
ALTER TABLE sessions ADD CONSTRAINT check_session_times 
    CHECK (end_time IS NULL OR end_time >= start_time);

-- 스키마 생성 완료 메시지
COMMENT ON TABLE sessions IS 'PTSD 심리치료 연구용 세션 메타데이터';
COMMENT ON TABLE messages IS 'PTSD 심리치료 연구용 대화 메시지 상세정보';

-- 데이터베이스 스키마 버전 정보
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description) 
VALUES ('1.0.0', 'PTSD 심리치료 연구용 초기 스키마') 
ON CONFLICT (version) DO NOTHING;