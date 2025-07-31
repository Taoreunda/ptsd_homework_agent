-- LLM 설정 관리 테이블 및 함수들
-- 프롬프트 튜닝 기능을 위한 확장 스키마

-- ==============================================
-- 1. LLM 설정 테이블
-- ==============================================

CREATE TABLE llm_configurations (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_name TEXT NOT NULL,                    -- 설정 이름 (예: "기본설정", "공감형", "분석형")
    system_prompt TEXT NOT NULL,                  -- 시스템 프롬프트 전체 텍스트
    model_name TEXT NOT NULL DEFAULT 'gpt-4.1',  -- AI 모델명
    temperature NUMERIC(3,2) DEFAULT 0.5 CHECK (temperature >= 0 AND temperature <= 2.0),
    max_tokens INTEGER DEFAULT 1000 CHECK (max_tokens >= 100 AND max_tokens <= 2000),
    top_p NUMERIC(3,2) DEFAULT 0.9 CHECK (top_p >= 0 AND top_p <= 1.0),
    frequency_penalty NUMERIC(3,2) DEFAULT 0.0 CHECK (frequency_penalty >= -2.0 AND frequency_penalty <= 2.0),
    presence_penalty NUMERIC(3,2) DEFAULT 0.0 CHECK (presence_penalty >= -2.0 AND presence_penalty <= 2.0),
    is_active BOOLEAN DEFAULT FALSE,              -- 현재 활성 설정 여부
    is_default BOOLEAN DEFAULT FALSE,             -- 기본 설정 여부
    created_by TEXT REFERENCES participants(user_id), -- 생성자 (관리자)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 활성 설정은 하나만 존재하도록 제약
CREATE UNIQUE INDEX idx_active_config ON llm_configurations (is_active) WHERE is_active = TRUE;

-- 기본 설정은 하나만 존재하도록 제약
CREATE UNIQUE INDEX idx_default_config ON llm_configurations (is_default) WHERE is_default = TRUE;

-- 인덱스 생성
CREATE INDEX idx_llm_config_name ON llm_configurations(config_name);
CREATE INDEX idx_llm_config_created_by ON llm_configurations(created_by);
CREATE INDEX idx_llm_config_updated ON llm_configurations(updated_at DESC);

-- ==============================================
-- 2. messages 테이블 확장
-- ==============================================

-- messages 테이블에 config_id 컬럼 추가
ALTER TABLE messages ADD COLUMN config_id UUID REFERENCES llm_configurations(config_id);

-- 인덱스 추가
CREATE INDEX idx_messages_config_id ON messages(config_id);

-- ==============================================
-- 3. LLM 설정 관리 함수들
-- ==============================================

-- 기본 설정 생성
CREATE OR REPLACE FUNCTION create_default_llm_config()
RETURNS UUID AS $$
DECLARE
    config_id UUID;
    default_prompt TEXT;
BEGIN
    -- 기본 프롬프트 내용
    default_prompt := '# PTSD 심리치료 숙제 지원 에이전트 시스템 프롬프트

## 1. 기본 역할 (Core Role)
당신은 사용자가 일상에서 자신의 감정과 생각을 표현하는 방법을 연습할 수 있도록 돕는 **''대화 연습 파트너''**입니다. 당신의 핵심 임무는 사용자가 상담자 선생님에게 배운 ''이야기하기''와 ''지지 요청하기''를 연습할 때, ''지지적으로 반응하기'' 기술을 활용하여 안전하고 공감적인 대화 상대가 되어주는 것입니다. 당신은 실제 치료사가 아니며, 당신의 역할은 숙제 연습에 한정됩니다.

## 2. 명칭 정의 및 사용자 호칭
- **사용자 (내담자)**: 현재 대화하고 있는 사람입니다. ID가 ''홍길동''이라면, 이름인 ''길동''에 ''님''을 붙여 **"길동님"**이라고 불러주세요. 대화 시 ''당신''이라는 표현은 사용하지 않습니다.
- **상담자 선생님**: 사용자가 실제로 만나는 인간 상담사를 지칭합니다.
- **프로그램**: 본 연구의 전체 과정을 의미합니다.

## 3. 핵심 대화 원칙: 지지적으로 반응하기
사용자가 자신의 생각이나 감정을 이야기할 때, 당신은 아래의 원칙에 따라 반응해야 합니다. 이것이 당신의 가장 중요한 임무입니다.

### 해야 할 일 (Do''s):
- **경청과 지지**: 판단 없이 들어주고, 사용자가 느끼는 모든 감정을 그대로 인정하고 지지합니다. (예: "그런 감정을 느끼시는군요.")
- **시간 제공**: 사용자가 자신의 생각을 정리하고 말할 수 있도록 충분한 시간을 주고, 침묵을 존중합니다.
- **감정의 타당성 인정**: "정말 힘들었겠다.", "무서웠겠다." 와 같이 사용자의 감정이 타당함을 표현해줍니다.
- **공감 표현**: "그 얘기를 들으니 저도 마음이 아프네요." 와 같이 당신의 감정을 나누며 공감할 수 있습니다.
- **도움 제안**: "제가 도와줄 수 있는 부분이 있을까요?" 와 같이 막연하지 않고 구체적인 도움을 제안할 수 있습니다.';

    INSERT INTO llm_configurations (
        config_name, system_prompt, model_name, temperature, max_tokens, 
        top_p, frequency_penalty, presence_penalty, is_active, is_default,
        created_by
    ) VALUES (
        '기본 설정', default_prompt, 'gpt-4.1', 0.5, 1000, 
        0.9, 0.0, 0.0, TRUE, TRUE,
        'admin'
    ) RETURNING llm_configurations.config_id INTO config_id;
    
    RETURN config_id;
END;
$$ LANGUAGE plpgsql;

-- 활성 설정 조회
CREATE OR REPLACE FUNCTION get_active_llm_config()
RETURNS TABLE(
    config_id UUID,
    config_name TEXT,
    system_prompt TEXT,
    model_name TEXT,
    temperature NUMERIC,
    max_tokens INTEGER,
    top_p NUMERIC,
    frequency_penalty NUMERIC,
    presence_penalty NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.config_id, c.config_name, c.system_prompt, c.model_name,
           c.temperature, c.max_tokens, c.top_p, c.frequency_penalty, c.presence_penalty
    FROM llm_configurations c
    WHERE c.is_active = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 모든 설정 조회 (관리자용) - 전체 정보 포함
CREATE OR REPLACE FUNCTION get_all_llm_configs()
RETURNS TABLE(
    config_id UUID,
    config_name TEXT,
    system_prompt TEXT,
    model_name TEXT,
    temperature NUMERIC,
    max_tokens INTEGER,
    top_p NUMERIC,
    frequency_penalty NUMERIC,
    presence_penalty NUMERIC,
    is_active BOOLEAN,
    is_default BOOLEAN,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.config_id, c.config_name, c.system_prompt, c.model_name,
           c.temperature, c.max_tokens, c.top_p, c.frequency_penalty, c.presence_penalty,
           c.is_active, c.is_default, c.created_at
    FROM llm_configurations c
    ORDER BY c.is_active DESC, c.is_default DESC, c.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- 설정 업데이트
CREATE OR REPLACE FUNCTION update_llm_config(
    input_config_id UUID,
    input_system_prompt TEXT,
    input_model_name TEXT,
    input_temperature NUMERIC,
    input_max_tokens INTEGER,
    input_top_p NUMERIC,
    input_frequency_penalty NUMERIC,
    input_presence_penalty NUMERIC
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE llm_configurations SET
        system_prompt = input_system_prompt,
        model_name = input_model_name,
        temperature = input_temperature,
        max_tokens = input_max_tokens,
        top_p = input_top_p,
        frequency_penalty = input_frequency_penalty,
        presence_penalty = input_presence_penalty,
        updated_at = NOW()
    WHERE config_id = input_config_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 활성 설정 변경
CREATE OR REPLACE FUNCTION set_active_llm_config(input_config_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- 기존 활성 설정을 비활성화
    UPDATE llm_configurations SET is_active = FALSE WHERE is_active = TRUE;
    
    -- 새 설정을 활성화
    UPDATE llm_configurations SET is_active = TRUE WHERE config_id = input_config_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 새 설정 생성
CREATE OR REPLACE FUNCTION create_llm_config(
    input_config_name TEXT,
    input_system_prompt TEXT,
    input_model_name TEXT,
    input_temperature NUMERIC,
    input_max_tokens INTEGER,
    input_top_p NUMERIC,
    input_frequency_penalty NUMERIC,
    input_presence_penalty NUMERIC,
    input_created_by TEXT
)
RETURNS UUID AS $$
DECLARE
    new_config_id UUID;
BEGIN
    INSERT INTO llm_configurations (
        config_name, system_prompt, model_name, temperature, max_tokens,
        top_p, frequency_penalty, presence_penalty, created_by
    ) VALUES (
        input_config_name, input_system_prompt, input_model_name, input_temperature, input_max_tokens,
        input_top_p, input_frequency_penalty, input_presence_penalty, input_created_by
    ) RETURNING config_id INTO new_config_id;
    
    RETURN new_config_id;
END;
$$ LANGUAGE plpgsql;

-- 설정 삭제 (기본 설정은 삭제 불가)
CREATE OR REPLACE FUNCTION delete_llm_config(input_config_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    is_default_config BOOLEAN;
    is_active_config BOOLEAN;
BEGIN
    -- 기본 설정 및 활성 설정 확인
    SELECT is_default, is_active INTO is_default_config, is_active_config
    FROM llm_configurations
    WHERE config_id = input_config_id;
    
    -- 기본 설정이거나 활성 설정이면 삭제 불가
    IF is_default_config = TRUE OR is_active_config = TRUE THEN
        RETURN FALSE;
    END IF;
    
    -- 설정 삭제
    DELETE FROM llm_configurations WHERE config_id = input_config_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- save_message 함수 수정 (config_id 포함)
CREATE OR REPLACE FUNCTION save_message_with_config(
    input_session_id TEXT,
    input_role TEXT,
    input_content TEXT,
    input_response_time FLOAT DEFAULT NULL,
    input_config_id UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    msg_id UUID;
    active_config_id UUID;
BEGIN
    -- config_id가 제공되지 않으면 현재 활성 설정 사용
    IF input_config_id IS NULL THEN
        SELECT config_id INTO active_config_id
        FROM llm_configurations
        WHERE is_active = TRUE
        LIMIT 1;
    ELSE
        active_config_id := input_config_id;
    END IF;
    
    INSERT INTO messages (session_id, role, content, response_time_seconds, config_id)
    VALUES (input_session_id, input_role, input_content, input_response_time, active_config_id)
    RETURNING message_id INTO msg_id;
    
    RETURN msg_id;
END;
$$ LANGUAGE plpgsql;

-- ==============================================
-- 4. 수정된 시간 자동 업데이트 트리거
-- ==============================================

-- LLM 설정 수정 시간 자동 업데이트
CREATE OR REPLACE FUNCTION update_llm_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_llm_config_timestamp
    BEFORE UPDATE ON llm_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_llm_config_timestamp();

-- ==============================================
-- 5. 기본 설정 자동 생성
-- ==============================================

-- 기본 설정이 없으면 생성
DO $$
DECLARE
    config_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO config_count FROM llm_configurations;
    
    IF config_count = 0 THEN
        PERFORM create_default_llm_config();
        RAISE NOTICE '기본 LLM 설정이 생성되었습니다.';
    ELSE
        RAISE NOTICE 'LLM 설정이 이미 존재합니다. (총 %개)', config_count;
    END IF;
END $$;

-- ==============================================
-- 6. 테이블 설명
-- ==============================================

COMMENT ON TABLE llm_configurations IS 'LLM 모델 설정 관리 (프롬프트 튜닝)';
COMMENT ON FUNCTION create_default_llm_config IS '기본 LLM 설정 생성';
COMMENT ON FUNCTION get_active_llm_config IS '현재 활성 LLM 설정 조회';
COMMENT ON FUNCTION get_all_llm_configs IS '모든 LLM 설정 조회 (관리자용)';
COMMENT ON FUNCTION update_llm_config IS 'LLM 설정 업데이트';
COMMENT ON FUNCTION set_active_llm_config IS '활성 LLM 설정 변경';
COMMENT ON FUNCTION create_llm_config IS '새 LLM 설정 생성';
COMMENT ON FUNCTION delete_llm_config IS 'LLM 설정 삭제 (기본/활성 설정 제외)';
COMMENT ON FUNCTION save_message_with_config IS '설정 ID와 함께 메시지 저장';