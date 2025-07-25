"""
PTSD 심리치료 연구용 데이터베이스 관리 모듈

Supabase PostgreSQL과 연동하여 세션 및 메시지 데이터를 저장/조회합니다.
"""

import os
import time
import uuid
import psycopg2
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from utils.logging_config import get_logger

logger = get_logger()


class DatabaseManager:
    """데이터베이스 연결 및 데이터 저장을 관리하는 클래스"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        데이터베이스 매니저 초기화
        
        Args:
            database_url: PostgreSQL 연결 문자열 (환경변수에서 자동 로드)
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다")
            raise ValueError("DATABASE_URL 환경변수가 필요합니다")
        
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                logger.info("데이터베이스 연결 성공")
                return True
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = None
        try:
            conn = psycopg2.connect(self.database_url)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"데이터베이스 오류: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """
        새로운 세션을 생성하고 데이터베이스에 저장
        
        Args:
            user_id: 참가자 ID
            session_id: 세션 ID (없으면 자동 생성)
            
        Returns:
            str: 생성된 세션 ID
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 해당 사용자의 세션 카운트 조회
                cursor.execute(
                    "SELECT COALESCE(MAX(session_count), 0) + 1 FROM sessions WHERE user_id = %s",
                    (user_id,)
                )
                session_count = cursor.fetchone()[0]
                
                # 새 세션 삽입
                cursor.execute("""
                    INSERT INTO sessions (session_id, user_id, start_time, session_count)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE SET
                        start_time = EXCLUDED.start_time,
                        session_count = EXCLUDED.session_count
                """, (session_id, user_id, datetime.now(), session_count))
                
                conn.commit()
                
                logger.info(f"세션 생성: {session_id} (사용자: {user_id}, 세션번호: {session_count})")
                return session_id
                
        except Exception as e:
            logger.error(f"세션 생성 실패: {e}")
            raise
    
    def end_session(self, session_id: str) -> bool:
        """
        세션 종료 시간을 기록
        
        Args:
            session_id: 종료할 세션 ID
            
        Returns:
            bool: 성공 여부
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE sessions 
                    SET end_time = %s 
                    WHERE session_id = %s AND end_time IS NULL
                """, (datetime.now(), session_id))
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"세션 종료: {session_id}")
                    return True
                else:
                    logger.warning(f"종료할 세션을 찾을 수 없음: {session_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"세션 종료 실패: {e}")
            return False
    
    def save_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        response_time_seconds: Optional[float] = None
    ) -> bool:
        """
        메시지를 데이터베이스에 저장
        
        Args:
            session_id: 세션 ID
            role: 메시지 역할 ('user' 또는 'assistant')
            content: 메시지 내용
            response_time_seconds: 응답 시간 (초)
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                message_length = len(content)
                timestamp = datetime.now()
                
                cursor.execute("""
                    INSERT INTO messages 
                    (session_id, role, content, timestamp, message_length, response_time_seconds)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (session_id, role, content, timestamp, message_length, response_time_seconds))
                
                conn.commit()
                
                logger.debug(f"메시지 저장: {role} ({message_length}자) - 세션: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"메시지 저장 실패: {e}")
            return False
    
    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        특정 세션의 모든 메시지 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            List[Dict]: 메시지 리스트
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT role, content, timestamp, message_length, response_time_seconds
                    FROM messages 
                    WHERE session_id = %s 
                    ORDER BY timestamp ASC
                """, (session_id,))
                
                messages = []
                for row in cursor.fetchall():
                    messages.append({
                        'role': row[0],
                        'content': row[1], 
                        'timestamp': row[2],
                        'message_length': row[3],
                        'response_time_seconds': row[4]
                    })
                
                logger.debug(f"세션 메시지 조회: {session_id} ({len(messages)}개)")
                return messages
                
        except Exception as e:
            logger.error(f"세션 메시지 조회 실패: {e}")
            return []
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        특정 사용자의 모든 세션 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            List[Dict]: 세션 리스트
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT session_id, start_time, end_time, total_messages, session_count
                    FROM sessions 
                    WHERE user_id = %s 
                    ORDER BY start_time DESC
                """, (user_id,))
                
                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        'session_id': row[0],
                        'start_time': row[1],
                        'end_time': row[2],
                        'total_messages': row[3],
                        'session_count': row[4]
                    })
                
                logger.debug(f"사용자 세션 조회: {user_id} ({len(sessions)}개)")
                return sessions
                
        except Exception as e:
            logger.error(f"사용자 세션 조회 실패: {e}")
            return []
    
    def get_research_stats(self) -> Dict[str, Any]:
        """
        연구용 전체 통계 조회
        
        Returns:
            Dict: 통계 정보
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 전체 통계 쿼리
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT user_id) as total_users,
                        COUNT(*) as total_sessions,
                        AVG(total_messages) as avg_messages_per_session,
                        SUM(total_messages) as total_messages,
                        MIN(start_time) as first_session,
                        MAX(start_time) as last_session
                    FROM sessions
                """)
                
                row = cursor.fetchone()
                stats = {
                    'total_users': row[0] or 0,
                    'total_sessions': row[1] or 0,
                    'avg_messages_per_session': float(row[2] or 0),
                    'total_messages': row[3] or 0,
                    'first_session': row[4],
                    'last_session': row[5]
                }
                
                # 활성 세션 수 조회
                cursor.execute("SELECT COUNT(*) FROM sessions WHERE end_time IS NULL")
                stats['active_sessions'] = cursor.fetchone()[0] or 0
                
                logger.info(f"연구 통계 조회 완료: {stats['total_users']}명, {stats['total_sessions']}세션")
                return stats
                
        except Exception as e:
            logger.error(f"연구 통계 조회 실패: {e}")
            return {}


