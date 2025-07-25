"""
관리자 전용 페이지 모듈

PTSD 연구용 관리자 인터페이스를 제공합니다.
- 참가자 등록
- 참가자 관리 및 상태 변경
- 연구 통계 대시보드
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any
from utils.logging_config import get_logger
from .ui_styles import apply_admin_page_styles

logger = get_logger()


def render_admin_sidebar():
    """관리자 전용 사이드바 메뉴를 렌더링합니다."""
    st.markdown("---")
    st.subheader("👨‍💼 관리자 메뉴")
    
    if "admin_page" not in st.session_state:
        st.session_state.admin_page = None
    
    if st.button("📝 참가자 등록"):
        st.session_state.admin_page = "register"
        st.rerun()
    
    if st.button("📋 참가자 관리"):
        st.session_state.admin_page = "manage"
        st.rerun()
    
    if st.button("🏠 대화 모드"):
        st.session_state.admin_page = None
        st.rerun()


def render_participant_registration():
    """참가자 등록 페이지를 렌더링합니다."""
    apply_admin_page_styles()  # 관리자 페이지 전용 스타일 적용
    st.header("📝 참가자 등록")
    
    with st.form("register_participant"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_user_id = st.text_input("참가자 ID", placeholder="예: P001")
            new_password = st.text_input("비밀번호", type="password")
            new_name = st.text_input("참가자명")
            new_group = st.selectbox("그룹", ["treatment", "control"])
        
        with col2:
            new_phone = st.text_input("전화번호", placeholder="010-1234-5678")
            new_gender = st.selectbox("성별", ["", "남성", "여성", "기타"])
            new_age = st.number_input("나이", min_value=18, max_value=100, value=None)
        
        submitted = st.form_submit_button("참가자 등록")
        
        if submitted:
            if new_user_id and new_password and new_name and new_group:
                try:
                    success = st.session_state.participant_manager.add_participant(
                        new_user_id, 
                        new_password, 
                        new_name, 
                        new_group,
                        new_phone if new_phone else None,
                        new_gender if new_gender else None,
                        new_age if new_age else None
                    )
                    
                    if success:
                        st.success(f"✅ 참가자 '{new_name}' ({new_user_id}) 등록 완료!")
                        logger.info(f"관리자가 참가자 등록: {new_user_id}")
                    else:
                        st.error("❌ 참가자 등록 실패. 중복된 ID이거나 입력값을 확인해주세요.")
                except Exception as e:
                    st.error(f"❌ 등록 중 오류 발생: {e}")
                    logger.error(f"참가자 등록 오류: {e}")
            else:
                st.error("필수 항목을 모두 입력해주세요. (ID, 비밀번호, 이름, 그룹)")


def render_participant_management():
    """참가자 관리 페이지를 렌더링합니다."""
    apply_admin_page_styles()  # 관리자 페이지 전용 스타일 적용
    st.header("📋 참가자 관리")
    
    try:
        participants = st.session_state.participant_manager.get_participant_stats()
        
        if participants:
            # 참가자 목록 테이블
            _render_participant_table(participants)
            
            # 상태 변경 섹션
            _render_status_change_section(participants)
            
            # 요약 통계
            _render_research_statistics()
            
        else:
            st.info("등록된 참가자가 없습니다.")
            
    except Exception as e:
        st.error(f"참가자 정보 조회 오류: {e}")
        logger.error(f"참가자 관리 페이지 오류: {e}")


def _render_participant_table(participants: list):
    """참가자 목록 테이블을 렌더링합니다."""
    st.subheader("참가자 목록")
    
    df = pd.DataFrame(participants)
    
    # 표시할 컬럼 선택
    display_cols = [
        'user_id', 'name', 'group_type', 'status', 
        'gender', 'age', 'phone', 'completed_sessions', 'total_messages'
    ]
    available_cols = [col for col in display_cols if col in df.columns]
    
    st.dataframe(
        df[available_cols],
        use_container_width=True,
        column_config={
            "user_id": "ID",
            "name": "이름", 
            "group_type": "그룹",
            "status": "상태",
            "gender": "성별",
            "age": "나이",
            "phone": "전화번호",
            "completed_sessions": "세션수",
            "total_messages": "메시지수"
        }
    )


def _render_status_change_section(participants: list):
    """참가자 상태 변경 섹션을 렌더링합니다."""
    st.subheader("참가자 상태 변경")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_user = st.selectbox(
            "참가자 선택",
            options=[p['user_id'] for p in participants if p['group_type'] != 'admin'],
            format_func=lambda x: f"{x} ({next(p['name'] for p in participants if p['user_id'] == x)})"
        )
    
    with col2:
        new_status = st.selectbox("새 상태", ["active", "dropout", "completed"])
    
    with col3:
        if st.button("상태 변경"):
            if selected_user:
                success = st.session_state.participant_manager.update_participant_status(
                    selected_user, new_status
                )
                if success:
                    st.success(f"✅ {selected_user}의 상태를 '{new_status}'로 변경했습니다.")
                    st.rerun()
                else:
                    st.error("❌ 상태 변경 실패")


def _render_research_statistics():
    """연구 통계 대시보드를 렌더링합니다."""
    st.subheader("연구 통계")
    
    try:
        summary = st.session_state.participant_manager.get_summary_stats()
        
        # 첫 번째 행: 기본 통계
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 참가자", summary.get('total_participants', 0))
        with col2:
            st.metric("활성 참가자", summary.get('active_participants', 0))
        with col3:
            st.metric("Treatment 그룹", summary.get('treatment_group', 0))
        with col4:
            st.metric("Control 그룹", summary.get('control_group', 0))
        
        # 두 번째 행: 상태 및 인구통계
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("중도포기", summary.get('dropout_participants', 0))
        with col6:
            st.metric("완료", summary.get('completed_participants', 0))
        with col7:
            avg_age = summary.get('avg_age', 0)
            st.metric("평균 나이", f"{avg_age:.1f}세" if avg_age else "N/A")
        with col8:
            male_count = summary.get('male_participants', 0)
            female_count = summary.get('female_participants', 0)
            st.metric("남성/여성", f"{male_count}/{female_count}")
            
    except Exception as e:
        st.error(f"통계 조회 오류: {e}")
        logger.error(f"연구 통계 조회 오류: {e}")


def render_admin_page():
    """현재 선택된 관리자 페이지를 렌더링합니다."""
    admin_page = st.session_state.get("admin_page", None)
    
    if admin_page == "register":
        render_participant_registration()
    elif admin_page == "manage":
        render_participant_management()
    else:
        # 관리자가 대화 모드를 선택한 경우 None 반환 (메인 앱에서 처리)
        return None
    
    return True  # 관리자 페이지가 렌더링됨을 표시