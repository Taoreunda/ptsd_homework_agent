-- 단순화된 참가자 테이블 스키마 (연구용 최적화)
-- username 제거, 인구통계학적 정보 추가

-- 1. 기존 테이블 삭제 (필요시)
-- DROP TABLE IF EXISTS participants CASCADE;

-- 2. 단순화된 참가자 테이블 생성
CREATE TABLE IF NOT EXISTS participants (
    user_id TEXT PRIMARY KEY,              -- 참가자 고유 ID (P001, P002, admin 등)
    password TEXT NOT NULL,                -- 로그인용 비밀번호
    name TEXT NOT NULL,                    -- 참가자 이름/닉네임
    group_type TEXT NOT NULL CHECK (group_type IN ('treatment', 'control', 'admin')), -- 실험 그룹
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'dropout', 'completed')), -- 참가 상태
    phone TEXT,                            -- 전화번호 (연구자 연락용)
    gender TEXT CHECK (gender IN ('남성', '여성', '기타')), -- 성별
    age INTEGER CHECK (age >= 18 AND age <= 100), -- 나이 (성인 연구 대상)
    created_at TIMESTAMP DEFAULT NOW()     -- 등록일시
);

-- 3. 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_participants_group ON participants(group_type);
CREATE INDEX IF NOT EXISTS idx_participants_status ON participants(status);
CREATE INDEX IF NOT EXISTS idx_participants_created_at ON participants(created_at);

-- 4. 기본 관리자 계정 생성
-- 보안상 실제 비밀번호는 배포 시 수동으로 설정하세요
INSERT INTO participants (user_id, password, name, group_type, status)
VALUES ('admin', 'CHANGE_THIS_PASSWORD', '연구관리자', 'admin', 'active')
ON CONFLICT (user_id) DO UPDATE SET
    password = EXCLUDED.password,
    name = EXCLUDED.name,
    group_type = EXCLUDED.group_type,
    status = EXCLUDED.status;

-- 5. 참가자 인증 함수 (user_id 기반)
CREATE OR REPLACE FUNCTION authenticate_participant(
    input_user_id TEXT,
    input_password TEXT
)
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
    SELECT 
        p.user_id,
        p.name,
        p.group_type,
        p.status,
        p.phone,
        p.gender,
        p.age
    FROM participants p
    WHERE p.user_id = input_user_id 
    AND p.password = input_password
    AND p.status = 'active';
END;
$$ LANGUAGE plpgsql;

-- 6. 새 참가자 추가 함수
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
    WHEN unique_violation THEN
        RETURN FALSE;
    WHEN check_violation THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- 7. 참가자 상태 업데이트 함수
CREATE OR REPLACE FUNCTION update_participant_status(
    input_user_id TEXT,
    new_status TEXT
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE participants 
    SET status = new_status
    WHERE user_id = input_user_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 8. 참가자 정보 수정 함수
CREATE OR REPLACE FUNCTION update_participant_info(
    input_user_id TEXT,
    input_name TEXT DEFAULT NULL,
    input_phone TEXT DEFAULT NULL,
    input_gender TEXT DEFAULT NULL,
    input_age INTEGER DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE participants 
    SET 
        name = COALESCE(input_name, name),
        phone = COALESCE(input_phone, phone),
        gender = COALESCE(input_gender, gender),
        age = COALESCE(input_age, age)
    WHERE user_id = input_user_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 9. 참가자 통계 뷰 (단순화)
CREATE OR REPLACE VIEW participant_summary AS
SELECT 
    p.user_id,
    p.name,
    p.group_type,
    p.status,
    p.phone,
    p.gender,
    p.age,
    p.created_at,
    COALESCE(s.total_sessions, 0) as completed_sessions,
    COALESCE(s.total_messages, 0) as total_messages,
    s.last_session,
    CASE 
        WHEN s.last_session IS NULL THEN NULL
        ELSE EXTRACT(DAYS FROM (NOW() - s.last_session))
    END as days_since_last_session
FROM participants p
LEFT JOIN (
    SELECT 
        user_id,
        COUNT(*) as total_sessions,
        SUM(total_messages) as total_messages,
        MAX(start_time) as last_session
    FROM sessions
    GROUP BY user_id
) s ON p.user_id = s.user_id
WHERE p.group_type IN ('treatment', 'control'); -- admin 제외

-- 10. 연구 전체 통계 함수
CREATE OR REPLACE FUNCTION get_research_summary()
RETURNS TABLE(
    total_participants INTEGER,
    active_participants INTEGER,
    treatment_group INTEGER,
    control_group INTEGER,
    dropout_participants INTEGER,
    completed_participants INTEGER,
    avg_age FLOAT,
    male_participants INTEGER,
    female_participants INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_participants,
        COUNT(CASE WHEN status = 'active' THEN 1 END)::INTEGER as active_participants,
        COUNT(CASE WHEN group_type = 'treatment' THEN 1 END)::INTEGER as treatment_group,
        COUNT(CASE WHEN group_type = 'control' THEN 1 END)::INTEGER as control_group,
        COUNT(CASE WHEN status = 'dropout' THEN 1 END)::INTEGER as dropout_participants,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)::INTEGER as completed_participants,
        AVG(age)::FLOAT as avg_age,
        COUNT(CASE WHEN gender = '남성' THEN 1 END)::INTEGER as male_participants,
        COUNT(CASE WHEN gender = '여성' THEN 1 END)::INTEGER as female_participants
    FROM participants 
    WHERE group_type IN ('treatment', 'control'); -- admin 제외
END;
$$ LANGUAGE plpgsql;

-- 11. 데이터 검증
DO $$
BEGIN
    -- 테이블 존재 확인
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'participants') THEN
        RAISE EXCEPTION 'participants 테이블 생성 실패';
    END IF;
    
    -- 관리자 계정 확인
    IF NOT EXISTS (SELECT FROM participants WHERE user_id = 'admin') THEN
        RAISE EXCEPTION '관리자 계정 생성 실패';
    END IF;
    
    RAISE NOTICE '단순화된 participants 테이블 생성 완료';
END $$;

-- 12. 스키마 버전 정보
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description) 
VALUES ('2.0.0', '단순화된 participants 테이블 - username 제거, 인구통계학적 정보 추가') 
ON CONFLICT (version) DO NOTHING;

-- 테이블 설명 추가
COMMENT ON TABLE participants IS 'PTSD 연구 참가자 정보 (단순화 버전)';
COMMENT ON COLUMN participants.user_id IS '참가자 고유 ID (로그인에도 사용)';
COMMENT ON COLUMN participants.phone IS '연구자 연락용 전화번호';
COMMENT ON COLUMN participants.gender IS '인구통계학적 분석용 성별';
COMMENT ON COLUMN participants.age IS '인구통계학적 분석용 나이';
COMMENT ON FUNCTION authenticate_participant IS 'user_id 기반 참가자 인증';
COMMENT ON FUNCTION add_participant IS '새 참가자 등록 (관리자용)';
COMMENT ON VIEW participant_summary IS '참가자별 상세 통계 (연구용)';