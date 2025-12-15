"""
VibeCurator Recommendation Engine
Stage3 하이브리드 추천 엔진
(recommend_model/stage3_hybrid_eval.ipynb와 동일한 로직)
"""

import logging
from typing import List, Dict, Any, Optional, Set

import numpy as np

from .loaders import MetaRegistry, AudioBundle, SongMeta
from .scoring import (
    batch_cosine_similarity,
    minmax_normalize,
    apply_stage1_5_reranking,
    compute_hybrid_scores
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Stage3 하이브리드 추천 엔진
    
    추천 파이프라인:
    1. Item2Vec으로 CF 후보 생성 (topn_cf개)
    2. Stage1.5 re-ranking (아티스트 페널티 + 장르 레일가드 + 아티스트 하드컷)
    3. 오디오 임베딩 유사도 계산
    4. 하이브리드 스코어링 (CF+메타 0.7 + 오디오 0.3)
    """
    
    def __init__(
        self,
        meta_registry: MetaRegistry,
        item2vec_model: Optional[Any] = None,
        audio_bundle: Optional[AudioBundle] = None,
        demo_mode: bool = True,
        candidate_topn: int = 200,
        alpha_audio: float = 0.3,
        # Stage1.5 re-ranking 파라미터
        max_per_artist_soft: int = 3,
        max_per_artist_final: int = 2,
        penalty_per_extra: float = 0.05,
        offrail_penalty_general: float = 0.008,
        offrail_penalty_special: float = 0.03,
        # Stage3 하이브리드 파라미터
        stage3_candidates: int = 200  # 하이브리드 계산 전 후보 수
    ):
        """
        Args:
            meta_registry: 메타데이터 레지스트리
            item2vec_model: Item2Vec 모델 (gensim Word2Vec)
            audio_bundle: 오디오 임베딩 번들
            demo_mode: 데모 모드
            candidate_topn: CF 후보 개수 (topn_cf)
            alpha_audio: 오디오 점수 가중치 (beta in stage3, 기본 0.3)
            max_per_artist_soft: 소프트 페널티 임계값
            max_per_artist_final: 하드컷 임계값
            penalty_per_extra: 아티스트 초과 시 곡당 페널티
            offrail_penalty_general: 일반 장르 불일치 페널티
            offrail_penalty_special: 특수 장르 불일치 페널티
            stage3_candidates: 하이브리드 계산 전 후보 수
        """
        self.meta = meta_registry
        self.item2vec = item2vec_model
        self.audio = audio_bundle
        self.demo_mode = demo_mode
        self.candidate_topn = candidate_topn
        
        # Stage3 하이브리드 가중치 (alpha=CF+메타, beta=오디오)
        self.alpha_cf = 1.0 - alpha_audio  # 0.7
        self.beta_audio = alpha_audio       # 0.3
        
        # Stage1.5 re-ranking 파라미터
        self.max_per_artist_soft = max_per_artist_soft
        self.max_per_artist_final = max_per_artist_final
        self.penalty_per_extra = penalty_per_extra
        self.offrail_penalty_general = offrail_penalty_general
        self.offrail_penalty_special = offrail_penalty_special
        self.stage3_candidates = stage3_candidates
        
        # 메타에 있는 곡 ID 집합 (빠른 조회용)
        # meta_registry는 이제 song_meta.json 기준 (meta_full)
        self._meta_song_ids: Set[int] = set(meta_registry.song_ids)
        
        # Item2Vec vocab (str 키)
        self._vocab_set: Set[str] = set()
        if item2vec_model is not None:
            self._vocab_set = set(item2vec_model.wv.key_to_index.keys())
        
        logger.info(
            f"Engine 초기화: demo={demo_mode}, "
            f"meta={len(self._meta_song_ids)}, "
            f"vocab={len(self._vocab_set)}, "
            f"audio={'loaded' if audio_bundle else 'none'}, "
            f"alpha_cf={self.alpha_cf}, beta_audio={self.beta_audio}"
        )
    
    def _get_seed_meta(self, seed_id: int) -> Optional[SongMeta]:
        """시드 곡 메타데이터 조회"""
        return self.meta.songs.get(seed_id)
    
    def _demo_recommend(self, seed_id: int, k: int) -> List[Dict]:
        """
        데모 모드 추천 (결정적)
        seed_id를 기반으로 해시하여 항상 같은 결과 반환
        """
        # seed_id 기반 결정적 정렬
        candidates = [sid for sid in self.meta.song_ids if sid != seed_id]
        
        # 해시 기반 정렬 (결정적)
        def score_fn(sid: int) -> int:
            return (sid * 31 + seed_id) % 1000000
        
        candidates.sort(key=score_fn)
        top_k = candidates[:k]
        
        results = []
        for rank, sid in enumerate(top_k, 1):
            meta = self.meta.songs.get(sid)
            if meta:
                results.append({
                    "rank": rank,
                    "song_id": sid,
                    "song_name": meta.song_name,
                    "artist": meta.artist,
                    "genre": meta.genre,
                    "score": 1.0 - (rank - 1) * 0.01  # 가상 점수
                })
        
        return results
    
    def _get_cf_candidates_raw(self, seed_id: int, topn: int) -> List[Dict]:
        """
        Item2Vec으로 CF 후보 생성 (Stage1 순수 CF)
        메타데이터와 결합하여 반환
        
        Returns:
            [{"song_id": int, "score_cf": float, "artist_key": str, "main_genre": str, ...}, ...]
        """
        if self.item2vec is None:
            return []
        
        seed_key = str(seed_id)
        if seed_key not in self._vocab_set:
            return []
        
        try:
            # most_similar 호출 (topn + 여유분)
            similar = self.item2vec.wv.most_similar(seed_key, topn=topn + 50)
            
            results = []
            for key, score in similar:
                try:
                    sid = int(key)
                except ValueError:
                    continue
                
                # 자기 자신 제외
                if sid == seed_id:
                    continue
                
                # 메타에 있는 곡만
                if sid not in self._meta_song_ids:
                    continue
                
                meta = self.meta.songs.get(sid)
                if meta is None:
                    continue
                
                # genre가 ", "로 join된 경우 첫 번째 장르만 사용 (re-ranking용)
                main_genre = meta.genre.split(", ")[0] if meta.genre and ", " in meta.genre else (meta.genre or "")
                
                results.append({
                    "song_id": sid,
                    "score_cf": float(score),
                    "song_name": meta.song_name,
                    "artist_str": meta.artist,
                    "main_genre": main_genre,
                    "issue_year": meta.issue_year,
                    "artist_key": meta.artist_key or "UNKNOWN"
                })
                
                if len(results) >= topn:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"CF 후보 생성 실패: {e}")
            return []
    
    def _get_cf_candidates_with_rerank(self, seed_id: int, topk_final: int) -> List[Dict]:
        """
        Stage1.5: CF 후보 추출 -> 아티스트 페널티 -> 장르 레일가드 -> 아티스트 하드컷
        
        Returns:
            re-ranking된 후보 리스트
        """
        # 1. CF 후보 추출
        candidates = self._get_cf_candidates_raw(seed_id, self.candidate_topn)
        
        if not candidates:
            return []
        
        # 2. Seed 정보 조회
        seed_meta = self._get_seed_meta(seed_id)
        # genre가 ", "로 join된 경우 첫 번째 장르만 사용
        if seed_meta and seed_meta.genre:
            seed_main_genre = seed_meta.genre.split(", ")[0] if ", " in seed_meta.genre else seed_meta.genre
        else:
            seed_main_genre = "UNK"
        
        # 3. Stage1.5 re-ranking 적용
        reranked = apply_stage1_5_reranking(
            candidates=candidates,
            seed_main_genre=seed_main_genre,
            topk_final=topk_final,
            max_per_artist_soft=self.max_per_artist_soft,
            max_per_artist_final=self.max_per_artist_final,
            penalty_per_extra=self.penalty_per_extra,
            offrail_penalty_general=self.offrail_penalty_general,
            offrail_penalty_special=self.offrail_penalty_special
        )
        
        return reranked
    
    def _compute_audio_scores(
        self,
        seed_id: int,
        candidate_ids: List[int]
    ) -> Dict[int, float]:
        """
        오디오 임베딩 기반 유사도 점수 계산 (raw cosine similarity)
        
        Returns:
            {song_id: cosine_similarity}
        """
        if self.audio is None:
            return {}
        
        # 시드 임베딩
        if seed_id not in self.audio.song_id_to_idx:
            return {}
        
        seed_idx = self.audio.song_id_to_idx[seed_id]
        seed_emb = self.audio.embeddings[seed_idx]
        
        # 후보 임베딩 수집
        valid_candidates = []
        valid_indices = []
        for sid in candidate_ids:
            if sid in self.audio.song_id_to_idx:
                valid_candidates.append(sid)
                valid_indices.append(self.audio.song_id_to_idx[sid])
        
        if not valid_candidates:
            return {}
        
        # 배치 코사인 유사도 (raw values)
        candidate_embs = self.audio.embeddings[valid_indices]
        similarities = batch_cosine_similarity(seed_emb, candidate_embs)
        
        return {sid: float(similarities[i]) for i, sid in enumerate(valid_candidates)}
    
    def recommend(self, seed_id: int, k: int) -> Dict[str, Any]:
        """
        추천 실행 (Stage3 하이브리드)
        
        파이프라인:
        1. CF 후보 생성 (topn_cf개)
        2. Stage1.5 re-ranking (stage3_candidates개로 축소)
        3. 오디오 유사도 계산
        4. 하이브리드 스코어링 (CF+메타 0.7 + 오디오 0.3)
        5. Top-K 반환
        
        Args:
            seed_id: 시드 곡 ID
            k: 추천 개수
        
        Returns:
            {
                "seed": {...},
                "items": [...],
                "method": "demo" | "cf_only" | "hybrid"
            }
        
        Raises:
            ValueError: 시드가 메타에 없는 경우
            RuntimeError: 리소스 미로드 상태
        """
        # 시드 메타 확인
        seed_meta = self._get_seed_meta(seed_id)
        if seed_meta is None:
            raise ValueError(f"Seed not found in metadata: {seed_id}")
        
        seed_info = {
            "song_id": seed_id,
            "song_name": seed_meta.song_name,
            "artist": seed_meta.artist,
            "genre": seed_meta.genre
        }
        
        # 데모 모드
        if self.demo_mode:
            items = self._demo_recommend(seed_id, k)
            return {
                "seed": seed_info,
                "items": items,
                "method": "demo"
            }
        
        # ========================================
        # Stage3 하이브리드 추천
        # ========================================
        
        # 1) Stage1.5: CF 후보 + re-ranking
        cf_candidates = self._get_cf_candidates_with_rerank(seed_id, self.stage3_candidates)
        
        if not cf_candidates:
            # CF 실패 (vocab에 없음)
            if str(seed_id) not in self._vocab_set:
                raise ValueError(f"Seed not in Item2Vec vocabulary: {seed_id}")
            raise RuntimeError("CF candidate generation failed")
        
        # 2) 오디오 유사도 계산 (raw cosine similarity)
        candidate_ids = [cand["song_id"] for cand in cf_candidates]
        audio_scores = self._compute_audio_scores(seed_id, candidate_ids)
        
        # 3) 하이브리드 스코어링
        if audio_scores:
            # Stage3: CF+메타(0.7) + 오디오(0.3) 결합
            hybrid_results = compute_hybrid_scores(
                cf_candidates=cf_candidates,
                audio_scores=audio_scores,
                alpha=self.alpha_cf,   # 0.7
                beta=self.beta_audio   # 0.3
            )
            method = "hybrid"
        else:
            # 오디오 없으면 CF+메타 only (Stage1.5 결과 그대로)
            hybrid_results = [
                (cand["song_id"], cand.get("score_final", cand.get("score_cf", 0)))
                for cand in cf_candidates
            ]
            method = "cf_only"
        
        # 4) Top-K 결과 생성
        items = []
        for rank, (sid, score) in enumerate(hybrid_results[:k], 1):
            meta = self.meta.songs.get(sid)
            if meta:
                items.append({
                    "rank": rank,
                    "song_id": sid,
                    "song_name": meta.song_name,
                    "artist": meta.artist,
                    "genre": meta.genre,
                    "score": round(score, 6)
                })
        
        return {
            "seed": seed_info,
            "items": items,
            "method": method
        }
