"""
UI 스타일링 모듈

모바일 최적화 CSS 및 Streamlit UI 커스터마이징을 관리합니다.
"""

import streamlit as st


def apply_mobile_optimized_css():
    """모바일 최적화 CSS를 적용합니다."""
    mobile_css = """
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
    """
    
    st.markdown(mobile_css, unsafe_allow_html=True)


def apply_admin_page_styles():
    """관리자 페이지용 추가 스타일을 적용합니다."""
    admin_css = """
    <style>
        /* 관리자 버튼 너비 통일 */
        .stButton > button {
            width: 100% !important;
            min-width: 150px !important;
            padding: 0.5rem 1rem !important;
            font-size: 14px !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
        }
        
        /* 사이드바 관리자 메뉴 버튼 */
        .css-1d391kg .stButton > button {
            width: 100% !important;
            margin-bottom: 0.5rem !important;
            background-color: #f8f9fa !important;
            border: 1px solid #dee2e6 !important;
            color: #495057 !important;
        }
        
        .css-1d391kg .stButton > button:hover {
            background-color: #e9ecef !important;
            border-color: #adb5bd !important;
        }
        
        /* 관리자 테이블 반응형 디자인 */
        @media (max-width: 768px) {
            .stDataFrame {
                font-size: 0.8rem;
            }
            
            /* 관리자 통계 카드 모바일 최적화 */
            .metric-container {
                margin-bottom: 1rem;
            }
            
            /* 모바일에서 버튼 크기 조정 */
            .stButton > button {
                min-width: 120px !important;
                font-size: 13px !important;
            }
        }
        
        /* 관리자 폼 스타일링 */
        .stForm {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        /* 폼 내부 버튼 스타일 */
        .stForm .stButton > button {
            background-color: #007bff !important;
            color: white !important;
            border: none !important;
        }
        
        .stForm .stButton > button:hover {
            background-color: #0056b3 !important;
        }
        
        /* 상태 변경 섹션 버튼 */
        div[data-testid="column"] .stButton > button {
            background-color: #28a745 !important;
            color: white !important;
            border: none !important;
        }
        
        div[data-testid="column"] .stButton > button:hover {
            background-color: #1e7e34 !important;
        }
        
        /* 성공/에러 메시지 스타일링 */
        .stSuccess {
            border-radius: 6px;
            font-size: 14px !important;
        }
        
        .stError {
            border-radius: 6px;
            font-size: 14px !important;
        }
        
        /* 관리자 통계 메트릭 스타일 개선 */
        .metric-container .metric-value {
            font-size: 1.5rem !important;
            font-weight: 600 !important;
        }
        
        .metric-container .metric-label {
            font-size: 0.9rem !important;
            color: #666 !important;
        }
    </style>
    """
    
    st.markdown(admin_css, unsafe_allow_html=True)


def apply_chat_interface_styles():
    """채팅 인터페이스용 스타일을 적용합니다."""
    chat_css = """
    <style>
        /* 채팅 메시지 스타일링 */
        .stChatMessage {
            margin-bottom: 1rem;
        }
        
        /* 사용자 메시지 스타일 */
        .stChatMessage[data-testid="user-message"] {
            background-color: rgba(0, 123, 255, 0.1);
            border-radius: 12px;
        }
        
        /* AI 어시스턴트 메시지 스타일 */
        .stChatMessage[data-testid="assistant-message"] {
            background-color: rgba(248, 249, 250, 1);
            border-radius: 12px;
        }
        
        /* 채팅 입력창 스타일링 */
        .stChatInput {
            border-radius: 25px;
            border: 2px solid #e0e0e0;
        }
        
        .stChatInput:focus {
            border-color: #007bff;
            box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
        }
    </style>
    """
    
    st.markdown(chat_css, unsafe_allow_html=True)


def apply_login_page_styles():
    """로그인 페이지용 스타일을 적용합니다."""
    login_css = """
    <style>
        /* 로그인 폼 중앙 정렬 */
        .login-container {
            max-width: 400px;
            margin: 2rem auto;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* 로그인 제목 스타일링 */
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
            color: #333;
        }
        
        /* 로그인 버튼 스타일링 */
        .stButton > button {
            width: 100%;
            border-radius: 8px;
            background-color: #007bff;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            background-color: #0056b3;
        }
    </style>
    """
    
    st.markdown(login_css, unsafe_allow_html=True)


def configure_page_settings():
    """Streamlit 페이지 기본 설정을 구성합니다."""
    st.set_page_config(
        page_title="심리치료 대화 지원 에이전트",
        page_icon="🥼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def apply_all_styles():
    """모든 스타일을 한 번에 적용합니다."""
    apply_mobile_optimized_css()
    apply_admin_page_styles() 
    apply_chat_interface_styles()
    apply_login_page_styles()