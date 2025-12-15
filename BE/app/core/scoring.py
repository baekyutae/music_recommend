"""
VibeCurator Scoring Utilities
Stage1.5 re-ranking + Stage3 하이브리드 스코어링
(recommend_model/stage3_hybrid_eval.ipynb와 동일한 로직)
"""

import numpy as np
from typing import List, Tuple, Dict, Optional


# =============================================================================
# 기본 유틸리티 함수
# =============================================================================

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """두 벡터의 코사인 유사도 계산"""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def batch_cosine_similarity(
    query_vec: np.ndarray,
    embeddings: np.ndarray
) -> np.ndarray:
    """
    쿼리 벡터와 임베딩 행렬 간의 코사인 유사도 계산
    
    Args:
        query_vec: (D,) 쿼리 벡터
        embeddings: (N, D) 임베딩 행렬
    
    Returns:
        (N,) 유사도 배열
    """
    # L2 정규화
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
    emb_norms = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
    
    # 내적으로 코사인 유사도 계산
    similarities = np.dot(emb_norms, query_norm)
    return similarities


def minmax_normalize(scores: np.ndarray) -> np.ndarray:
    """
    Min-Max 정규화 (0~1)
    - NaN을 제외한 값들에 대해 0~1 범위로 선형 정규화
    - 모든 값이 같으면(분산 0) → 0.5로 설정
    - NaN 위치는 0.0으로 채움 (오디오 임베딩이 없는 곡은 최소값 취급)
    """
    scores = np.asarray(scores, dtype=float)
    nan_mask = np.isnan(scores)
    
    # NaN이 아닌 값들만 추출
    valid_vals = scores[~nan_mask]
    
    if len(valid_vals) == 0:
        return np.zeros_like(scores)
    
    v_min = valid_vals.min()
    v_max = valid_vals.max()
    
    if v_max - v_min < 1e-8:
        # 모든 valid 값이 동일한 경우 → 0.5로 설정
        result = np.full_like(scores, 0.5)
    else:
        result = (scores - v_min) / (v_max - v_min)
    
    # NaN 위치는 0.0으로 채움
    result[nan_mask] = 0.0
    
    return result


# =============================================================================
# Stage1.5 Re-ranking 함수들 (아티스트 페널티, 장르 레일가드)
# =============================================================================

def get_genre_group(code: Optional[str]) -> str:
    """
    장르 코드를 그룹으로 변환
    특수 장르(트로트, CCM, 동요, 국악)는 별도 그룹으로 분류
    """
    if not isinstance(code, str) or not code:
        return "UNK"
    if code.startswith("GN07") or code.startswith("GN11"):
        return "TROT"
    if code == "GN1900" or code.startswith("GN19"):
        return "CCM"
    if code == "GN2200" or code.startswith("GN22"):
        return "KIDS"
    if code == "GN2400" or code.startswith("GN24"):
        return "GUGAK"
    if len(code) >= 4:
        return code[:4]
    return "UNK"


def apply_artist_penalty_soft(
    candidates: List[Dict],
    max_per_artist_soft: int = 3,
    penalty_per_extra: float = 0.05
) -> List[Dict]:
    """
    동일 아티스트(artist_key) 곡이 너무 많이 나오면 소프트 페널티를 부여합니다.
    
    Args:
        candidates: [{"song_id": int, "score_cf": float, "artist_key": str, ...}, ...]
        max_per_artist_soft: 이 개수까지는 페널티 없음
        penalty_per_extra: 초과 시 곡당 페널티
    
    Returns:
        score_after_artist가 추가된 candidates
    """
    if not candidates:
        return candidates
    
    # score_cf 기준 정렬
    sorted_candidates = sorted(candidates, key=lambda x: x.get("score_cf", 0), reverse=True)
    
    # 아티스트별 등장 순서 계산
    artist_counts: Dict[str, int] = {}
    
    for cand in sorted_candidates:
        artist_key = cand.get("artist_key", "UNKNOWN") or "UNKNOWN"
        order = artist_counts.get(artist_key, 0)
        artist_counts[artist_key] = order + 1
        
        # 페널티 계산
        if order < max_per_artist_soft:
            penalty = 0.0
        else:
            extra_count = order - max_per_artist_soft + 1
            penalty = extra_count * penalty_per_extra
        
        cand["artist_penalty_soft"] = penalty
        cand["score_after_artist"] = cand.get("score_cf", 0) - penalty
    
    return sorted_candidates


def apply_genre_railguard(
    candidates: List[Dict],
    seed_main_genre: str,
    offrail_penalty_general: float = 0.008,
    offrail_penalty_special: float = 0.03
) -> List[Dict]:
    """
    시드 곡과 장르가 다르면 페널티를 부여합니다.
    
    Args:
        candidates: score_after_artist가 있는 candidates
        seed_main_genre: 시드 곡의 메인 장르
        offrail_penalty_general: 일반 장르 불일치 페널티
        offrail_penalty_special: 특수 장르 불일치 페널티
    
    Returns:
        score_after_genre가 추가된 candidates
    """
    if not candidates:
        return candidates
    
    seed_genre_group = get_genre_group(seed_main_genre)
    special_groups = ["TROT", "CCM", "KIDS", "GUGAK"]
    
    for cand in candidates:
        if seed_genre_group == "UNK":
            cand["genre_penalty"] = 0.0
        else:
            cand_genre = cand.get("main_genre", "")
            cand_group = get_genre_group(cand_genre)
            
            if cand_group == seed_genre_group:
                cand["genre_penalty"] = 0.0
            elif seed_genre_group in special_groups and cand_group in special_groups:
                cand["genre_penalty"] = offrail_penalty_special
            elif (seed_genre_group in special_groups) != (cand_group in special_groups):
                cand["genre_penalty"] = offrail_penalty_general * 1.5
            else:
                cand["genre_penalty"] = offrail_penalty_general
        
        cand["score_after_genre"] = cand.get("score_after_artist", 0) - cand.get("genre_penalty", 0)
    
    return candidates