class ResponseTimeTracker:
    """사용자 응답 시간을 추적하는 헬퍼 클래스"""
    
    def __init__(self):
        self.last_message_time: Optional[float] = None
    
    def start_timing(self):
        """응답 시간 측정 시작"""
        self.last_message_time = time.time()
    
    def get_response_time(self) -> Optional[float]:
        """응답 시간 계산 (초)"""
        if self.last_message_time is None:
            return None
        
        response_time = time.time() - self.last_message_time
        self.last_message_time = time.time()  # 다음 측정을 위해 리셋
        return response_time


def init_database() -> DatabaseManager:
    """
    데이터베이스 매니저 초기화 및 연결 테스트
    
    Returns:
        DatabaseManager: 초기화된 데이터베이스 매니저
    """
    try:
        db_manager = DatabaseManager()
        logger.info("데이터베이스 초기화 완료")
        return db_manager
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


# 전역 인스턴스 (필요시 사용)
_db_manager: Optional[DatabaseManager] = None

def get_db_manager() -> DatabaseManager:
    """싱글톤 패턴으로 데이터베이스 매니저 반환"""
    global _db_manager
    if _db_manager is None:
        _db_manager = init_database()
    return _db_manager


class ParticipantManager:
    """참가자 인증 및 관리를 위한 클래스"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        참가자 매니저 초기화
        
        Args:
            database_url: PostgreSQL 연결 문자열
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다")
            raise ValueError("DATABASE_URL 환경변수가 필요합니다")
    
    @contextmanager
    def _get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = None
        try:
            conn = psycopg2.connect(self.database_url)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"데이터베이스 오류: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def authenticate_user(self, user_id: str, password: str) -> Optional[Dict[str, Any]]:
        """
        사용자 인증을 수행합니다 (데이터베이스 기반)
        
        Args:
            user_id: 참가자 ID (P001, P002, admin 등)
            password: 비밀번호
            
        Returns:
            Dict: 인증된 사용자 정보 또는 None
        """
        logger.info(f"ParticipantManager.authenticate_user 시작: user_id={user_id}")
        
        try:
            logger.info("데이터베이스 연결 시도...")
            with self._get_connection() as conn:
                logger.info("데이터베이스 연결 성공")
                cursor = conn.cursor()
                
                # authenticate_participant 함수 호출
                logger.info(f"authenticate_participant 함수 호출: user_id={user_id}")
                cursor.execute("""
                    SELECT user_id, name, group_type, status, phone, gender, age
                    FROM authenticate_participant(%s, %s)
                """, (user_id, password))
                
                result = cursor.fetchone()
                logger.info(f"SQL 쿼리 결과: {result}")
                
                if result:
                    user_id, name, group_type, status, phone, gender, age = result
                    logger.info(f"인증 성공 - 사용자 정보: user_id={user_id}, name={name}, group={group_type}, status={status}")
                    
                    user_info = {
                        "user_id": user_id,
                        "user_data": {
                            "name": name,
                            "group": group_type,
                            "status": status,
                            "phone": phone,
                            "gender": gender,
                            "age": age
                        }
                    }
                    
                    logger.info(f"로그인 성공: {user_id} ({name})")
                    return user_info
                else:
                    logger.warning(f"로그인 실패: user_id={user_id} - SQL 결과가 None (사용자 없음 또는 비밀번호 불일치)")
                    return None
                    
        except Exception as e:
            logger.error(f"인증 중 오류: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"상세 오류 정보:\n{traceback.format_exc()}")
            return None
    
    def get_participant_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 참가자의 상세 정보 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            Dict: 참가자 정보 또는 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_id, username, name, group_type, enrolled_date, 
                           session_limit, status, created_at, updated_at
                    FROM participants 
                    WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                
                if result:
                    (user_id, username, name, group_type, enrolled_date, 
                     session_limit, status, created_at, updated_at) = result
                    
                    return {
                        'user_id': user_id,
                        'username': username,
                        'name': name,
                        'group_type': group_type,
                        'enrolled_date': enrolled_date.isoformat() if enrolled_date else None,
                        'session_limit': session_limit,
                        'status': status,
                        'created_at': created_at.isoformat() if created_at else None,
                        'updated_at': updated_at.isoformat() if updated_at else None
                    }
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"참가자 정보 조회 실패: {e}")
            return None
    
    def update_participant_status(self, user_id: str, new_status: str) -> bool:
        """
        참가자 상태 업데이트
        
        Args:
            user_id: 사용자 ID
            new_status: 새로운 상태
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT update_participant_status(%s, %s)", (user_id, new_status))
                success = cursor.fetchone()[0]
                conn.commit()
                
                if success:
                    logger.info(f"참가자 상태 업데이트: {user_id} → {new_status}")
                else:
                    logger.warning(f"참가자 상태 업데이트 실패: {user_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"참가자 상태 업데이트 중 오류: {e}")
            return False
    
    def get_participant_stats(self) -> List[Dict[str, Any]]:
        """
        모든 참가자의 통계 정보 조회
        
        Returns:
            List[Dict]: 참가자별 통계 정보
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_id, username, name, group_type, status, enrolled_date,
                           session_limit, completed_sessions, total_messages, 
                           days_since_last_session, participation_status
                    FROM participant_stats
                    ORDER BY user_id
                """)
                
                stats = []
                for row in cursor.fetchall():
                    (user_id, username, name, group_type, status, enrolled_date,
                     session_limit, completed_sessions, total_messages,
                     days_since_last_session, participation_status) = row
                    
                    stats.append({
                        'user_id': user_id,
                        'username': username,
                        'name': name,
                        'group_type': group_type,
                        'status': status,
                        'enrolled_date': enrolled_date.isoformat() if enrolled_date else None,
                        'session_limit': session_limit,
                        'completed_sessions': completed_sessions or 0,
                        'total_messages': total_messages or 0,
                        'days_since_last_session': float(days_since_last_session) if days_since_last_session else None,
                        'participation_status': participation_status
                    })
                
                logger.debug(f"참가자 통계 조회: {len(stats)}명")
                return stats
                
        except Exception as e:
            logger.error(f"참가자 통계 조회 실패: {e}")
            return []
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        연구 전체 요약 통계 조회
        
        Returns:
            Dict: 전체 통계 정보
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM get_participant_summary()")
                result = cursor.fetchone()
                
                if result:
                    (total_participants, active_participants, treatment_group,
                     control_group, completed_participants, dropout_participants,
                     avg_sessions_per_participant) = result
                    
                    return {
                        'total_participants': total_participants,
                        'active_participants': active_participants,
                        'treatment_group': treatment_group,
                        'control_group': control_group,
                        'completed_participants': completed_participants,
                        'dropout_participants': dropout_participants,
                        'avg_sessions_per_participant': float(avg_sessions_per_participant or 0)
                    }
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"요약 통계 조회 실패: {e}")
            return {}


    def add_participant(
        self, 
        user_id: str, 
        password: str, 
        name: str, 
        group_type: str,
        phone: str = None,
        gender: str = None,
        age: int = None
    ) -> bool:
        """
        새 참가자 추가
        
        Args:
            user_id: 참가자 ID
            password: 비밀번호
            name: 이름
            group_type: 그룹 ('treatment', 'control')
            phone: 전화번호
            gender: 성별
            age: 나이
            
        Returns:
            bool: 추가 성공 여부
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT add_participant(%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, password, name, group_type, phone, gender, age))
                
                success = cursor.fetchone()[0]
                conn.commit()
                
                if success:
                    logger.info(f"참가자 추가 성공: {user_id} ({name})")
                else:
                    logger.warning(f"참가자 추가 실패: {user_id} (중복 또는 유효성 검사 실패)")
                
                return success
                
        except Exception as e:
            logger.error(f"참가자 추가 중 오류: {e}")
            return False


# 전역 인스턴스
_participant_manager: Optional[ParticipantManager] = None

def get_participant_manager() -> ParticipantManager:
    """싱글톤 패턴으로 참가자 매니저 반환"""
    global _participant_manager
    if _participant_manager is None:
        logger.info("새로운 ParticipantManager 인스턴스 생성 중...")
        database_url = os.getenv("DATABASE_URL")
        logger.info(f"DATABASE_URL 환경변수: {'설정됨' if database_url else '설정되지 않음'}")
        if database_url:
            logger.info(f"DATABASE_URL 시작 부분: {database_url[:50]}...")
        _participant_manager = ParticipantManager()
        logger.info("ParticipantManager 인스턴스 생성 완료")
    return _participant_manager