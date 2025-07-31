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
    
    if st.button("📝 참가자 관리"):
        st.session_state.admin_page = "manage"
        st.rerun()
    
    if st.button("🔧 프롬프트 튜닝"):
        st.session_state.admin_page = "prompt_tuning"
        st.rerun()
    
    if st.button("🏠 대화 모드"):
        st.session_state.admin_page = None
        st.rerun()




def render_participant_management():
    """통합 참가자 관리 페이지를 렌더링합니다."""
    st.header("📋 참가자 관리")
    
    # 2열 레이아웃 구성
    left_col, right_col = st.columns([1, 1.5])
    
    # 왼쪽 열: 참가자 등록/수정/삭제
    with left_col:
        _render_participant_crud_section()
    
    # 오른쪽 열: 참가자 목록 (스크롤 가능)
    with right_col:
        _render_participant_list_section()




def render_admin_page():
    """현재 선택된 관리자 페이지를 렌더링합니다."""
    admin_page = st.session_state.get("admin_page", None)
    
    if admin_page == "manage":
        render_participant_management()
        return True  # 관리자 페이지가 렌더링됨을 표시
    elif admin_page == "prompt_tuning":
        render_prompt_tuning()
        return True  # 관리자 페이지가 렌더링됨을 표시
    else:
        # 관리자가 대화 모드를 선택한 경우 None 반환 (메인 앱에서 처리)
        return None




