"""
VibeCurator Health Check API
헬스 체크 라우터
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str
    engine_version: str
    audio_model: str
    demo_mode: bool
    meta_full_loaded: bool
    meta_full_count: int
    meta_audio_loaded: bool
    meta_audio_count: int
    item2vec_loaded: bool
    audio_loaded: bool
    audio_model_type: Optional[str] = None
    redis_connected: bool


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """
    서버 상태 확인
    
    - 엔진 버전 및 오디오 모델 정보
    - 리소스 로드 상태 (메타, Item2Vec, 오디오 임베딩)
    - Redis 연결 상태
    """
    state = request.app.state
    config = state.config
    
    # 메타 상태 (song_meta.json)
    meta_full_loaded = getattr(state, 'meta_full_loaded', False)
    meta_full_count = len(state.meta_full.songs) if state.meta_full is not None else 0
    
    # 메타 상태 (audio_embedding_songs_metadata.json, 선택)
    meta_audio_loaded = getattr(state, 'meta_audio_loaded', False)
    meta_audio_count = len(state.meta_audio.songs) if state.meta_audio is not None else 0
    
    # Item2Vec 상태
    item2vec_loaded = getattr(state, 'item2vec_loaded', False)
    
    # 오디오 임베딩 상태
    audio_loaded = getattr(state, 'audio_loaded', False)
    audio_model_type = state.audio_bundle.model_type if state.audio_bundle is not None else None
    
    # Redis 상태
    redis_connected = False
    if state.redis_cache is not None:
        redis_connected = state.redis_cache.ping()
    
    # 전체 상태 결정 (meta_full이 필수)
    if meta_full_loaded:
        status = "ok"
    else:
        status = "degraded"
    
    return HealthResponse(
        status=status,
        engine_version=config.ENGINE_VERSION,
        audio_model=config.AUDIO_MODEL,
        demo_mode=config.DEMO_MODE,
        meta_full_loaded=meta_full_loaded,
        meta_full_count=meta_full_count,
        meta_audio_loaded=meta_audio_loaded,
        meta_audio_count=meta_audio_count,
        item2vec_loaded=item2vec_loaded,
        audio_loaded=audio_loaded,
        audio_model_type=audio_model_type,
        redis_connected=redis_connected
    )

