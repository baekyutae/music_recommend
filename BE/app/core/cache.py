"""
VibeCurator Redis Cache
추천 결과 JSON 캐싱
"""

import json
import logging
from typing import Optional, Any

import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 캐시 클라이언트"""
    
    def __init__(self, redis_url: str):
        """
        Args:
            redis_url: Redis 연결 URL (예: redis://localhost:6379/0)
        """
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._connected = False
        self._connect()
    
    def _connect(self) -> None:
        """Redis 연결 시도"""
        try:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 연결 테스트
            self._client.ping()
            self._connected = True
            logger.info(f"Redis 연결 성공: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis 연결 실패 (캐시 없이 진행): {e}")
            self._connected = False
            self._client = None
    
    @property
    def is_connected(self) -> bool:
        """Redis 연결 상태"""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    def ping(self) -> bool:
        """Redis ping 테스트"""
        return self.is_connected


def make_recommend_cache_key(
    engine_version: str,
    audio_model: str,
    seed_id: int,
    k: int
) -> str:
    """
    추천 결과 캐시 키 생성
    
    형식: rec:{engine_version}:{audio_model}:seed:{seed_id}:k:{k}
    """
    return f"rec:{engine_version}:{audio_model}:seed:{seed_id}:k:{k}"


def get_json(cache: Optional[RedisCache], key: str) -> Optional[dict]:
    """
    캐시에서 JSON 조회
    
    Args:
        cache: RedisCache 인스턴스 (None이면 None 반환)
        key: 캐시 키
    
    Returns:
        파싱된 JSON 딕셔너리 또는 None
    """
    if cache is None or not cache.is_connected:
        return None
    
    try:
        data = cache._client.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"캐시 조회 실패: {e}")
    
    return None


def set_json(
    cache: Optional[RedisCache],
    key: str,
    value: dict,
    ttl_sec: int
) -> None:
    """
    캐시에 JSON 저장
    
    Args:
        cache: RedisCache 인스턴스 (None이면 무시)
        key: 캐시 키
        value: 저장할 딕셔너리
        ttl_sec: TTL (초)
    """
    if cache is None or not cache.is_connected:
        return
    
    try:
        data = json.dumps(value, ensure_ascii=False)
        cache._client.setex(key, ttl_sec, data)
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {e}")

