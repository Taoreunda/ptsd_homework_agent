import streamlit as st
from operator import itemgetter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
import os
from utils.logging_config import get_logger
from dotenv import load_dotenv
import extra_streamlit_components as stx
from datetime import datetime, timedelta
from src.database import DatabaseManager, ResponseTimeTracker, get_participant_manager
from src.session_manager import get_session_manager
from src.admin_pages import render_admin_sidebar, render_admin_page
from src.ui_styles import (
    configure_page_settings, apply_mobile_optimized_css,
    apply_chat_interface_styles, apply_login_page_styles
)

load_dotenv()

# 로거 설정
logger = get_logger()

# 페이지 설정 및 기본 스타일 적용
configure_page_settings()
apply_mobile_optimized_css()  # 기본 모바일 최적화 스타일만 적용

# CookieManager 초기화 (세션 상태로 관리)
if "cookie_manager" not in st.session_state:
    st.session_state.cookie_manager = stx.CookieManager()

cookie_manager = st.session_state.cookie_manager


# 쿠키 관리 유틸리티 함수들
def save_session_cookie(session_token: str) -> None:
    """세션 토큰을 쿠키에 저장합니다."""
    try:
        expires_at = datetime.now() + timedelta(days=7)
        cookie_manager.set('session_token', session_token, expires_at=expires_at)
        logger.info(f"세션 토큰 쿠키 저장 완료: {session_token[:8]}... (만료: {expires_at})")
    except Exception as e:
        logger.error(f"쿠키 저장 실패: {e}")

def remove_session_cookie() -> None:
    """세션 토큰 쿠키를 제거합니다."""
    try:
        cookie_manager.delete('session_token')
        logger.debug("세션 토큰 쿠키 제거 완료")
    except Exception as e:
        logger.warning(f"쿠키 제거 실패: {e}")

def initialize_session_managers() -> None:
    """세션 관련 매니저들을 초기화합니다."""
    st.session_state.db_manager = DatabaseManager()
    st.session_state.participant_manager = get_participant_manager()


# 유틸리티 함수들
def load_participants():
    """참가자 정보를 데이터베이스에서 로드합니다."""
    try:
        participant_manager = get_participant_manager()
        participants_stats = participant_manager.get_participant_stats()
        
        # 기존 형식으로 변환 (하위 호환성)
        participants = {}
        for participant in participants_stats:
            user_id = participant['user_id']
            participants[user_id] = {
                "name": participant['name'],
                "group": participant['group_type'],
                "status": participant['status']
            }
        
        logger.info(f"참가자 정보 로드 완료: {len(participants)}명 (데이터베이스)")
        return participants
    except Exception as e:
        logger.error(f"참가자 정보 로드 실패: {e}")
        return {}

