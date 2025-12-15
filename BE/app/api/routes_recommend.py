"""
VibeCurator Recommendation API
추천 라우터
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Query

from ..schemas.recommend import RecommendResponse, SeedInfo, RecommendItem
from ..schemas.common import ErrorResponse
from ..core.cache import make_recommend_cache_key, get_json, set_json

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recommend"])


@router.get(
    "/recommend",
    response_model=RecommendResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Seed not found"},
        503: {"model": ErrorResponse, "description": "Resources not loaded"}
    }
)
async def recommend(
    request: Request,
    seed_id: int = Query(..., description="시드 곡 ID"),
    k: int = Query(default=20, ge=1, le=100, description="추천 개수")
) -> RecommendResponse:
    """
    곡 추천
    
    - seed_id: 시드 곡 ID
    - k: 추천 개수 (1~100, 기본값 20)
    
    캐시가 있으면 캐시에서 반환, 없으면 엔진으로 계산 후 캐시 저장
    """
    state = request.app.state
    config = state.config
    
    # 엔진 확인
    if state.engine is None:
        raise HTTPException(status_code=503, detail="Recommendation engine not initialized")
    
    # 캐시 키 생성
    cache_key = make_recommend_cache_key(
        engine_version=config.ENGINE_VERSION,
        audio_model=config.AUDIO_MODEL,
        seed_id=seed_id,
        k=k
    )
    
    # 캐시 조회
    cached_data = get_json(state.redis_cache, cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit: {cache_key}")
        return RecommendResponse(
            engine_version=config.ENGINE_VERSION,
            audio_model=config.AUDIO_MODEL,
            cached=True,
            method=cached_data.get("method", "unknown"),
            seed=SeedInfo(**cached_data["seed"]),
            items=[RecommendItem(**item) for item in cached_data["items"]]
        )
    
    # 추천 실행
    try:
        result = state.engine.recommend(seed_id=seed_id, k=k)
    except ValueError as e:
        # 시드 없음
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # 리소스 문제
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    # 응답 생성
    response = RecommendResponse(
        engine_version=config.ENGINE_VERSION,
        audio_model=config.AUDIO_MODEL,
        cached=False,
        method=result["method"],
        seed=SeedInfo(**result["seed"]),
        items=[RecommendItem(**item) for item in result["items"]]
    )
    
    # 캐시 저장
    cache_data = {
        "method": result["method"],
        "seed": result["seed"],
        "items": result["items"]
    }
    set_json(state.redis_cache, cache_key, cache_data, config.CACHE_TTL_SEC)
    
    return response

