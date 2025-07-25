#!/usr/bin/env python3
"""
참가자 데이터 JSON → PostgreSQL 마이그레이션 스크립트

기존 participants.json 파일의 데이터를 Supabase PostgreSQL 데이터베이스로 이전합니다.
"""

import os
import json
import psycopg2
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리 찾기
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 환경변수 로드
load_dotenv(project_root / '.env')

def load_participants_json(json_path: str) -> dict:
    """
    JSON 파일에서 참가자 데이터 로드
    
    Args:
        json_path: participants.json 파일 경로
        
    Returns:
        dict: 참가자 데이터
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('participants', {})
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {json_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return {}

def test_database_connection(database_url: str) -> bool:
    """
    데이터베이스 연결 테스트
    
    Args:
        database_url: PostgreSQL 연결 문자열
        
    Returns:
        bool: 연결 성공 여부
    """
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        print("✅ 데이터베이스 연결 성공")
        return True
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False

def check_participants_table_exists(database_url: str) -> bool:
    """
    participants 테이블 존재 여부 확인
    
    Args:
        database_url: PostgreSQL 연결 문자열
        
    Returns:
        bool: 테이블 존재 여부
    """
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'participants'
            );
        """)
        
        exists = cursor.fetchone()[0]
        conn.close()
        
        if exists:
            print("✅ participants 테이블이 존재합니다")
        else:
            print("❌ participants 테이블이 존재하지 않습니다")
            print("먼저 sql/create_participants_table.sql을 실행하세요")
        
        return exists
        
    except Exception as e:
        print(f"❌ 테이블 확인 중 오류: {e}")
        return False

def migrate_participant_data(database_url: str, participants: dict) -> bool:
    """
    참가자 데이터를 데이터베이스로 마이그레이션
    
    Args:
        database_url: PostgreSQL 연결 문자열
        participants: 참가자 데이터 딕셔너리
        
    Returns:
        bool: 마이그레이션 성공 여부
    """
    if not participants:
        print("⚠️ 마이그레이션할 참가자 데이터가 없습니다")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        success_count = 0
        error_count = 0
        
        for user_id, data in participants.items():
            try:
                # 데이터 검증 및 변환
                username = data.get('username')
                password = data.get('password') 
                name = data.get('name')
                group_type = data.get('group', 'treatment')  # 기본값: treatment
                enrolled_date = data.get('enrolled_date', '2024-07-01')
                session_limit = data.get('session_limit', 7)
                status = data.get('status', 'active')
                
                # 필수 필드 검증
                if not all([username, password, name]):
                    print(f"⚠️ 필수 필드 누락: {user_id}")
                    error_count += 1
                    continue
                
                # group_type 검증 및 변환
                if group_type not in ['treatment', 'control', 'admin']:
                    print(f"⚠️ 잘못된 group_type ({group_type}), 기본값(treatment) 사용: {user_id}")
                    group_type = 'treatment'
                
                # 날짜 형식 변환
                try:
                    enrolled_date = datetime.strptime(enrolled_date, '%Y-%m-%d').date()
                except ValueError:
                    enrolled_date = datetime.strptime('2024-07-01', '%Y-%m-%d').date()
                    print(f"⚠️ 잘못된 날짜 형식, 기본값 사용: {user_id}")
                
                # 데이터베이스에 삽입 (UPSERT)
                cursor.execute("""
                    INSERT INTO participants (user_id, username, password, name, group_type, enrolled_date, session_limit, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        password = EXCLUDED.password,
                        name = EXCLUDED.name,
                        group_type = EXCLUDED.group_type,
                        enrolled_date = EXCLUDED.enrolled_date,
                        session_limit = EXCLUDED.session_limit,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                """, (user_id, username, password, name, group_type, enrolled_date, session_limit, status))
                
                success_count += 1
                print(f"✅ 마이그레이션 완료: {user_id} ({username})")
                
            except Exception as e:
                print(f"❌ 마이그레이션 실패: {user_id} - {e}")
                error_count += 1
                continue
        
        # 트랜잭션 커밋
        conn.commit()
        conn.close()
        
        print(f"\n📊 마이그레이션 결과:")
        print(f"   성공: {success_count}개")
        print(f"   실패: {error_count}개")
        print(f"   총계: {success_count + error_count}개")
        
        return error_count == 0
        
    except Exception as e:
        print(f"❌ 마이그레이션 중 전체 오류: {e}")
        return False

