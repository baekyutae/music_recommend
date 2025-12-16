"""
VibeCurator Backend Configuration
환경변수 기반 설정 관리
"""

import os
from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field

#Field()는 pydantic 라이브러리에서 제공하는 함수이고,
# pydantic 모델/설정 클래스에서 필드 설정(기본값, 범위, 설명 등)을 할 때 쓰는 함수

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Engine settings
    ENGINE_VERSION: str = Field(default="stage3_v1_myna", description="추천 엔진 버전")
    AUDIO_MODEL: Literal["myna", "cnn"] = Field(default="myna", description="오디오 모델 종류")
    DEFAULT_K: int = Field(default=20, ge=1, le=100, description="기본 추천 개수")
    CANDIDATE_TOPN: int = Field(default=200, ge=10, description="CF 후보 개수")
    ALPHA_AUDIO: float = Field(default=0.3, ge=0.0, le=1.0, description="오디오 점수 가중치 (beta)")
    
    # Stage1.5 Re-ranking settings
    MAX_PER_ARTIST_SOFT: int = Field(default=3, ge=1, description="소프트 페널티 임계값")
    MAX_PER_ARTIST_FINAL: int = Field(default=2, ge=1, description="하드컷 임계값")
    PENALTY_PER_EXTRA: float = Field(default=0.05, ge=0.0, description="아티스트 초과 시 곡당 페널티")
    OFFRAIL_PENALTY_GENERAL: float = Field(default=0.008, ge=0.0, description="일반 장르 불일치 페널티")
    OFFRAIL_PENALTY_SPECIAL: float = Field(default=0.03, ge=0.0, description="특수 장르 불일치 페널티")
    STAGE3_CANDIDATES: int = Field(default=200, ge=10, description="하이브리드 계산 전 후보 수")
    
    # Mode settings
    DEMO_MODE: bool = Field(default=True, description="데모 모드 (실제 모델 없이 동작)")
    
    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis 연결 URL")
    CACHE_TTL_SEC: int = Field(default=900, ge=0, description="캐시 TTL (초)")
    
    # File paths
    SONG_META_PATH: str = Field(
        default="",
        description="메인 메타데이터 JSON 경로 (song_meta.json, CF 후보 필터링용)"
    )
    SONG_META_AUDIO_PATH: str = Field(
        default="",
        description="오디오 메타데이터 JSON 경로 (audio_embedding_songs_metadata.json, 선택)"
    )
    ITEM2VEC_PATH: str = Field(default="", description="Item2Vec 모델 경로")
    AUDIO_EMB_MYNA_PATH: str = Field(default="", description="Myna 오디오 임베딩 경로")
    AUDIO_EMB_CNN_PATH: str = Field(default="", description="CNN 오디오 임베딩 경로")
    
    # Settings 모델이 환경변수를 어떻게 읽을지 규칙을 알려주는 설정 클래스
    class Config:
        env_file = ".env" # 현재 디렉터리의 .env 파일을 읽어서 환경변수처럼 사용해라
        env_file_encoding = "utf-8"
        case_sensitive = True # 환경변수 이름의 대소문자를 구분

# Settings 인스턴스를 돌려주는 함수 
def get_settings() -> Settings:
    
    return Settings()