def load_prompt(file_path: str) -> str:
    """파일 경로에서 프롬프트 내용을 읽어옵니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.debug(f"프롬프트 파일 로드 성공: {file_path}")
            return content
    except FileNotFoundError as e:
        logger.error(f"프롬프트 파일을 찾을 수 없음: {file_path}, 오류: {e}")
        return "프롬프트 파일을 찾을 수 없습니다."

def _load_active_llm_config():
    """데이터베이스에서 활성 LLM 설정을 로드합니다."""
    logger.debug("활성 LLM 설정 로드 시작...")
    
    try:
        # 데이터베이스 매니저가 있는 경우에만 시도
        if hasattr(st.session_state, 'db_manager') and st.session_state.db_manager:
            logger.debug("데이터베이스 매니저 확인 완료, 설정 조회 중...")
            with st.session_state.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM get_active_llm_config()")
                result = cursor.fetchone()
                
                if result:
                    config = {
                        'config_id': result[0],
                        'config_name': result[1], 
                        'system_prompt': result[2],
                        'model_name': result[3],
                        'temperature': float(result[4]),
                        'max_tokens': result[5],
                        'top_p': float(result[6]),
                        'frequency_penalty': float(result[7]),
                        'presence_penalty': float(result[8])
                    }
                    logger.info(f"데이터베이스에서 LLM 설정 로드 성공: {config['config_name']} (ID: {config['config_id']})")
                    return config
                else:
                    logger.warning("데이터베이스에 활성 LLM 설정이 없음")
        else:
            logger.debug("데이터베이스 매니저가 없음, 기본값 사용")
    except Exception as e:
        logger.warning(f"데이터베이스 LLM 설정 로드 실패, 기본값 사용: {e}")
    
    # 데이터베이스 연결 실패시 기본값 반환
    logger.info("기본 LLM 설정 사용")
    return {
        'model_name': 'gpt-4.1',
        'temperature': 0.5,
        'max_tokens': 1000,
        'top_p': 0.9,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0,
        'system_prompt': None  # 파일에서 로드하도록 None 반환
    }

def authenticate_user(user_id: str, password: str) -> dict:
    """사용자 인증을 수행합니다 (데이터베이스 기반)."""
    logger.info(f"인증 시도: user_id={user_id}")
    
    try:
        # ParticipantManager 인스턴스 생성 시도
        logger.info("ParticipantManager 인스턴스 생성 중...")
        participant_manager = get_participant_manager()
        logger.info("ParticipantManager 인스턴스 생성 완료")
        
        # 인증 시도
        logger.info(f"데이터베이스 인증 시작: user_id={user_id}")
        auth_result = participant_manager.authenticate_user(user_id, password)
        logger.info(f"데이터베이스 인증 결과: {auth_result is not None}")
        
        if auth_result:
            logger.info(f"로그인 성공: {auth_result['user_id']} ({auth_result['user_data']['name']})")
            logger.info(f"사용자 데이터: {auth_result['user_data']}")
            return auth_result
        else:
            logger.warning(f"로그인 실패: user_id={user_id} - 인증 결과가 None")
            return None
    except Exception as e:
        logger.error(f"인증 중 오류 발생: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"상세 오류 정보:\n{traceback.format_exc()}")
        return None

def setup_model_and_chain(user_name: str, memory: ConversationBufferMemory):
    """OpenAI 모델 및 대화 체인을 설정합니다."""
    
    # 데이터베이스에서 활성 LLM 설정 로드
    llm_config = _load_active_llm_config()
    
    # LLM 설정 로깅
    logger.info(f"=== LLM 설정 적용 ===")
    logger.info(f"모델: {llm_config.get('model_name', 'gpt-4.1')}")
    logger.info(f"Temperature: {llm_config.get('temperature', 0.5)}")
    logger.info(f"Max Tokens: {llm_config.get('max_tokens', 1000)}")
    logger.info(f"Top P: {llm_config.get('top_p', 0.9)}")
    logger.info(f"Frequency Penalty: {llm_config.get('frequency_penalty', 0.0)}")
    logger.info(f"Presence Penalty: {llm_config.get('presence_penalty', 0.0)}")
    
    # OpenAI 모델 생성 (비동기 스트리밍 지원)
    model = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),  
        model=llm_config.get('model_name', 'gpt-4.1'),
        temperature=llm_config.get('temperature', 0.5),
        max_tokens=llm_config.get('max_tokens', 1000),
        top_p=llm_config.get('top_p', 0.9),
        frequency_penalty=llm_config.get('frequency_penalty', 0.0),
        presence_penalty=llm_config.get('presence_penalty', 0.0),
        streaming=True  # 스트리밍은 항상 활성화
    )
    
    # 프롬프트 설정 (데이터베이스 설정 우선, 파일 백업)
    if llm_config.get('system_prompt'):
        system_prompt_template = llm_config['system_prompt']
        logger.info(f"시스템 프롬프트 소스: 데이터베이스 (설정 ID: {llm_config.get('config_id', 'N/A')})")
    else:
        system_prompt_template = load_prompt("prompts/therapy_system_prompt.md")
        logger.info(f"시스템 프롬프트 소스: 파일 (prompts/therapy_system_prompt.md)")
    
    system_prompt = system_prompt_template.replace("길동님", f"{user_name}님")
    
    # 시스템 프롬프트 내용 로깅 (처음 200자만)
    prompt_preview = system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt
    logger.info(f"적용된 시스템 프롬프트 (처음 200자): {prompt_preview}")
    logger.info(f"시스템 프롬프트 전체 길이: {len(system_prompt)}자")
    logger.info(f"사용자명 치환: 길동님 → {user_name}님")
    logger.info("=====================")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])
    
    # 실행 체인 구성 (LangChain 비동기 스트리밍 지원)
    runnable = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        )
        | prompt
        | model
        | StrOutputParser()
    )
    
    return runnable

def response_generator(runnable, question: str):
    """응답 생성 함수 (LangChain 스트리밍 방식)"""
    try:
        # runnable이 None인지 확인
        if runnable is None:
            logger.error("runnable이 None입니다. 체인을 다시 초기화해야 합니다.")
            yield "죄송합니다. 시스템을 초기화하는 중입니다. 잠시 후 다시 시도해주세요."
            return
            
        # LangChain의 동기 스트리밍 사용 (Streamlit 호환)
        for chunk in runnable.stream({"question": question}):
            # 응답 텍스트 추출
            if isinstance(chunk, dict) and "answer" in chunk:
                yield chunk["answer"]
            elif isinstance(chunk, str):
                yield chunk
            else:
                # 기타 chunk 형태 처리
                yield str(chunk)
    except Exception as e:
        logger.error(f"응답 생성 중 오류: {e}")
        yield "죄송합니다. 응답 생성 중 오류가 발생했습니다."

def load_chat_history_to_ui(memory):
    """메모리에서 대화 내용을 불러와 UI에 표시"""
    try:
        if memory and hasattr(memory, 'chat_memory'):
            chat_messages = memory.chat_memory.messages
            
            # 기존 대화가 있는 경우에만 UI 메시지를 로드
            if chat_messages:
                new_messages = []
                
                for message in chat_messages:
                    if hasattr(message, 'content') and message.content.strip():
                        if message.__class__.__name__ == 'HumanMessage':
                            new_messages.append({
                                "role": "user", 
                                "content": message.content
                            })
                        elif message.__class__.__name__ == 'AIMessage':
                            new_messages.append({
                                "role": "assistant", 
                                "content": message.content
                            })
                
                # 실제로 메시지가 있는 경우에만 UI 업데이트
                if new_messages:
                    st.session_state.messages = new_messages
                    logger.info(f"대화 기록 UI 복원: {len(new_messages)}개 메시지")
                else:
                    logger.debug("복원할 대화 기록이 없음 (빈 메시지)")
            else:
                logger.debug("복원할 대화 기록이 없음 (메시지 없음)")
                
    except Exception as e:
        logger.error(f"대화 기록 UI 복원 실패: {e}")
        # 오류 시에만 messages 초기화
        if "messages" not in st.session_state:
            st.session_state.messages = []

def _render_chat_interface(user_name: str, user_id: str):
    """대화 인터페이스를 렌더링합니다."""
    apply_chat_interface_styles()  # 채팅 인터페이스 전용 스타일 적용
    
    # 시작 메시지 초기화 (처음 로그인 시, 기존 대화가 없는 경우만)
    if not st.session_state.messages:
        start_message = f"{user_name}님, 안녕하세요. 오늘 어떤 이야기를 해보고 싶으신가요?"
        st.session_state.messages.append({"role": "assistant", "content": start_message})
    
    # 대화 기록 표시 (Streamlit 표준 방식)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 사용자 입력 처리 (Streamlit 표준 채팅 UI 패턴)
    if prompt := st.chat_input("메시지를 입력하세요..."):
        # 응답 시간 계산
        response_time = st.session_state.response_tracker.get_response_time()
        
        # 사용자 메시지를 세션 상태 및 메모리에 추가 (응답 시간 포함)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.memory.chat_memory.add_message(HumanMessage(content=prompt), response_time)
        
        # 사용자 메시지 표시
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 응답 시간 추적 시작
        st.session_state.response_tracker.start_timing()
        
        # runnable이 None인 경우 재생성
        if st.session_state.runnable is None:
            logger.warning("runnable이 None입니다. 다시 생성합니다...")
            user_name = st.session_state.user_info.get("name", "사용자")
            st.session_state.runnable = setup_model_and_chain(user_name, st.session_state.memory)
            logger.info("runnable 재생성 완료")
        
        # AI 응답 생성 및 스트리밍 표시 (Streamlit 표준 방식)
        with st.chat_message("assistant"):
            response = st.write_stream(
                response_generator(st.session_state.runnable, prompt)
            )
            
            # AI 응답 시간 계산
            ai_response_time = st.session_state.response_tracker.get_response_time()
            
            # 로깅
            logger.info(f"AI 응답 완료: {user_id} - 사용자 메시지: {len(prompt)}자, AI 응답: {len(response)}자, 응답시간: {ai_response_time:.1f}초")
        
        # AI 응답을 세션 상태 및 메모리에 추가 (응답 시간 포함)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.memory.chat_memory.add_message(AIMessage(content=response), ai_response_time)
        
        # 다음 사용자 응답을 위한 시간 추적 시작
        st.session_state.response_tracker.start_timing()

async def async_response_generator(runnable, question: str):
    """비동기 응답 생성 함수 (LangChain astream 사용)"""
    try:
        # LangChain의 비동기 스트리밍 사용
        async for chunk in runnable.astream({"question": question}):
            # 응답 텍스트 추출
            if isinstance(chunk, dict) and "answer" in chunk:
                yield chunk["answer"]
            elif isinstance(chunk, str):
                yield chunk
            else:
                # 기타 chunk 형태 처리
                yield str(chunk)
    except Exception as e:
        logger.error(f"비동기 응답 생성 중 오류: {e}")
        yield "죄송합니다. 응답 생성 중 오류가 발생했습니다."

# --- 세션 상태 초기화 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "session_token" not in st.session_state:
    st.session_state.session_token = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "runnable" not in st.session_state:
    st.session_state.runnable = None
if "db_manager" not in st.session_state:
    st.session_state.db_manager = None
if "response_tracker" not in st.session_state:
    st.session_state.response_tracker = ResponseTimeTracker()
if "participant_manager" not in st.session_state:
    st.session_state.participant_manager = None
if "session_manager" not in st.session_state:
    st.session_state.session_manager = None

# --- 자동 세션 복원 시도 ---
if not st.session_state.authenticated:
    session_token = None
    
    # 1순위: 쿠키에서 세션 토큰 확인
    try:
        cookie_token = cookie_manager.get('session_token')
        if cookie_token:
            session_token = cookie_token
            logger.info(f"쿠키에서 세션 토큰 발견: {session_token[:8]}...")
        else:
            logger.debug("쿠키에서 session_token을 찾을 수 없음")
    except Exception as e:
        logger.error(f"쿠키 확인 중 오류: {e}")
    
    # 2순위: URL 파라미터에서 세션 토큰 확인 (쿠키가 없는 경우)
    if not session_token:
        query_params = st.query_params
        if "session_token" in query_params and not st.session_state.session_token:
            session_token = query_params["session_token"]
            logger.info(f"URL에서 세션 토큰 발견: {session_token[:8]}...")
    
    # 세션 토큰이 있으면 복원 시도
    if session_token and not st.session_state.session_token:
        
        try:
            session_manager = get_session_manager()
            user_info = session_manager.authenticate_by_session(session_token)
            
            if user_info:
                # 자동 로그인 성공
                st.session_state.authenticated = True
                st.session_state.user_info = user_info
                st.session_state.session_token = session_token
                st.session_state.session_manager = session_manager
                
                # 데이터베이스 초기화
                initialize_session_managers()
                
                # 세션 ID 복원 (토큰에서)
                st.session_state.session_id = user_info["session_id"]
                
                # 대화 메모리 복원 (session_id 직접 전달하여 중복 인증 방지)
                st.session_state.memory = session_manager.create_memory(
                    user_info["user_id"],
                    session_token,
                    user_info["user_data"]["name"],
                    user_info["session_id"]
                )
                
                # 대화 기록을 UI에 로드
                load_chat_history_to_ui(st.session_state.memory)
                
                # 모델 체인 설정
                st.session_state.runnable = setup_model_and_chain(
                    user_info["user_data"]["name"],
                    st.session_state.memory
                )
                
                # 응답 시간 추적 시작
                st.session_state.response_tracker.start_timing()
                
                # 쿠키에 세션 토큰 저장
                save_session_cookie(session_token)
                
                logger.info(f"자동 세션 복원 성공: {user_info['user_id']}")
                st.rerun()
            else:
                logger.warning(f"세션 토큰 인증 실패 (만료/무효): {session_token}")
                # URL에서 잘못된 토큰 제거
                st.query_params.clear()
                # 쿠키에서도 만료된 토큰 제거
                remove_session_cookie()
                # 만료 메시지 표시
                st.warning("⏰ 세션이 만료되었습니다. 다시 로그인해 주세요.")
                
        except Exception as e:
            logger.error(f"자동 세션 복원 실패: {e}")
            # 문제가 있는 쿠키도 제거
            remove_session_cookie()
            st.error("🔗 세션 복원 중 오류가 발생했습니다. 다시 로그인해 주세요.")

# --- 인증 처리 ---
if not st.session_state.authenticated:
    apply_login_page_styles()  # 로그인 페이지 전용 스타일 적용
    st.subheader("🔐 로그인")
    
    with st.form("login_form"):
        user_id = st.text_input("참가자 ID")
        password = st.text_input("비밀번호", type="password")
        login_button = st.form_submit_button("로그인")
        
        if login_button:
            if user_id and password:
                logger.info(f"로그인 버튼 클릭: user_id={user_id}")
                st.info("로그인 처리 중...")
                auth_result = authenticate_user(user_id, password)
                logger.info(f"authenticate_user 반환값: {auth_result}")
                if auth_result:
                    st.session_state.authenticated = True
                    st.session_state.user_info = auth_result
                    
                    # 세션 관리자 및 데이터베이스 초기화
                    try:
                        st.session_state.session_manager = get_session_manager()
                        initialize_session_managers()
                        
                        # 새 세션 토큰 생성 (단순화된 방식)
                        st.session_state.session_token = st.session_state.session_manager.create_session(
                            auth_result["user_id"]
                        )
                        
                        # 세션 ID는 이미 생성된 토큰에서 직접 획득 (중복 인증 방지)
                        # create_session이 토큰을 반환하므로, 별도 인증 없이 메모리 생성에서 처리
                        
                        # 토큰으로 세션 정보 획득 (session_id 필요)
                        session_info = st.session_state.session_manager.authenticate_by_session(
                            st.session_state.session_token
                        )
                        st.session_state.session_id = session_info["session_id"]
                        
                        # 대화 메모리 생성 (session_id 직접 전달하여 중복 인증 방지)
                        st.session_state.memory = st.session_state.session_manager.create_memory(
                            auth_result["user_id"],
                            st.session_state.session_token,
                            auth_result["user_data"]["name"],
                            st.session_state.session_id
                        )
                        
                        # 대화 기록을 UI에 로드 (기존 세션이 있는 경우)
                        load_chat_history_to_ui(st.session_state.memory)
                        
                        # URL에 세션 토큰 추가 (브라우저 새로고침 대응)
                        st.query_params.update({"session_token": st.session_state.session_token})
                        
                        # 쿠키에 세션 토큰 저장
                        save_session_cookie(st.session_state.session_token)
                        
                        logger.info(f"새 세션 생성: {auth_result['user_id']} -> {st.session_state.session_token}")
                        
                    except Exception as e:
                        logger.error(f"세션 초기화 실패: {e}")
                        st.error("세션 생성에 실패했습니다. 관리자에게 문의하세요.")
                        st.stop()
                    
                    # 모델 및 체인 설정
                    st.session_state.runnable = setup_model_and_chain(
                        auth_result["user_data"]["name"],
                        st.session_state.memory
                    )
                    
                    # 응답 시간 추적 시작
                    st.session_state.response_tracker.start_timing()
                    
                    st.success(f"환영합니다, {auth_result['user_data']['name']}님!")
                    st.rerun()
                else:
                    st.error("로그인에 실패했습니다. 참가자 ID와 비밀번호를 확인해주세요.")
            else:
                st.error("참가자 ID와 비밀번호를 입력해주세요.")

else:
    # --- 인증된 사용자 대화 인터페이스 ---
    user_name = st.session_state.user_info["user_data"]["name"]
    user_id = st.session_state.user_info["user_id"]
    user_group = st.session_state.user_info["user_data"]["group"]
    
    # 관리자인 경우 관리자 스타일 적용
    if user_group == "admin":
        from src.ui_styles import apply_admin_page_styles
        apply_admin_page_styles()
    
    # 사이드바에 사용자 정보
    with st.sidebar:
        st.subheader("👤 사용자 정보")
        st.write(f"**이름:** {user_name}")
        st.write(f"**ID:** {user_id}")
        
        # 관리자 전용 메뉴
        if user_group == "admin":
            render_admin_sidebar()
        
        st.markdown("---")
        if st.button("로그아웃"):
            # 세션 종료 처리
            if st.session_state.db_manager and st.session_state.session_id:
                success = st.session_state.db_manager.end_session(st.session_state.session_id)
                if success:
                    logger.info(f"기존 세션 종료: {st.session_state.session_id}")
                else:
                    logger.warning(f"기존 세션 종료 실패: {st.session_state.session_id}")
            
            # URL에서 세션 토큰 제거
            st.query_params.clear()
            
            # 쿠키에서 세션 토큰 제거
            remove_session_cookie()
            
            # 세션 상태 초기화
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.session_state.messages = []
            st.session_state.memory = None
            st.session_state.runnable = None
            st.session_state.session_id = None
            st.session_state.session_token = None
            st.session_state.thread_id = None
            st.session_state.db_manager = None
            st.session_state.participant_manager = None
            st.session_state.session_manager = None
            st.session_state.response_tracker = ResponseTimeTracker()
            st.session_state.admin_page = None
            
            logger.info("로그아웃 완료")
            st.rerun()
    
    # 관리자 페이지 표시
    if user_group == "admin":
        # 관리자 첫 로그인시 참가자 관리 탭을 기본으로 설정 (한 번만)
        if "admin_page" not in st.session_state:
            st.session_state.admin_page = "manage"
        
        admin_page_rendered = render_admin_page()
        if admin_page_rendered:
            # 관리자 페이지가 렌더링된 경우 여기서 종료
            pass
        else:
            # 대화 모드로 진행
            _render_chat_interface(user_name, user_id)
    else:
        # 일반 사용자 대화 모드
        _render_chat_interface(user_name, user_id)