"""
VibeCurator Backend Main Application
FastAPI 앱 및 startup/shutdown 이벤트
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings, Settings
from .core.loaders import (
    load_audio_song_meta,
    load_song_meta_melon,
    load_item2vec_model,
    load_audio_embeddings,
    MetaRegistry,
    AudioBundle
)
from .core.engine import RecommendationEngine
from .core.cache import RedisCache
from .api import routes_health, routes_songs, routes_recommend
from .utils.logging import setup_logging

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 라이프사이클 관리"""
    # Startup
    logger.info("=" * 60)
    logger.info("VibeCurator Backend Starting...")
    logger.info("=" * 60)
    
    # 설정 로드
    config = get_settings()
    app.state.config = config
    
    logger.info(f"Engine Version: {config.ENGINE_VERSION}")
    logger.info(f"Audio Model: {config.AUDIO_MODEL}")
    logger.info(f"Demo Mode: {config.DEMO_MODE}")
    
    # 1. song_meta.json 로드 (CF 후보 필터링용)
    meta_full_path = config.SONG_META_PATH
    if not meta_full_path:
        # 기본 경로 시도
        default_path = Path(__file__).parent.parent.parent / "melon-dataset-excepttar" / "song_meta.json"
        if default_path.exists():
            meta_full_path = str(default_path)
            logger.info(f"Using default song_meta path: {meta_full_path}")
    
    try:
        app.state.meta_full = load_song_meta_melon(meta_full_path, config.DEMO_MODE)
        app.state.meta_full_loaded = True
    except Exception as e:
        logger.error(f"Failed to load song_meta.json: {e}")
        app.state.meta_full = None
        app.state.meta_full_loaded = False
    
    # 2. audio_embedding_songs_metadata.json 로드 (선택, 보조용)
    meta_audio_path = config.SONG_META_AUDIO_PATH
    if not meta_audio_path:
        # 기본 경로 시도
        default_path = Path(__file__).parent.parent.parent / "recommend_model" / "audio_embedding_songs_metadata.json"
        if default_path.exists():
            meta_audio_path = str(default_path)
            logger.info(f"Using default audio meta path: {meta_audio_path}")
    
    try:
        app.state.meta_audio = load_audio_song_meta(meta_audio_path, config.DEMO_MODE)
        app.state.meta_audio_loaded = True
    except Exception as e:
        logger.warning(f"Failed to load audio metadata (optional): {e}")
        app.state.meta_audio = None
        app.state.meta_audio_loaded = False
    
    # 3. Item2Vec 모델 로드
    app.state.item2vec_model = load_item2vec_model(config.ITEM2VEC_PATH)
    app.state.item2vec_loaded = app.state.item2vec_model is not None
    
    # 4. 오디오 임베딩 로드
    app.state.audio_bundle = load_audio_embeddings(
        audio_model=config.AUDIO_MODEL,
        myna_path=config.AUDIO_EMB_MYNA_PATH,
        cnn_path=config.AUDIO_EMB_CNN_PATH
    )
    app.state.audio_loaded = app.state.audio_bundle is not None
    
    # Redis 캐시 초기화
    try:
        app.state.redis_cache = RedisCache(config.REDIS_URL)
    except Exception as e:
        logger.warning(f"Redis initialization failed: {e}")
        app.state.redis_cache = None
    
    # 추천 엔진 초기화 (Stage3 하이브리드)
    # meta_full(song_meta.json)을 메인 메타데이터로 사용
    if app.state.meta_full is not None:
        app.state.engine = RecommendationEngine(
            meta_registry=app.state.meta_full,
            item2vec_model=app.state.item2vec_model,
            audio_bundle=app.state.audio_bundle,
            demo_mode=config.DEMO_MODE,
            candidate_topn=config.CANDIDATE_TOPN,
            alpha_audio=config.ALPHA_AUDIO,
            # Stage1.5 re-ranking 파라미터
            max_per_artist_soft=config.MAX_PER_ARTIST_SOFT,
            max_per_artist_final=config.MAX_PER_ARTIST_FINAL,
            penalty_per_extra=config.PENALTY_PER_EXTRA,
            offrail_penalty_general=config.OFFRAIL_PENALTY_GENERAL,
            offrail_penalty_special=config.OFFRAIL_PENALTY_SPECIAL,
            stage3_candidates=config.STAGE3_CANDIDATES
        )
        logger.info(f"Engine initialized with Stage3 hybrid (alpha_cf={1-config.ALPHA_AUDIO}, beta_audio={config.ALPHA_AUDIO})")
    else:
        app.state.engine = None
        logger.warning("Engine not initialized (no song_meta.json)")
    
    logger.info("=" * 60)
    logger.info("VibeCurator Backend Ready!")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("VibeCurator Backend Shutting down...")


# FastAPI 앱 생성
app = FastAPI(
    title="VibeCurator API",
    description="음악 추천 서비스 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(routes_health.router)
app.include_router(routes_songs.router)
app.include_router(routes_recommend.router)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "VibeCurator API",
        "version": "1.0.0",
        "docs": "/docs"
    }

