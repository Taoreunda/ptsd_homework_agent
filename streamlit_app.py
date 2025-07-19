import streamlit as st
import json
import asyncio
import uuid
from operator import itemgetter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.memory import ConversationBufferMemory
import os
from utils.logging_config import get_logger
from dotenv import load_dotenv

load_dotenv()

# 로거 설정
logger = get_logger()

# 모바일 뷰포트 최적화 CSS (dvh 단위 사용)
st.markdown("""
<style>
    /* 모바일 뷰포트 높이 동적 대응 - dvh 단위 사용 */
    .stApp {
        min-height: 100dvh !important;
    }
    
    /* 채팅 입력 영역 모바일 최적화 */
    .stChatFloatingInputContainer {
        bottom: env(safe-area-inset-bottom, 0px) !important;
        padding-bottom: max(env(safe-area-inset-bottom, 0px), 1rem) !important;
    }
    
    /* 모바일에서 키보드 올라올 때 뷰포트 높이 조정 */
    @supports (height: 100dvh) {
        .stApp {
            height: 100dvh;
            min-height: 100dvh;
        }
    }
    
    /* CSS 변수 제거 - config.toml 테마만 사용 */
    
    /* 모바일 환경 최적화 - 채팅 입력창 위치만 조정 */
    @media (max-width: 768px) {
        /* 채팅 입력 컨테이너 위치 조정 */
        .stElementContainer:has(.stChatInput) {
            position: fixed !important;
            bottom: 3rem !important;  /* 화면 하단에서 3rem(48px) 위로 조정 */
            left: 0.5rem !important;
            right: 0.5rem !important;
            z-index: 999 !important;
        }
        
        /* 메인 컨텐츠 영역 하단 패딩 (채팅 입력창 공간 확보) */
        .main .block-container {
            padding-bottom: 6rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Streamlit 페이지 설정
st.set_page_config(
    page_title="심리치료 대화 지원 에이전트",
    page_icon="🥼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 유틸리티 함수들
def load_participants():
    """참가자 정보를 JSON 파일에서 로드합니다."""
    try:
        with open(os.getenv("PARTICIPANTS_JSON_PATH"), 'r', encoding='utf-8') as f:
            participants = json.load(f).get("participants", {})
            logger.info(f"참가자 정보 로드 완료: {len(participants)}명")
            return participants
    except (FileNotFoundError, json.JSONDecodeError) as e:
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

def authenticate_user(username: str, password: str) -> dict:
    """사용자 인증을 수행합니다."""
    participants = load_participants()
    logger.info(f"로그인 시도: {username}")
    
    for user_id, user_data in participants.items():
        if user_data["username"] == username and user_data["password"] == password:
            logger.info(f"로그인 성공: {user_id} ({user_data.get('name', 'Unknown')})")
            return {"user_id": user_id, "user_data": user_data}
    
    logger.warning(f"로그인 실패: {username}")
    return None

def setup_model_and_chain(user_name: str, memory: ConversationBufferMemory):
    """OpenAI 모델 및 대화 체인을 설정합니다."""
    
    # OpenAI 모델 생성 (비동기 스트리밍 지원)
    model = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL_NAME"),
        temperature=0.5,
        streaming=True
    )
    
    # 프롬프트 설정
    system_prompt_template = load_prompt(os.getenv("THERAPY_SYSTEM_PROMPT_PATH"))
    system_prompt = system_prompt_template.replace("길동님", f"{user_name}님")
    
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
if "runnable" not in st.session_state:
    st.session_state.runnable = None

# --- 인증 처리 ---
if not st.session_state.authenticated:
    st.subheader("🔐 로그인")
    
    with st.form("login_form"):
        username = st.text_input("사용자명")
        password = st.text_input("비밀번호", type="password")
        login_button = st.form_submit_button("로그인")
        
        if login_button:
            if username and password:
                auth_result = authenticate_user(username, password)
                if auth_result:
                    st.session_state.authenticated = True
                    st.session_state.user_info = auth_result
                    
                    # 세션 ID 생성
                    st.session_state.session_id = str(uuid.uuid4())
                    
                    # 기본 메모리 초기화
                    st.session_state.memory = ConversationBufferMemory(
                        memory_key="history", 
                        return_messages=True
                    )
                    
                    # 모델 및 체인 설정
                    st.session_state.runnable = setup_model_and_chain(
                        auth_result["user_data"]["name"],
                        st.session_state.memory
                    )
                    
                    st.success(f"환영합니다, {auth_result['user_data']['name']}님!")
                    st.rerun()
                else:
                    st.error("로그인에 실패했습니다. 사용자명과 비밀번호를 확인해주세요.")
            else:
                st.error("사용자명과 비밀번호를 입력해주세요.")

else:
    # --- 인증된 사용자 대화 인터페이스 ---
    user_name = st.session_state.user_info["user_data"]["name"]
    user_id = st.session_state.user_info["user_id"]
    
    # 사이드바에 사용자 정보
    with st.sidebar:
        st.subheader("👤 사용자 정보")
        st.write(f"**이름:** {user_name}")
        
        if st.button("로그아웃"):
            # 세션 종료 처리 (기본 메모리에는 close_session 없음)
            
            # 세션 상태 초기화
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.session_state.messages = []
            st.session_state.memory = None
            st.session_state.runnable = None
            st.session_state.session_id = None
            st.rerun()
    
    # 시작 메시지 초기화 (처음 로그인 시)
    if not st.session_state.messages:
        start_message = f"{user_name}님, 안녕하세요. 오늘 어떤 이야기를 해보고 싶으신가요?"
        st.session_state.messages.append({"role": "assistant", "content": start_message})
    
    # 대화 기록 표시 (Streamlit 표준 방식)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 사용자 입력 처리 (Streamlit 표준 채팅 UI 패턴)
    if prompt := st.chat_input("메시지를 입력하세요..."):
        # 사용자 메시지를 세션 상태 및 메모리에 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.memory.chat_memory.add_user_message(prompt)
        
        # 사용자 메시지 표시
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 응답 생성 및 스트리밍 표시 (Streamlit 표준 방식)
        with st.chat_message("assistant"):
            response = st.write_stream(
                response_generator(st.session_state.runnable, prompt)
            )
            
            # 로깅
            logger.info(f"AI 응답 완료: {user_id} - 사용자 메시지: {len(prompt)}자, AI 응답: {len(response)}자")
        
        # AI 응답을 세션 상태 및 메모리에 추가
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.memory.chat_memory.add_ai_message(response)
    

