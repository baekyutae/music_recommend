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
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """로거 반환"""
    return logging.getLogger(name)

