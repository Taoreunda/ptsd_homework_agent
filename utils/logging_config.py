"""
로깅 설정 모듈

PTSD 치료 챗봇 애플리케이션의 로깅을 관리합니다.
일별 파일 분리, 타임스탬프, 파일명, 오류정보를 포함한 구조화된 로깅을 제공합니다.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys
import os


class ColoredFormatter(logging.Formatter):
    """컬러 포맷터 - 콘솔 출력시 로그 레벨별 색상 구분"""
    
    # ANSI 색상 코드
    COLORS = {
        'DEBUG': '\033[36m',     # 청록색
        'INFO': '\033[32m',      # 초록색
        'WARNING': '\033[33m',   # 노란색
        'ERROR': '\033[31m',     # 빨간색
        'CRITICAL': '\033[35m'   # 자주색
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 색상 적용
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class TimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """일별 로그 파일 핸들러 - 한국어 파일명 형식"""
    
    def __init__(self, log_dir: str, **kwargs):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 오늘 날짜로 로그 파일명 생성
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.log_dir / f"{today}.log"
        
        super().__init__(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=30,  # 30일간 로그 보관
            encoding='utf-8',
            **kwargs
        )
    
    def doRollover(self):
        """자정에 새로운 로그 파일 생성"""
        super().doRollover()
        
        # 새로운 파일명으로 업데이트
        today = datetime.now().strftime('%Y-%m-%d')
        new_log_file = self.log_dir / f"{today}.log"
        self.baseFilename = str(new_log_file)


def setup_logger(
    name: str = "ptsd_chatbot",
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_file: bool = True
) -> logging.Logger:
    """
    로거 설정 및 초기화
    
    Args:
        name: 로거 이름
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 로그 파일 저장 디렉토리
        enable_console: 콘솔 출력 활성화
        enable_file: 파일 출력 활성화
        
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정된 경우 재설정 방지
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 로그 포맷 정의
    file_format = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_format = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 파일 핸들러 설정
    if enable_file:
        try:
            file_handler = TimedRotatingFileHandler(log_dir)
            file_handler.setFormatter(file_format)
            file_handler.setLevel(logging.DEBUG)  # 파일에는 모든 로그 저장
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"[WARNING] 파일 로그 핸들러 설정 실패: {e}")
    
    # 콘솔 핸들러 설정
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_format)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        logger.addHandler(console_handler)
    
    # 로거 초기화 메시지
    logger.info(f"로깅 시스템 초기화 완료 - 레벨: {log_level}")
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    기존 로거 인스턴스 조회
    
    Args:
        name: 로거 이름 (None인 경우 기본 로거 반환)
        
    Returns:
        Logger 인스턴스
    """
    if name is None:
        name = "ptsd_chatbot"
    
    logger = logging.getLogger(name)
    
    # 로거가 설정되지 않은 경우 기본 설정으로 초기화
    if not logger.handlers:
        logger = setup_logger(name)
    
    return logger


def log_function_call(func_name: str, args: dict = None, logger: logging.Logger = None):
    """
    함수 호출 로깅 데코레이터 헬퍼
    
    Args:
        func_name: 함수명
        args: 함수 인자
        logger: 로거 인스턴스
    """
    if logger is None:
        logger = get_logger()
    
    args_str = f"with args: {args}" if args else ""
    logger.debug(f"함수 호출: {func_name}() {args_str}")


def log_user_action(user_id: str, action: str, details: dict = None, logger: logging.Logger = None):
    """
    사용자 행동 로깅
    
    Args:
        user_id: 사용자 ID
        action: 수행한 행동
        details: 상세 정보
        logger: 로거 인스턴스
    """
    if logger is None:
        logger = get_logger()
    
    details_str = f" - {details}" if details else ""
    logger.info(f"사용자 행동 | {user_id} | {action}{details_str}")


def log_error_with_context(error: Exception, context: str = "", logger: logging.Logger = None):
    """
    컨텍스트와 함께 에러 로깅
    
    Args:
        error: 발생한 예외
        context: 에러 발생 컨텍스트
        logger: 로거 인스턴스
    """
    if logger is None:
        logger = get_logger()
    
    context_str = f"[{context}] " if context else ""
    logger.error(f"{context_str}오류 발생: {type(error).__name__}: {str(error)}", exc_info=True)


def log_model_interaction(model_provider: str, model_name: str, input_tokens: int = None, 
                         output_tokens: int = None, response_time: float = None, 
                         logger: logging.Logger = None):
    """
    AI 모델 상호작용 로깅
    
    Args:
        model_provider: 모델 제공자 (ollama, openai)
        model_name: 모델명
        input_tokens: 입력 토큰 수
        output_tokens: 출력 토큰 수
        response_time: 응답 시간 (초)
        logger: 로거 인스턴스
    """
    if logger is None:
        logger = get_logger()
    
    details = []
    if input_tokens:
        details.append(f"입력토큰: {input_tokens}")
    if output_tokens:
        details.append(f"출력토큰: {output_tokens}")
    if response_time:
        details.append(f"응답시간: {response_time:.2f}s")
    
    details_str = f" | {' | '.join(details)}" if details else ""
    logger.info(f"AI 모델 호출 | {model_provider}:{model_name}{details_str}")


# 애플리케이션 전역 로거 생성 함수
def initialize_app_logging(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    애플리케이션 로깅 초기화
    
    Args:
        log_level: 로그 레벨
        log_dir: 로그 디렉토리
        
    Returns:
        메인 애플리케이션 로거
    """
    return setup_logger(
        name="ptsd_chatbot",
        log_level=log_level,
        log_dir=log_dir,
        enable_console=True,
        enable_file=True
    )