-- 중복 메시지 제거 스크립트
-- 동일한 세션에서 같은 내용과 역할을 가진 메시지의 중복을 제거합니다.

-- 1. 중복 메시지 확인 (실행 전 확인용)
SELECT 
    session_id,
    role,
    content,
    COUNT(*) as duplicate_count,
    MIN(timestamp) as first_time,
    MAX(timestamp) as last_time
FROM messages 
GROUP BY session_id, role, content
HAVING COUNT(*) > 1
ORDER BY session_id, role, first_time;

-- 2. 중복 메시지 중 최신 것만 남기고 삭제
-- (주의: 실제 실행 전 백업 권장)
DELETE FROM messages 
WHERE message_id IN (
    SELECT message_id 
    FROM (
        SELECT 
            message_id,
            ROW_NUMBER() OVER (
                PARTITION BY session_id, role, content 
                ORDER BY timestamp DESC, message_order DESC
            ) as rn
        FROM messages
    ) ranked
    WHERE rn > 1
);

-- 3. 삭제 후 확인
SELECT 
    session_id,
    COUNT(*) as total_messages,
    COUNT(DISTINCT content) as unique_messages
FROM messages 
GROUP BY session_id
ORDER BY session_id;

-- 4. 메시지 순서 재정렬 (선택사항)
-- 각 세션의 메시지 순서를 timestamp 기준으로 재정렬
UPDATE messages 
SET message_order = new_order.rn
FROM (
    SELECT 
        message_id,
        ROW_NUMBER() OVER (
            PARTITION BY session_id 
            ORDER BY timestamp ASC
        ) as rn
    FROM messages
) new_order
WHERE messages.message_id = new_order.message_id;

-- 5. 세션 메시지 수 업데이트
UPDATE sessions 
SET total_messages = (
    SELECT COUNT(*) 
    FROM messages 
    WHERE messages.session_id = sessions.session_id
);

-- 완료 메시지
SELECT '중복 메시지 제거 완료' as status;