def verify_migration(database_url: str, original_participants: dict) -> bool:
    """
    마이그레이션 결과 검증
    
    Args:
        database_url: PostgreSQL 연결 문자열
        original_participants: 원본 참가자 데이터
        
    Returns:
        bool: 검증 성공 여부
    """
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # 데이터베이스에서 참가자 수 조회
        cursor.execute("SELECT COUNT(*) FROM participants")
        db_count = cursor.fetchone()[0]
        
        # 원본 데이터 개수
        original_count = len(original_participants)
        
        print(f"\n🔍 마이그레이션 검증:")
        print(f"   원본 JSON: {original_count}개")
        print(f"   데이터베이스: {db_count}개")
        
        # 각 참가자별 검증
        missing_participants = []
        for user_id in original_participants.keys():
            cursor.execute("SELECT COUNT(*) FROM participants WHERE user_id = %s", (user_id,))
            exists = cursor.fetchone()[0] > 0
            
            if not exists:
                missing_participants.append(user_id)
        
        if missing_participants:
            print(f"❌ 누락된 참가자: {missing_participants}")
            conn.close()
            return False
        
        print("✅ 모든 참가자 데이터가 정상적으로 마이그레이션되었습니다")
        
        # 샘플 데이터 확인
        cursor.execute("SELECT user_id, username, name, group_type FROM participants ORDER BY user_id")
        sample_data = cursor.fetchall()
        
        print(f"\n📋 마이그레이션된 데이터 (처음 5개):")
        for i, (user_id, username, name, group_type) in enumerate(sample_data[:5]):
            print(f"   {i+1}. {user_id}: {name} ({username}) - {group_type}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 검증 중 오류: {e}")
        return False

def create_backup_json(database_url: str, backup_path: str) -> bool:
    """
    데이터베이스에서 JSON 백업 파일 생성
    
    Args:
        database_url: PostgreSQL 연결 문자열
        backup_path: 백업 파일 경로
        
    Returns:
        bool: 백업 성공 여부
    """
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, password, name, group_type, 
                   enrolled_date, session_limit, status
            FROM participants 
            ORDER BY user_id
        """)
        
        participants_data = {}
        for row in cursor.fetchall():
            user_id, username, password, name, group_type, enrolled_date, session_limit, status = row
            
            participants_data[user_id] = {
                'username': username,
                'password': password,
                'name': name,
                'group': group_type,
                'enrolled_date': enrolled_date.strftime('%Y-%m-%d'),
                'session_limit': session_limit,
                'status': status
            }
        
        backup_data = {
            'participants': participants_data,
            'backup_created_at': datetime.now().isoformat(),
            'source': 'postgresql_database'
        }
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 백업 파일 생성: {backup_path}")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 백업 생성 실패: {e}")
        return False

def main():
    """메인 마이그레이션 함수"""
    print("🚀 참가자 데이터 마이그레이션 시작")
    print("=" * 50)
    
    # 환경변수 확인
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다")
        print("   .env 파일에 DATABASE_URL을 설정하세요")
        return False
    
    # JSON 파일 경로
    json_path = project_root / 'data' / 'participants.json'
    if not json_path.exists():
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        return False
    
    # 1. 데이터베이스 연결 테스트
    if not test_database_connection(database_url):
        return False
    
    # 2. participants 테이블 존재 확인
    if not check_participants_table_exists(database_url):
        return False
    
    # 3. JSON 데이터 로드
    print(f"\n📁 JSON 파일 로드: {json_path}")
    participants_data = load_participants_json(str(json_path))
    
    if not participants_data:
        print("❌ 로드할 참가자 데이터가 없습니다")
        return False
    
    print(f"✅ {len(participants_data)}개의 참가자 데이터 로드됨")
    
    # 4. 데이터 마이그레이션
    print(f"\n🔄 데이터베이스로 마이그레이션 시작...")
    success = migrate_participant_data(database_url, participants_data)
    
    if not success:
        print("❌ 마이그레이션 실패")
        return False
    
    # 5. 마이그레이션 검증
    if not verify_migration(database_url, participants_data):
        print("❌ 마이그레이션 검증 실패")
        return False
    
    # 6. 백업 파일 생성
    backup_path = project_root / 'data' / f'participants_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    create_backup_json(database_url, str(backup_path))
    
    print(f"\n🎉 마이그레이션 완료!")
    print(f"   원본 JSON: {json_path}")
    print(f"   백업 파일: {backup_path}")
    print(f"   이제 streamlit_app.py에서 데이터베이스 인증을 사용할 수 있습니다")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)