def apply_artist_hardcut(
    candidates: List[Dict],
    topk_final: int,
    max_per_artist_final: int = 2
) -> List[Dict]:
    """
    최종 결과에서 아티스트당 최대 곡 수를 제한합니다 (Hardcut).
    
    Args:
        candidates: score_after_genre가 있는 candidates
        topk_final: 최종 반환할 곡 수
        max_per_artist_final: 아티스트당 최대 곡 수
    
    Returns:
        필터링된 candidates
    """
    if not candidates:
        return candidates
    
    # score_after_genre (= score_final) 기준 정렬
    sorted_candidates = sorted(
        candidates, 
        key=lambda x: x.get("score_after_genre", x.get("score_cf", 0)), 
        reverse=True
    )
    
    selected = []
    artist_counts: Dict[str, int] = {}
    
    for cand in sorted_candidates:
        if len(selected) >= topk_final:
            break
        
        artist_key = cand.get("artist_key", "UNKNOWN") or "UNKNOWN"
        current_count = artist_counts.get(artist_key, 0)
        
        if current_count < max_per_artist_final:
            # score_final 설정
            cand["score_final"] = cand.get("score_after_genre", cand.get("score_cf", 0))
            selected.append(cand)
            artist_counts[artist_key] = current_count + 1
    
    return selected


def apply_stage1_5_reranking(
    candidates: List[Dict],
    seed_main_genre: str,
    topk_final: int,
    max_per_artist_soft: int = 3,
    max_per_artist_final: int = 2,
    penalty_per_extra: float = 0.05,
    offrail_penalty_general: float = 0.008,
    offrail_penalty_special: float = 0.03
) -> List[Dict]:
    """
    Stage1.5 전체 re-ranking 파이프라인
    CF 후보 -> 아티스트 페널티(Soft) -> 장르 레일가드 -> 아티스트 하드컷
    
    Args:
        candidates: [{"song_id": int, "score_cf": float, "artist_key": str, "main_genre": str, ...}, ...]
        seed_main_genre: 시드 곡의 메인 장르
        topk_final: 최종 반환할 곡 수
        max_per_artist_soft: 소프트 페널티 임계값
        max_per_artist_final: 하드컷 임계값
        penalty_per_extra: 아티스트 초과 시 곡당 페널티
        offrail_penalty_general: 일반 장르 불일치 페널티
        offrail_penalty_special: 특수 장르 불일치 페널티
    
    Returns:
        re-ranking된 candidates (score_final 기준 정렬)
    """
    if not candidates:
        return candidates
    
    # 1. 아티스트 페널티 (Soft)
    candidates = apply_artist_penalty_soft(
        candidates,
        max_per_artist_soft=max_per_artist_soft,
        penalty_per_extra=penalty_per_extra
    )
    
    # 2. 장르 레일가드
    candidates = apply_genre_railguard(
        candidates,
        seed_main_genre=seed_main_genre,
        offrail_penalty_general=offrail_penalty_general,
        offrail_penalty_special=offrail_penalty_special
    )
    
    # 3. 아티스트 하드컷
    candidates = apply_artist_hardcut(
        candidates,
        topk_final=topk_final,
        max_per_artist_final=max_per_artist_final
    )
    
    return candidates


# =============================================================================
# Stage3 하이브리드 스코어링
# =============================================================================

def compute_hybrid_scores(
    cf_candidates: List[Dict],
    audio_scores: Dict[int, float],
    alpha: float = 0.7,
    beta: float = 0.3
) -> List[Tuple[int, float]]:
    """
    CF+메타 점수와 오디오 점수를 결합한 하이브리드 점수 계산
    (recommend_model/stage3_hybrid_eval.ipynb의 rerank_with_audio와 동일)
    
    Args:
        cf_candidates: Stage1.5 결과 [{"song_id": int, "score_final": float, ...}, ...]
        audio_scores: {song_id: audio_similarity} 오디오 유사도 딕셔너리 (이미 계산된 raw 값)
        alpha: CF+메타 점수 가중치 (기본 0.7)
        beta: 오디오 유사도 가중치 (기본 0.3)
    
    Returns:
        [(song_id, hybrid_score), ...] 하이브리드 점수 리스트 (내림차순 정렬)
    """
    if not cf_candidates:
        return []
    
    # 1. CF+메타 점수 추출 (score_final 사용)
    song_ids = [cand["song_id"] for cand in cf_candidates]
    cf_raw_scores = np.array([cand.get("score_final", cand.get("score_cf", 0)) for cand in cf_candidates])
    
    # 2. 오디오 점수 추출 (없으면 NaN)
    audio_raw_scores = np.array([
        audio_scores.get(sid, np.nan) for sid in song_ids
    ])
    
    # 3. Min-Max 정규화
    cf_normalized = minmax_normalize(cf_raw_scores)
    audio_normalized = minmax_normalize(audio_raw_scores)
    
    # 4. 하이브리드 점수 계산
    hybrid_scores = alpha * cf_normalized + beta * audio_normalized
    
    # 5. 결과 생성 및 정렬
    results = [(sid, float(score)) for sid, score in zip(song_ids, hybrid_scores)]
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results
