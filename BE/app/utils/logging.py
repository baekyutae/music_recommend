"""
VibeCurator Logging Configuration
로깅 설정
"""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """로깅 설정"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        # 로그를 어디로 보낼지” 정하는 부분
        handlers=[
            logging.StreamHandler(sys.stdout) # 표준 출력(터미널) 로 로그 보냄
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """로거 반환"""
    return logging.getLogger(name)

