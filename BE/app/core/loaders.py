"""
VibeCurator Data Loaders
메타데이터, Item2Vec 모델, 오디오 임베딩 로더
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SongMeta:
    """곡 메타데이터"""
    song_id: int
    song_name: str
    artist: str
    genre: str  # main_genre (첫 번째 장르 코드)
    issue_year: Optional[int] = None
    artist_key: Optional[str] = None  # artist_id_basket[0] 또는 "UNKNOWN"


@dataclass
class MetaRegistry:
    """메타데이터 레지스트리"""
    songs: Dict[int, SongMeta]
    song_ids: List[int]
    search_index: List[Tuple[int, str]]  # (song_id, normalized_text)


@dataclass
class AudioBundle:
    """오디오 임베딩 번들"""
    song_ids: np.ndarray
    embeddings: np.ndarray
    song_id_to_idx: Dict[int, int]
    model_type: str  # "myna" or "cnn"


def _normalize_text(text: str) -> str:
    """검색용 텍스트 정규화"""
    return text.lower().strip()


def _extract_field(item: Dict, candidates: List[str], default: str = "") -> str:
    """여러 후보 키에서 필드 추출"""
    for key in candidates:
        if key in item:
            val = item[key]
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val) if val else default
    return default


def _parse_year(value: Any) -> Optional[int]:
    """연도 파싱"""
    if value is None:
        return None
    try:
        s = str(value)
        if len(s) >= 4:
            return int(s[:4])
    except (ValueError, TypeError):
        pass
    return None


def load_song_meta_melon(path: str, demo_mode: bool) -> MetaRegistry:
    """
    Melon song_meta.json 로드 (CF 후보 필터링용)
    
    Args:
        path: JSON 파일 경로
        demo_mode: 데모 모드 여부 (파일 없으면 더미 생성)
    
    Returns:
        MetaRegistry: 메타데이터 레지스트리
    """
    songs: Dict[int, SongMeta] = {}
    song_ids: List[int] = []
    search_index: List[Tuple[int, str]] = []
    
    file_path = Path(path) if path else None
    
    # 파일 로드 시도
    if file_path and file_path.exists():
        try:
            logger.info(f"Melon 메타데이터 로드 중: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 구조 파악: 리스트 또는 딕셔너리
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # 딕셔너리인 경우 values 사용
                if all(isinstance(v, dict) for v in data.values()):
                    items = list(data.values())
                else:
                    items = [data]
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                # song_id 추출 (id 또는 song_id)
                sid_raw = item.get("id") or item.get("song_id") or item.get("sid")
                if sid_raw is None:
                    continue
                try:
                    sid = int(sid_raw)
                except (ValueError, TypeError):
                    continue
                
                # song_name 추출
                song_name = _extract_field(
                    item,
                    ["song_name", "title", "name", "track_name"],
                    default="Unknown"
                )
                
                # artist 추출 (artist_name_basket 처리)
                artist = ""
                if "artist_name_basket" in item:
                    artist_list = item["artist_name_basket"]
                    if isinstance(artist_list, list):
                        artist = ", ".join(str(a) for a in artist_list if a)
                    else:
                        artist = str(artist_list) if artist_list else ""
                else:
                    artist = _extract_field(
                        item,
                        ["artist", "artist_name", "artists"],
                        default="Unknown"
                    )
                
                # genre 추출 (song_gn_gnr_basket 또는 song_gn_dtl_gnr_basket)
                genre = ""
                genre_raw = item.get("song_gn_gnr_basket") or item.get("song_gn_dtl_gnr_basket")
                if genre_raw:
                    if isinstance(genre_raw, list):
                        genre = ", ".join(str(g) for g in genre_raw if g)
                    else:
                        genre = str(genre_raw)
                else:
                    genre = _extract_field(item, ["genre", "genres"], default="")
                
                # issue_year 추출 (issue_date에서 YYYYMMDD 파싱)
                issue_year = None
                issue_date = item.get("issue_date") or item.get("issue_year")
                if issue_date:
                    issue_year = _parse_year(issue_date)
                
                # artist_key 추출 (artist_id_basket[0])
                artist_key = "UNKNOWN"
                artist_id_basket = item.get("artist_id_basket")
                if isinstance(artist_id_basket, list) and len(artist_id_basket) > 0:
                    artist_key = str(artist_id_basket[0])
                elif artist_id_basket:
                    artist_key = str(artist_id_basket)
                
                # 중복 song_id 스킵
                if sid in songs:
                    logger.debug(f"중복 song_id 스킵: {sid}")
                    continue
                
                meta = SongMeta(
                    song_id=sid,
                    song_name=song_name,
                    artist=artist,
                    genre=genre,
                    issue_year=issue_year,
                    artist_key=artist_key
                )
                songs[sid] = meta
                song_ids.append(sid)
                
                # 검색 인덱스
                search_text = _normalize_text(f"{song_name} {artist}")
                search_index.append((sid, search_text))
            
            logger.info(f"Melon 메타데이터 로드 완료: {len(songs):,}곡")
            
        except Exception as e:
            logger.error(f"Melon 메타데이터 로드 실패: {e}")
            if not demo_mode:
                raise RuntimeError(f"Melon 메타데이터 로드 실패: {e}")
    
    # 데모 모드: 더미 데이터 생성
    if not songs and demo_mode:
        logger.warning("데모 모드: 더미 메타데이터 생성")
        demo_genres = ["GN0100", "GN0200", "GN0300", "GN0400", "GN0500"]
        for i in range(1, 5001):
            meta = SongMeta(
                song_id=i,
                song_name=f"Demo Song {i}",
                artist=f"Demo Artist {i % 100}",
                genre=demo_genres[i % len(demo_genres)],
                issue_year=2020 + (i % 5),
                artist_key=str(i % 100)
            )
            songs[i] = meta
            song_ids.append(i)
            search_text = _normalize_text(f"{meta.song_name} {meta.artist}")
            search_index.append((i, search_text))
        logger.info(f"더미 메타데이터 생성 완료: {len(songs):,}곡")
    
    # 데모 모드가 아닌데 메타가 없으면 예외
    if not songs and not demo_mode:
        raise RuntimeError(f"메타데이터가 비어있습니다: {path}")
    
    return MetaRegistry(songs=songs, song_ids=song_ids, search_index=search_index)


def load_audio_song_meta(path: str, demo_mode: bool) -> MetaRegistry:
    """
    오디오 메타데이터 JSON 로드
    
    Args:
        path: JSON 파일 경로
        demo_mode: 데모 모드 여부 (파일 없으면 더미 생성)
    
    Returns:
        MetaRegistry: 메타데이터 레지스트리
    """
    songs: Dict[int, SongMeta] = {}
    song_ids: List[int] = []
    search_index: List[Tuple[int, str]] = []
    
    file_path = Path(path) if path else None
    
    # 파일 로드 시도
    if file_path and file_path.exists():
        try:
            logger.info(f"메타데이터 로드 중: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 구조 파악: 리스트 또는 딕셔너리
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # 딕셔너리인 경우 values 사용
                if all(isinstance(v, dict) for v in data.values()):
                    items = list(data.values())
                else:
                    # 단일 객체인 경우
                    items = [data]
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                # song_id 추출
                sid_raw = _extract_field(item, ["song_id", "id", "sid"])
                if not sid_raw:
                    continue
                try:
                    sid = int(sid_raw)
                except ValueError:
                    continue
                
                # 필드 추출
                song_name = _extract_field(
                    item, 
                    ["song_name", "title", "name", "track_name"],
                    default="Unknown"
                )
                artist = _extract_field(
                    item,
                    ["artist", "artist_name", "artist_name_basket", "artists"],
                    default="Unknown"
                )
                
                # main_genre 추출 (첫 번째 장르 코드)
                genre_raw = item.get("song_gn_gnr_basket") or item.get("genre") or item.get("genres")
                if isinstance(genre_raw, list) and len(genre_raw) > 0:
                    genre = str(genre_raw[0])
                elif isinstance(genre_raw, str):
                    genre = genre_raw
                else:
                    genre = ""
                
                # artist_key 추출 (첫 번째 아티스트 ID)
                artist_id_basket = item.get("artist_id_basket")
                if isinstance(artist_id_basket, list) and len(artist_id_basket) > 0:
                    artist_key = str(artist_id_basket[0])
                else:
                    artist_key = "UNKNOWN"
                
                issue_year = _parse_year(
                    item.get("issue_year") or item.get("issue_date") or item.get("year")
                )
                
                # 중복 song_id 스킵
                if sid in songs:
                    logger.debug(f"중복 song_id 스킵: {sid}")
                    continue
                
                meta = SongMeta(
                    song_id=sid,
                    song_name=song_name,
                    artist=artist,
                    genre=genre,
                    issue_year=issue_year,
                    artist_key=artist_key
                )
                songs[sid] = meta
                song_ids.append(sid)
                
                # 검색 인덱스
                search_text = _normalize_text(f"{song_name} {artist}")
                search_index.append((sid, search_text))
            
            logger.info(f"메타데이터 로드 완료: {len(songs):,}곡")
            
        except Exception as e:
            logger.error(f"메타데이터 로드 실패: {e}")
            if not demo_mode:
                raise RuntimeError(f"메타데이터 로드 실패: {e}")
    
    # 데모 모드: 더미 데이터 생성
    if not songs and demo_mode:
        logger.warning("데모 모드: 더미 메타데이터 생성")
        demo_genres = ["GN0100", "GN0200", "GN0300", "GN0400", "GN0500"]
        for i in range(1, 5001):
            meta = SongMeta(
                song_id=i,
                song_name=f"Demo Song {i}",
                artist=f"Demo Artist {i % 100}",
                genre=demo_genres[i % len(demo_genres)],
                issue_year=2020 + (i % 5),
                artist_key=str(i % 100)  # 아티스트 ID 시뮬레이션
            )
            songs[i] = meta
            song_ids.append(i)
            search_text = _normalize_text(f"{meta.song_name} {meta.artist}")
            search_index.append((i, search_text))
        logger.info(f"더미 메타데이터 생성 완료: {len(songs):,}곡")
    
    # 데모 모드가 아닌데 메타가 없으면 예외
    if not songs and not demo_mode:
        raise RuntimeError(f"메타데이터가 비어있습니다: {path}")
    
    return MetaRegistry(songs=songs, song_ids=song_ids, search_index=search_index)


def load_item2vec_model(path: str) -> Optional[Any]:
    """
    Item2Vec (Word2Vec) 모델 로드
    
    Args:
        path: 모델 파일 경로
    
    Returns:
        Word2Vec 모델 또는 None
    """
    if not path:
        logger.info("Item2Vec 경로 미설정, 스킵")
        return None
    
    file_path = Path(path)
    if not file_path.exists():
        logger.warning(f"Item2Vec 파일 없음: {path}")
        return None
    
    try:
        from gensim.models import Word2Vec
        logger.info(f"Item2Vec 모델 로드 중: {path}")
        model = Word2Vec.load(path)
        vocab_size = len(model.wv)
        logger.info(f"Item2Vec 로드 완료: vocab={vocab_size:,}")
        return model
    except Exception as e:
        logger.error(f"Item2Vec 로드 실패: {e}")
        return None


def load_audio_embeddings(
    audio_model: str,
    myna_path: str,
    cnn_path: str
) -> Optional[AudioBundle]:
    """
    오디오 임베딩 로드
    
    Args:
        audio_model: "myna" 또는 "cnn"
        myna_path: Myna 임베딩 경로
        cnn_path: CNN 임베딩 경로
    
    Returns:
        AudioBundle 또는 None
    """
    path = myna_path if audio_model == "myna" else cnn_path
    
    if not path:
        logger.info(f"오디오 임베딩 경로 미설정 ({audio_model}), 스킵")
        return None
    
    file_path = Path(path)
    if not file_path.exists():
        logger.warning(f"오디오 임베딩 파일 없음: {path}")
        return None
    
    try:
        logger.info(f"오디오 임베딩 로드 중 ({audio_model}): {path}")
        data = np.load(path)
        
        # 키 탐색
        song_ids = None
        embeddings = None
        
        # song_ids 후보
        for key in ["song_ids", "ids", "song_id"]:
            if key in data.files:
                song_ids = data[key]
                break
        
        # embeddings 후보
        for key in ["embeddings", "emb", "audio_embeddings", "embedding"]:
            if key in data.files:
                embeddings = data[key]
                break
        
        # 키를 못 찾은 경우: 딕셔너리 형태 (song_id: embedding)
        if song_ids is None or embeddings is None:
            keys = list(data.keys())
            logger.info(f"NPZ 키 목록: {keys[:10]}...")
            
            # 숫자 키면 song_id로 간주
            try:
                song_ids_list = [int(k) for k in keys]
                embeddings_list = [data[k] for k in keys]
                song_ids = np.array(song_ids_list, dtype=np.int64)
                embeddings = np.array(embeddings_list, dtype=np.float32)
            except ValueError:
                logger.error("오디오 임베딩 키 파싱 실패")
                return None
        
        # 타입 변환
        song_ids = song_ids.astype(np.int64)
        embeddings = embeddings.astype(np.float32)
        
        # 검증: 길이 일치 확인
        if len(song_ids) != embeddings.shape[0]:
            logger.error(f"song_ids({len(song_ids)})와 embeddings({embeddings.shape[0]}) 길이 불일치")
            return None
        
        # 검증: 2차원 배열 확인
        if embeddings.ndim != 2:
            logger.error(f"embeddings가 2차원이 아님: ndim={embeddings.ndim}")
            return None
        
        # 인덱스 맵 생성
        # 각 song_id가 embeddings 배열에서 몇 번째 위치인지 알려주는 딕셔너리를 만듬
        song_id_to_idx = {int(sid): idx for idx, sid in enumerate(song_ids)}
        
        logger.info(f"오디오 임베딩 로드 완료: {len(song_ids):,}곡, dim={embeddings.shape[1]}")
        
        return AudioBundle(
            song_ids=song_ids,
            embeddings=embeddings,
            song_id_to_idx=song_id_to_idx,
            model_type=audio_model
        )
        
    except Exception as e:
        logger.error(f"오디오 임베딩 로드 실패: {e}")
        return None

