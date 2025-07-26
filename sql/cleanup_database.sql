-- 데이터베이스 완전 정리 스크립트
-- 모든 기존 테이블, 함수, 뷰, 트리거를 삭제하고 깨끗하게 시작

-- ==============================================
-- 1. 기존 테이블 모두 삭제 (CASCADE로 의존성까지)
-- ==============================================

-- 복잡한 새 시스템 테이블들 삭제
DROP TABLE IF EXISTS conversation_messages CASCADE;
DROP TABLE IF EXISTS conversation_threads CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;

-- 기존 테이블들 삭제
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;

-- 메타데이터 테이블 삭제
DROP TABLE IF EXISTS schema_version CASCADE;

-- 참가자 테이블도 삭제 (완전 재생성)
DROP TABLE IF EXISTS participants CASCADE;

-- ==============================================
-- 2. 기존 함수들 모두 삭제
-- ==============================================

-- 세션 관리 함수들
DROP FUNCTION IF EXISTS create_user_session(TEXT) CASCADE;
DROP FUNCTION IF EXISTS authenticate_by_session(UUID) CASCADE;
DROP FUNCTION IF EXISTS create_conversation_thread(TEXT, UUID) CASCADE;
DROP FUNCTION IF EXISTS save_conversation_message(UUID, TEXT, TEXT, JSONB) CASCADE;
DROP FUNCTION IF EXISTS get_conversation_history(UUID) CASCADE;
DROP FUNCTION IF EXISTS get_active_thread(TEXT) CASCADE;
DROP FUNCTION IF EXISTS cleanup_expired_sessions() CASCADE;

-- 기존 분석 함수들
DROP FUNCTION IF EXISTS calculate_dropout_risk(TEXT) CASCADE;
DROP FUNCTION IF EXISTS archive_old_sessions(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS get_research_summary() CASCADE;

-- 참가자 관리 함수들
DROP FUNCTION IF EXISTS authenticate_participant(TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS add_participant(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, INTEGER) CASCADE;

-- 트리거 함수들
DROP FUNCTION IF EXISTS update_session_message_count() CASCADE;
DROP FUNCTION IF EXISTS calculate_message_length() CASCADE;
DROP FUNCTION IF EXISTS set_message_order() CASCADE;

-- 새로 만들어질 함수들도 미리 삭제 (에러 방지)
DROP FUNCTION IF EXISTS create_session_with_token(TEXT) CASCADE;
DROP FUNCTION IF EXISTS authenticate_by_token(UUID) CASCADE;
DROP FUNCTION IF EXISTS save_message(TEXT, TEXT, TEXT, FLOAT) CASCADE;
DROP FUNCTION IF EXISTS end_session(TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_session_messages(TEXT) CASCADE;
DROP FUNCTION IF EXISTS cleanup_inactive_sessions() CASCADE;
DROP FUNCTION IF EXISTS migrate_from_complex_tables() CASCADE;

-- ==============================================
-- 3. 기존 뷰들 모두 삭제
-- ==============================================

DROP VIEW IF EXISTS user_session_stats CASCADE;
DROP VIEW IF EXISTS daily_activity_stats CASCADE;
DROP VIEW IF EXISTS message_analysis CASCADE;
DROP VIEW IF EXISTS participant_summary CASCADE;
DROP VIEW IF EXISTS user_session_summary CASCADE;
DROP VIEW IF EXISTS daily_activity CASCADE;

-- ==============================================
-- 4. 기존 트리거들 삭제 (테이블 삭제로 자동 삭제되지만 명시적으로)
-- ==============================================

-- 트리거들은 테이블 삭제시 자동 삭제되므로 별도 명시 불필요

-- ==============================================
-- 5. 확장 기능 및 타입 정리
-- ==============================================

-- UUID 확장은 시스템에서 사용할 수 있으므로 유지
-- DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;

-- ==============================================
-- 6. 정리 완료 확인
-- ==============================================

DO $$
DECLARE
    table_count INTEGER;
    function_count INTEGER;
    view_count INTEGER;
BEGIN
    -- 남은 테이블 수 확인 (시스템 테이블 제외)
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
    
    -- 남은 함수 수 확인 (시스템 함수 제외)
    SELECT COUNT(*) INTO function_count
    FROM information_schema.routines 
    WHERE routine_schema = 'public' 
    AND routine_type = 'FUNCTION';
    
    -- 남은 뷰 수 확인
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views 
    WHERE table_schema = 'public';
    
    RAISE NOTICE '=== 데이터베이스 정리 완료 ===';
    RAISE NOTICE '남은 테이블: %개', table_count;
    RAISE NOTICE '남은 함수: %개', function_count;
    RAISE NOTICE '남은 뷰: %개', view_count;
    RAISE NOTICE '===========================';
    
    IF table_count = 0 AND function_count = 0 AND view_count = 0 THEN
        RAISE NOTICE '✅ 데이터베이스가 완전히 정리되었습니다.';
        RAISE NOTICE '이제 simplified_schema.sql을 실행하세요.';
    ELSE
        RAISE NOTICE '⚠️  일부 객체가 남아있습니다. 수동 확인이 필요할 수 있습니다.';
    END IF;
END $$;