def _render_participant_crud_section():
    """통합 참가자 CRUD 섹션을 렌더링합니다."""
    st.subheader("📝 참가자 관리")
    
    # 삭제 확인 상태 관리
    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = False
    if "delete_target" not in st.session_state:
        st.session_state.delete_target = None
    
    # 메인 참가자 폼 (항상 표시)
    with st.form("participant_form", clear_on_submit=False):
        st.markdown("#### 참가자 정보")
        
        # 첫 번째 행: 참가자 ID, 비밀번호
        col1, col2 = st.columns(2)
        with col1:
            form_user_id = st.text_input("참가자 ID", value=st.session_state.get("form_user_id", ""), placeholder="예: P001")
        with col2:
            form_password = st.text_input("비밀번호", value=st.session_state.get("form_password", ""), placeholder="최소 4자 이상")
        
        # 두 번째 행: 이름, 그룹
        col3, col4 = st.columns(2)
        with col3:
            form_name = st.text_input("참가자명", value=st.session_state.get("form_name", ""))
        with col4:
            current_group = st.session_state.get("form_group", "treatment")
            group_options = ["treatment", "control", "admin"]
            group_index = group_options.index(current_group) if current_group in group_options else 0
            form_group = st.selectbox("그룹", group_options, index=group_index)
        
        # 세 번째 행: 성별, 나이
        col5, col6 = st.columns(2)
        with col5:
            current_gender = st.session_state.get("form_gender", "")
            gender_options = ["", "남성", "여성", "기타"]
            gender_index = gender_options.index(current_gender) if current_gender in gender_options else 0
            form_gender = st.selectbox("성별", gender_options, index=gender_index)
        with col6:
            form_age = st.number_input("나이", min_value=18, max_value=100, 
                                      value=st.session_state.get("form_age", None))
        
        # 네 번째 행: 전화번호
        form_phone = st.text_input("전화번호", value=st.session_state.get("form_phone", ""), placeholder="010-1234-5678")
        
        # 버튼 레이아웃: [로드] [등록] [수정] [삭제] [재설정]
        st.markdown("---")
        col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
        
        with col_btn1:
            load_btn = st.form_submit_button("🔍 로드", use_container_width=True)
        with col_btn2:
            register_btn = st.form_submit_button("✅ 등록", use_container_width=True)
        with col_btn3:
            update_btn = st.form_submit_button("📝 수정", use_container_width=True)
        with col_btn4:
            delete_btn = st.form_submit_button("🗑️ 삭제", use_container_width=True)
        with col_btn5:
            reset_btn = st.form_submit_button("🔄 재설정", use_container_width=True)
    
    # 삭제 버튼 빨간색 스타일링
    st.markdown("""
    <style>
    div[data-testid="column"]:nth-child(4) .stFormSubmitButton > button {
        color: #dc3545 !important;
        border-color: #dc3545 !important;
    }
    div[data-testid="column"]:nth-child(4) .stFormSubmitButton > button:hover {
        background-color: #dc3545 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 버튼 처리 로직
    if load_btn:
        _handle_load_participant(form_user_id)
    elif register_btn:
        _handle_register_participant(form_user_id, form_password, form_name, form_group, form_phone, form_gender, form_age)
    elif update_btn:
        _handle_update_participant(form_user_id, form_name, form_password, form_phone, form_gender, form_age)
    elif delete_btn:
        _handle_delete_participant(form_user_id)
    elif reset_btn:
        _handle_reset_form()
    
    # 삭제 확인 모달
    if st.session_state.confirm_delete and st.session_state.delete_target:
        _render_delete_confirmation_modal()


def _handle_load_participant(load_id: str):
    """참가자 로드 처리"""
    if not load_id:
        st.error("❌ 로드할 참가자 ID를 입력해주세요.")
        return
    
    try:
        participant = st.session_state.participant_manager.get_participant_info(load_id)
        if participant:
            # 폼에 데이터 로드 (비밀번호 포함)
            st.session_state.form_user_id = participant.get('user_id', '')
            st.session_state.form_password = participant.get('password', '')
            st.session_state.form_name = participant.get('name', '')
            st.session_state.form_group = participant.get('group_type', 'treatment')
            st.session_state.form_phone = participant.get('phone', '') or ''
            st.session_state.form_gender = participant.get('gender', '') or ''
            st.session_state.form_age = participant.get('age', None)
            
            st.success(f"✅ 참가자 '{participant.get('name', 'N/A')}' 데이터를 불러왔습니다.")
            st.rerun()
        else:
            st.error(f"❌ 참가자 ID '{load_id}'를 찾을 수 없습니다.")
    except Exception as e:
        st.error(f"❌ 데이터 로드 중 오류: {e}")
        logger.error(f"참가자 로드 오류: {e}")


def _handle_register_participant(user_id: str, password: str, name: str, group: str, phone: str, gender: str, age: int):
    """참가자 등록 처리"""
    if not user_id or not password or not name or not group:
        st.error("❌ 필수 항목(참가자 ID, 비밀번호, 이름, 그룹)을 모두 입력해주세요.")
        return
    
    # 입력값 검증
    if len(user_id) < 3:
        st.error("❌ 참가자 ID는 최소 3자 이상이어야 합니다.")
        return
    
    if len(password) < 4:
        st.error("❌ 비밀번호는 최소 4자 이상이어야 합니다.")
        return
    
    try:
        # 기존 참가자 확인
        existing_participant = st.session_state.participant_manager.get_participant_info(user_id)
        if existing_participant:
            st.error(f"❌ 참가자 ID '{user_id}'는 이미 사용 중입니다.")
            return
        
        # 참가자 등록
        success = st.session_state.participant_manager.add_participant(
            user_id, password, name, group,
            phone if phone else None,
            gender if gender else None,
            age if age else None
        )
        
        if success:
            st.success(f"✅ 참가자 '{name}' 등록 완료!")
            logger.info(f"관리자가 참가자 등록: {user_id}")
            _clear_form_data()
            st.rerun()
        else:
            st.error("❌ 등록 실패. 입력값을 확인해주세요.")
            
    except Exception as e:
        st.error(f"❌ 등록 중 오류: {e}")
        logger.error(f"참가자 등록 오류: {e}")


def _handle_update_participant(user_id: str, name: str, password: str, phone: str, gender: str, age: int):
    """참가자 수정 처리"""
    if not user_id:
        st.error("❌ 수정할 참가자 ID를 입력해주세요.")
        return
    
    if not name:
        st.error("❌ 참가자명은 필수 항목입니다.")
        return
    
    if password and len(password) < 4:
        st.error("❌ 비밀번호는 최소 4자 이상이어야 합니다.")
        return
    
    try:
        # 참가자 존재 확인
        existing_participant = st.session_state.participant_manager.get_participant_info(user_id)
        if not existing_participant:
            st.error(f"❌ 참가자 ID '{user_id}'를 찾을 수 없습니다.")
            return
        
        # 참가자 정보 수정 (비밀번호 포함)
        success = st.session_state.participant_manager.update_participant(
            user_id, 
            name, 
            password if password else None, 
            phone if phone else None, 
            gender if gender else None, 
            age if age else None
        )
        
        if success:
            st.success(f"✅ 참가자 '{name}' 정보가 수정되었습니다!")
            logger.info(f"관리자가 참가자 정보 수정: {user_id}")
            st.rerun()
        else:
            st.error("❌ 수정 실패. 입력값을 확인해주세요.")
            
    except Exception as e:
        st.error(f"❌ 수정 중 오류: {e}")
        logger.error(f"참가자 수정 오류: {e}")


def _handle_delete_participant(user_id: str):
    """참가자 삭제 처리 (확인 단계)"""
    if not user_id:
        st.error("❌ 삭제할 참가자 ID를 입력해주세요.")
        return
    
    try:
        # 참가자 존재 확인
        participant = st.session_state.participant_manager.get_participant_info(user_id)
        if not participant:
            st.error(f"❌ 참가자 ID '{user_id}'를 찾을 수 없습니다.")
            return
        
        # 관리자 계정 삭제 방지
        if participant.get('group_type') == 'admin':
            st.error("❌ 관리자 계정은 삭제할 수 없습니다.")
            return
        
        # 삭제 확인 상태 설정
        st.session_state.confirm_delete = True
        st.session_state.delete_target = participant
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ 삭제 처리 중 오류: {e}")
        logger.error(f"참가자 삭제 처리 오류: {e}")


def _render_delete_confirmation_modal():
    """삭제 확인 모달"""
    participant = st.session_state.delete_target
    
    st.markdown("---")
    st.markdown("### 🗑️ 참가자 삭제 확인")
    st.warning(f"⚠️ 정말로 '{participant['name']}' ({participant['user_id']}) 참가자를 삭제하시겠습니까?")
    st.error("이 작업은 되돌릴 수 없으며, 모든 대화 데이터도 함께 삭제됩니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("❌ 삭제 확인", type="primary", use_container_width=True, key="confirm_delete_btn"):
            try:
                success = st.session_state.participant_manager.delete_participant(participant['user_id'])
                
                if success:
                    st.success(f"✅ 참가자 '{participant['name']}' 삭제 완료!")
                    logger.info(f"관리자가 참가자 삭제: {participant['user_id']}")
                    _clear_form_data()
                    st.session_state.confirm_delete = False
                    st.session_state.delete_target = None
                    st.rerun()
                else:
                    st.error("❌ 삭제 실패. 다시 시도해주세요.")
                    
            except Exception as e:
                st.error(f"❌ 삭제 중 오류: {e}")
                logger.error(f"참가자 삭제 오류: {e}")
    
    with col2:
        if st.button("취소", use_container_width=True, key="cancel_delete_btn"):
            st.session_state.confirm_delete = False
            st.session_state.delete_target = None
            st.rerun()


def _handle_reset_form():
    """폼 재설정 처리"""
    _clear_form_data()
    st.success("✅ 폼이 초기화되었습니다.")
    st.rerun()


def _clear_form_data():
    """폼 데이터 초기화"""
    # 모든 폼 관련 session_state 키를 삭제
    form_keys = ["form_user_id", "form_password", "form_name", "form_group", "form_phone", "form_gender", "form_age"]
    for key in form_keys:
        if key in st.session_state:
            del st.session_state[key]


def _render_participant_list_section():
    """참가자 목록 섹션을 렌더링합니다 (스크롤 가능)."""
    st.subheader("👥 참가자 목록")
    
    try:
        participants = st.session_state.participant_manager.get_participant_stats()
        
        if participants:
            # 검색/필터 기능
            col1, col2 = st.columns(2)
            with col1:
                search_term = st.text_input("🔍 검색", placeholder="이름 또는 ID로 검색")
            with col2:
                filter_group = st.selectbox("그룹 필터", ["전체", "treatment", "control", "admin"])
            
            # 필터링
            filtered_participants = participants
            if search_term:
                filtered_participants = [
                    p for p in filtered_participants 
                    if search_term.lower() in p.get('name', '').lower() 
                    or search_term.lower() in p.get('user_id', '').lower()
                ]
            
            if filter_group != "전체":
                filtered_participants = [
                    p for p in filtered_participants 
                    if p.get('group_type') == filter_group
                ]
            
            # 참가자 목록 테이블 (스크롤 가능)
            if filtered_participants:
                df = pd.DataFrame(filtered_participants)
                
                # 표시할 컬럼 선택 및 순서 정리
                display_cols = ['user_id', 'name', 'group_type', 'status', 'gender', 'age', 'phone']
                available_cols = [col for col in display_cols if col in df.columns]
                
                # 스크롤 가능한 테이블로 표시
                st.dataframe(
                    df[available_cols],
                    use_container_width=True,
                    height=400,  # 고정 높이로 스크롤 가능
                    column_config={
                        "user_id": st.column_config.TextColumn("ID", width="small"),
                        "name": st.column_config.TextColumn("이름", width="medium"),
                        "group_type": st.column_config.TextColumn("그룹", width="small"),
                        "status": st.column_config.TextColumn("상태", width="small"),
                        "gender": st.column_config.TextColumn("성별", width="small"),
                        "age": st.column_config.NumberColumn("나이", width="small"),
                        "phone": st.column_config.TextColumn("전화번호", width="medium")
                    }
                )
                
                # 참가자 총 개수 표시
                st.info(f"총 {len(filtered_participants)}명의 참가자가 등록되어 있습니다.")
                
            else:
                st.info("검색 조건에 맞는 참가자가 없습니다.")
        else:
            st.info("등록된 참가자가 없습니다.")
            
    except Exception as e:
        st.error(f"참가자 목록 조회 오류: {e}")
        logger.error(f"참가자 목록 조회 오류: {e}")


def render_prompt_tuning():
    """프롬프트 튜닝 페이지를 렌더링합니다."""
    st.header("🔧 프롬프트 튜닝")
    
    # LLM 설정 관리를 위한 데이터베이스 매니저 접근
    try:
        db_manager = st.session_state.db_manager
        
        # 현재 활성 설정 조회
        active_config = _get_active_config(db_manager)
        
        if not active_config:
            st.error("❌ 활성 LLM 설정을 찾을 수 없습니다. 기본 설정을 생성합니다.")
            if st.button("기본 설정 생성"):
                _create_default_config(db_manager)
                st.rerun()
            return
        
        # 탭 구성
        config_tab, history_tab = st.tabs(["⚙️ 설정 편집", "📋 설정 이력"])
        
        with config_tab:
            _render_config_editor(db_manager, active_config)
        
        with history_tab:
            _render_config_history(db_manager)
            
    except Exception as e:
        st.error(f"❌ 프롬프트 튜닝 페이지 로드 오류: {e}")
        logger.error(f"프롬프트 튜닝 페이지 오류: {e}")


def _get_active_config(db_manager):
    """현재 활성 LLM 설정을 조회합니다."""
    try:
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_active_llm_config()")
            result = cursor.fetchone()
            
            if result:
                return {
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
            return None
    except Exception as e:
        logger.error(f"활성 설정 조회 오류: {e}")
        return None


def _create_default_config(db_manager):
    """기본 LLM 설정을 생성합니다."""
    try:
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT create_default_llm_config()")
            config_id = cursor.fetchone()[0]
            conn.commit()
            
            st.success(f"✅ 기본 설정이 생성되었습니다: {config_id}")
            logger.info(f"기본 LLM 설정 생성: {config_id}")
            return True
    except Exception as e:
        st.error(f"❌ 기본 설정 생성 실패: {e}")
        logger.error(f"기본 설정 생성 오류: {e}")
        return False


def _render_config_editor(db_manager, active_config):
    """설정 편집 UI를 렌더링합니다."""
    st.subheader("현재 활성 설정 편집")
    
    with st.form("llm_config_form"):
        # 설정명 입력
        st.markdown("#### 설정 기본 정보")
        config_name = st.text_input(
            "설정명",
            value=active_config['config_name'],
            help="이 LLM 설정의 이름을 입력하세요."
        )
        
        st.markdown("#### 시스템 프롬프트")
        system_prompt = st.text_area(
            "시스템 프롬프트",
            value=active_config['system_prompt'],
            height=300,
            help="치료 에이전트의 기본 행동과 응답 방식을 정의하는 프롬프트입니다.",
            label_visibility="collapsed"
        )
        
        # 모델 설정
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### AI 모델 설정")
            model_name = st.selectbox(
                "모델명",
                options=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini", "gpt-4.1"],
                index=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini", "gpt-4.1"].index(active_config['model_name']) if active_config['model_name'] in ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini", "gpt-4.1"] else 5,
                help="사용할 OpenAI GPT 모델을 선택합니다."
            )
            
            temperature = st.slider(
                "Temperature",
                min_value=0.0, max_value=2.0, 
                value=active_config['temperature'],
                step=0.1,
                help="창의성 수준 (0=일관성, 2=창의성)"
            )
            
            max_tokens = st.slider(
                "Max Tokens",
                min_value=100, max_value=2000,
                value=active_config['max_tokens'],
                step=50,
                help="응답 최대 길이 (토큰 수)"
            )
        
        with col2:
            st.markdown("#### 고급 설정")
            top_p = st.slider(
                "Top P",
                min_value=0.0, max_value=1.0,
                value=active_config['top_p'],
                step=0.1,
                help="단어 선택 다양성 제어"
            )
            
            frequency_penalty = st.slider(
                "Frequency Penalty",
                min_value=-2.0, max_value=2.0,
                value=active_config['frequency_penalty'],
                step=0.1,
                help="단어 반복 억제 (-2=허용, 2=강력억제)"
            )
            
            presence_penalty = st.slider(
                "Presence Penalty",
                min_value=-2.0, max_value=2.0,
                value=active_config['presence_penalty'],
                step=0.1,
                help="새 주제 도입 촉진 (-2=반복, 2=새주제)"
            )
        
        # 저장 버튼
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            save_button = st.form_submit_button("💾 설정 저장", use_container_width=True, type="primary")
    
    # 설정 저장 처리
    if save_button:
        success = _save_config(
            db_manager, active_config['config_id'], config_name,
            system_prompt, model_name, temperature, max_tokens,
            top_p, frequency_penalty, presence_penalty
        )
        
        if success:
            st.success("✅ 설정이 성공적으로 저장되었습니다!")
            st.info("🔄 새 설정은 다음 대화부터 자동으로 적용됩니다.")
            # 세션 상태의 LLM 설정을 업데이트하여 즉시 반영
            if hasattr(st.session_state, 'runnable'):
                st.session_state.runnable = None  # 기존 체인 초기화하여 재생성 유도
                logger.info("LLM 설정 변경으로 runnable 초기화")
            st.rerun()
        else:
            st.error("❌ 설정 저장에 실패했습니다.")


def _save_config(db_manager, config_id, config_name, system_prompt, model_name, temperature, max_tokens, top_p, frequency_penalty, presence_penalty):
    """LLM 설정을 저장합니다."""
    try:
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            
            # 설정명도 함께 업데이트
            cursor.execute("""
                UPDATE llm_configurations SET
                    config_name = %s,
                    system_prompt = %s,
                    model_name = %s,
                    temperature = %s,
                    max_tokens = %s,
                    top_p = %s,
                    frequency_penalty = %s,
                    presence_penalty = %s,
                    updated_at = NOW()
                WHERE config_id = %s
            """, (
                config_name, system_prompt, model_name, temperature, max_tokens,
                top_p, frequency_penalty, presence_penalty, config_id
            ))
            
            conn.commit()
            
            # UPDATE가 성공했는지 확인
            if cursor.rowcount > 0:
                logger.info(f"LLM 설정 업데이트 성공: {config_id}")
                return True
            else:
                logger.warning(f"LLM 설정 업데이트 실패: {config_id}")
                return False
                
    except Exception as e:
        logger.error(f"LLM 설정 저장 오류: {e}")
        return False


def _render_config_history(db_manager):
    """설정 이력을 렌더링합니다."""
    st.subheader("설정 이력")
    
    try:
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_all_llm_configs()")
            configs = cursor.fetchall()
        
        if configs:
            # 설정 목록을 DataFrame으로 변환
            import pandas as pd
            
            df_data = []
            for config in configs:
                # 시스템 프롬프트 미리보기 (처음 50자 + ...)
                prompt_preview = config[2][:50] + "..." if len(config[2]) > 50 else config[2]
                
                df_data.append({
                    "설정명": config[1],
                    "프롬프트": prompt_preview,
                    "모델": config[3],
                    "Temp": float(config[4]),
                    "Max Tokens": config[5],
                    "Top P": float(config[6]),
                    "Freq Penalty": float(config[7]),
                    "Pres Penalty": float(config[8]),
                    "활성": "✅" if config[9] else "❌",
                    "생성일시": config[11].strftime("%m-%d %H:%M")
                })
            
            df = pd.DataFrame(df_data)
            
            st.dataframe(
                df,
                use_container_width=True,
                height=400,
                column_config={
                    "설정명": st.column_config.TextColumn("설정명", width="medium"),
                    "프롬프트": st.column_config.TextColumn("프롬프트", width="large"),
                    "모델": st.column_config.TextColumn("모델", width="small"),
                    "Temp": st.column_config.NumberColumn("Temp", format="%.1f", width="small"),
                    "Max Tokens": st.column_config.NumberColumn("Max Tokens", width="small"),
                    "Top P": st.column_config.NumberColumn("Top P", format="%.1f", width="small"),
                    "Freq Penalty": st.column_config.NumberColumn("Freq Penalty", format="%.1f", width="small"),
                    "Pres Penalty": st.column_config.NumberColumn("Pres Penalty", format="%.1f", width="small"),
                    "활성": st.column_config.TextColumn("활성", width="small"),
                    "생성일시": st.column_config.TextColumn("생성일시", width="medium")
                }
            )
            
            st.info(f"총 {len(configs)}개의 설정이 있습니다.")
        else:
            st.info("저장된 설정이 없습니다.")
            
    except Exception as e:
        st.error(f"❌ 설정 이력 조회 오류: {e}")
        logger.error(f"설정 이력 조회 오류: {e}")


