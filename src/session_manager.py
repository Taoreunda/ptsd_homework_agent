"""
세션 지속성 및 대화 메모리 관리 모듈

LangChain 기반 PostgreSQL 백엔드를 활용한 세션 관리 시스템
"""

import os
import uuid
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import psycopg2
from contextlib import contextmanager

from langchain.memory import ConversationSummaryMemory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from utils.logging_config import get_logger

logger = get_logger()


class PostgresChatMessageHistory(BaseChatMessageHistory):
    """PostgreSQL 백엔드 대화 히스토리 저장소"""
    
    def __init__(self, thread_id: str, database_url: str):
        self.thread_id = thread_id
        self.database_url = database_url
        self._messages: List[BaseMessage] = []
        self._loaded = False
    
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
    
    def _load_messages(self):
        """데이터베이스에서 메시지 로드"""
        if self._loaded:
            return
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content, msg_timestamp, message_order, metadata
                    FROM get_conversation_history(%s)
                """, (self.thread_id,))
                
                rows = cursor.fetchall()
                self._messages = []
                
                for role, content, timestamp, order, metadata in rows:
                    if role == 'user':
                        self._messages.append(HumanMessage(content=content))
                    elif role == 'assistant':
                        self._messages.append(AIMessage(content=content))
                
                logger.debug(f"대화 히스토리 로드: {len(self._messages)}개 메시지")
                self._loaded = True
                
        except Exception as e:
            logger.error(f"메시지 로드 실패: {e}")
            self._messages = []
            self._loaded = True
    
    @property
    def messages(self) -> List[BaseMessage]:
        """메시지 목록 반환"""
        self._load_messages()
        return self._messages
    
    def add_message(self, message: BaseMessage) -> None:
        """메시지 추가"""
        self._load_messages()
        
        # 메모리에 추가
        self._messages.append(message)
        
        # 데이터베이스에 저장
        role = 'user' if isinstance(message, HumanMessage) else 'assistant'
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'length': len(message.content)
        }
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT save_conversation_message(%s, %s, %s, %s)
                """, (self.thread_id, role, message.content, json.dumps(metadata)))
                conn.commit()
                
                logger.debug(f"메시지 저장: {role} ({len(message.content)}자)")
                
        except Exception as e:
            logger.error(f"메시지 저장 실패: {e}")
    
    def clear(self) -> None:
        """메시지 히스토리 클리어 (실제로는 스레드 비활성화)"""
        self._messages = []
        self._loaded = False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # 스레드를 비활성화하여 새로운 대화 시작
                cursor.execute("""
                    UPDATE conversation_threads 
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE thread_id = %s
                """, (self.thread_id,))
                conn.commit()
                
                logger.info(f"대화 스레드 클리어: {self.thread_id}")
                
        except Exception as e:
            logger.error(f"스레드 클리어 실패: {e}")


class SessionManager:
    """세션 및 대화 메모리 관리 클래스"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경변수가 필요합니다")
        
        # LangChain 모델 초기화 (요약용)
        self.llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4.1",
            temperature=0.3
        )
    
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
    
    def create_session(self, user_id: str) -> str:
        """새로운 세션 생성"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 새 세션 토큰 생성
                cursor.execute("SELECT create_user_session(%s)", (user_id,))
                session_token = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(f"새 세션 생성: {user_id} -> {session_token}")
                return str(session_token)
                
        except Exception as e:
            logger.error(f"세션 생성 실패: {e}")
            raise
    
    def authenticate_by_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """세션 토큰으로 사용자 인증"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_id, name, group_type, status, phone, gender, age
                    FROM authenticate_by_session(%s)
                """, (session_token,))
                
                result = cursor.fetchone()
                
                if result:
                    user_id, name, group_type, status, phone, gender, age = result
                    
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
                    
                    logger.info(f"세션 인증 성공: {user_id}")
                    return user_info
                else:
                    logger.warning(f"세션 인증 실패: {session_token}")
                    return None
                    
        except Exception as e:
            logger.error(f"세션 인증 중 오류: {e}")
            return None
    
    def get_or_create_thread(self, user_id: str, session_token: str) -> str:
        """활성 대화 스레드 조회 또는 생성"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 기존 활성 스레드 확인
                cursor.execute("SELECT get_active_thread(%s)", (user_id,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    thread_id = str(result[0])
                    logger.debug(f"기존 스레드 사용: {thread_id}")
                    return thread_id
                
                # 새 스레드 생성
                cursor.execute("""
                    SELECT create_conversation_thread(%s, %s)
                """, (user_id, session_token))
                
                thread_id = str(cursor.fetchone()[0])
                conn.commit()
                
                logger.info(f"새 대화 스레드 생성: {user_id} -> {thread_id}")
                return thread_id
                
        except Exception as e:
            logger.error(f"스레드 생성 실패: {e}")
            raise
    
    def create_memory(self, user_id: str, session_token: str, user_name: str) -> ConversationSummaryMemory:
        """사용자별 대화 메모리 생성"""
        try:
            # 대화 스레드 확인/생성
            thread_id = self.get_or_create_thread(user_id, session_token)
            
            # PostgreSQL 백엔드 메시지 히스토리 생성
            chat_history = PostgresChatMessageHistory(
                thread_id=thread_id,
                database_url=self.database_url
            )
            
            # ConversationSummaryMemory 생성
            memory = ConversationSummaryMemory(
                llm=self.llm,
                chat_memory=chat_history,
                memory_key="history",
                return_messages=True,
                max_token_limit=1000,  # 요약 기준 토큰 수
                summary_message_cls=AIMessage
            )
            
            logger.info(f"대화 메모리 생성: {user_name} ({user_id})")
            return memory
            
        except Exception as e:
            logger.error(f"메모리 생성 실패: {e}")
            raise
    
    def cleanup_expired_sessions(self) -> int:
        """만료된 세션 정리"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT cleanup_expired_sessions()")
                cleaned_count = cursor.fetchone()[0]
                conn.commit()
                
                if cleaned_count > 0:
                    logger.info(f"만료된 세션 정리: {cleaned_count}개")
                
                return cleaned_count
                
        except Exception as e:
            logger.error(f"세션 정리 실패: {e}")
            return 0
    
    def get_session_info(self, session_token: str) -> Optional[Dict[str, Any]]:
        """세션 정보 조회"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT us.user_id, us.created_at, us.expires_at, us.last_accessed,
                           p.name, p.group_type
                    FROM user_sessions us
                    JOIN participants p ON us.user_id = p.user_id
                    WHERE us.session_token = %s AND us.is_active = TRUE
                """, (session_token,))
                
                result = cursor.fetchone()
                
                if result:
                    user_id, created_at, expires_at, last_accessed, name, group_type = result
                    return {
                        'user_id': user_id,
                        'name': name,
                        'group_type': group_type,
                        'created_at': created_at.isoformat(),
                        'expires_at': expires_at.isoformat(),
                        'last_accessed': last_accessed.isoformat()
                    }
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"세션 정보 조회 실패: {e}")
            return None


# 전역 인스턴스
_session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    """싱글톤 패턴으로 세션 매니저 반환"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager