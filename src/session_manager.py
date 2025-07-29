"""
세션 관리 모듈

essential_schema.sql 기반 세션 및 대화 메모리 관리
"""

import os
import uuid
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import psycopg2
from contextlib import contextmanager

from langchain.memory import ConversationBufferMemory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from .database import DatabaseMixin
from utils.logging_config import get_logger

logger = get_logger()


class PostgresChatHistory(BaseChatMessageHistory, DatabaseMixin):
    """PostgreSQL 기반 대화 히스토리"""
    
    def __init__(self, session_id: str, database_url: str):
        DatabaseMixin.__init__(self, database_url)
        self.session_id = session_id
        self._messages: List[BaseMessage] = []
        self._loaded = False
    
    def _load_messages(self):
        """데이터베이스에서 메시지 로드"""
        if self._loaded:
            return
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content, msg_timestamp, message_order
                    FROM get_session_messages(%s)
                """, (self.session_id,))
                
                rows = cursor.fetchall()
                self._messages = []
                
                for role, content, msg_timestamp, order in rows:
                    if role == 'user':
                        self._messages.append(HumanMessage(content=content))
                    elif role == 'assistant':
                        self._messages.append(AIMessage(content=content))
                
                logger.debug(f"세션 {self.session_id}: {len(self._messages)}개 메시지 로드")
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
    
    def add_message(self, message: BaseMessage, response_time: float = None) -> None:
        """메시지 추가"""
        self._load_messages()
        
        # 메모리에 추가
        self._messages.append(message)
        
        # 데이터베이스에 저장
        role = 'user' if isinstance(message, HumanMessage) else 'assistant'
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 메시지 저장
                cursor.execute("""
                    SELECT save_message(%s, %s, %s, %s)
                """, (self.session_id, role, message.content, response_time))
                
                # 세션 활성 상태 갱신 (대화 중 세션 유지)
                cursor.execute("""
                    UPDATE sessions 
                    SET last_accessed = NOW(), total_messages = total_messages + 1
                    WHERE session_id = %s AND is_active = TRUE
                """, (self.session_id,))
                
                conn.commit()
                
                logger.debug(f"메시지 저장 및 세션 갱신: {role} ({len(message.content)}자) - 응답시간: {response_time}초")
                
        except Exception as e:
            logger.error(f"메시지 저장 실패: {e}")
    
    def clear(self) -> None:
        """메시지 히스토리 클리어"""
        self._messages = []
        self._loaded = False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # 세션 종료
                cursor.execute("SELECT end_session(%s)", (self.session_id,))
                conn.commit()
                
                logger.info(f"세션 클리어: {self.session_id}")
                
        except Exception as e:
            logger.error(f"세션 클리어 실패: {e}")


class SessionManager(DatabaseMixin):
    """세션 관리 클래스"""
    
    def __init__(self, database_url: Optional[str] = None):
        super().__init__(database_url)
        
        # LangChain 모델 초기화 (요약용)
        self.llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
            temperature=0.3
        )
    
    def create_session(self, user_id: str) -> str:
        """기존 활성 세션 조회 또는 새 세션 생성"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 먼저 기존 활성 세션 확인
                cursor.execute("""
                    SELECT session_id, session_token
                    FROM sessions
                    WHERE user_id = %s AND is_active = TRUE
                    ORDER BY last_accessed DESC
                    LIMIT 1
                """, (user_id,))
                
                existing_session = cursor.fetchone()
                
                if existing_session:
                    # 기존 세션이 있으면 마지막 접근 시간 업데이트 후 반환
                    session_id, session_token = existing_session
                    cursor.execute("""
                        UPDATE sessions 
                        SET last_accessed = NOW()
                        WHERE session_id = %s
                    """, (session_id,))
                    conn.commit()
                    
                    logger.info(f"기존 세션 재사용: {user_id} -> {session_id} (토큰: {session_token})")
                    return str(session_token)
                
                # 기존 세션이 없으면 새 세션 생성
                cursor.execute("SELECT * FROM create_session_with_token(%s)", (user_id,))
                result = cursor.fetchone()
                session_id, session_token = result
                conn.commit()
                
                logger.info(f"새 세션 생성: {user_id} -> {session_id} (토큰: {session_token})")
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
                    SELECT user_id, session_id, name, group_type, status, phone, gender, age
                    FROM authenticate_by_token(%s)
                """, (session_token,))
                
                result = cursor.fetchone()
                
                if result:
                    user_id, session_id, name, group_type, status, phone, gender, age = result
                    
                    user_info = {
                        "user_id": user_id,
                        "session_id": session_id,  # 실제 세션 ID 포함
                        "user_data": {
                            "name": name,
                            "group": group_type,
                            "status": status,
                            "phone": phone,
                            "gender": gender,
                            "age": age
                        }
                    }
                    
                    logger.info(f"토큰 인증 성공: {user_id}")
                    return user_info
                else:
                    logger.warning(f"토큰 인증 실패 (만료/무효/비활성): {session_token}")
                    return None
                    
        except Exception as e:
            logger.error(f"토큰 인증 중 오류: {e}")
            return None
    
    def create_memory(self, user_id: str, session_token: str, user_name: str, session_id: str = None) -> ConversationBufferMemory:
        """사용자별 대화 메모리 생성"""
        try:
            # 세션 ID가 제공되지 않은 경우에만 토큰으로 조회 (중복 인증 방지)
            if not session_id:
                user_info = self.authenticate_by_session(session_token)
                if not user_info:
                    raise ValueError(f"유효하지 않은 세션 토큰: {session_token}")
                session_id = user_info["session_id"]
            
            # PostgreSQL 백엔드 메시지 히스토리 생성
            chat_history = PostgresChatHistory(
                session_id=session_id,
                database_url=self.database_url
            )
            
            # ConversationBufferMemory 생성 (요약 없이 단순하게)
            memory = ConversationBufferMemory(
                chat_memory=chat_history,
                memory_key="history",
                return_messages=True
            )
            
            logger.info(f"대화 메모리 생성: {user_name} ({user_id}) - 세션: {session_id}")
            return memory
            
        except Exception as e:
            logger.error(f"메모리 생성 실패: {e}")
            raise
    
    def cleanup_expired_sessions(self) -> int:
        """만료된 세션 정리"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT cleanup_inactive_sessions()")
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
        return self.authenticate_by_session(session_token)


# 전역 인스턴스
_session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    """싱글톤 패턴으로 세션 매니저 반환"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager