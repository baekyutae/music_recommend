# 📏 VibeCurator Offline Evaluation Spec  
Stage 1 / 1.5 / 2 공통 오프라인 평가 기준

---

## 1. 목적

VibeCurator 프로젝트에서 다음 세 가지 모델을 **동일한 기준으로 비교**하기 위한 오프라인 평가 스펙을 정의한다.

- **Stage 1**: item2vec 기반 CF 베이스라인
- **Stage 1.5**: Stage 1 결과에 메타데이터(artist/genre) 기반 re-ranking 적용
- **Stage 2**: CF + Audio(멜스펙 CNN 임베딩) + Meta를 결합한 하이브리드 모델

목표:

- 동일한 평가 셋, 동일한 지표로 Stage 1 → 1.5 → 2 성능 변화를 정량적으로 측정
- 아티스트/장르 다양성, 카탈로그 커버리지까지 포함해 "실제 서비스 품질"을 수치로 설명
- 나중에 웹 베타(추천 API)와도 이어질 수 있도록 인터페이스를 정리

---

## 2. 평가 시점 및 전제

이 스펙은 **Stage 2까지 구현이 끝난 시점**에 실제 실행하는 것을 전제로 한다.

전제:

- Melon Playlist Dataset 기반
  - `train.json`: 플레이리스트
  - `song_meta.json`: 곡 메타데이터 (song_id, song_name, artist, 장르 등)
- Stage 1 / 1.5 / 2 모델이 모두 학습 완료된 상태
  - Stage 1: `v2_item2vec.model` (min_count=2)
  - Stage 1.5: Stage 1 결과에 대해 artist/genre rerank 함수가 준비됨
  - Stage 2: audio encoder + hybrid scoring 함수가 준비됨
- 오프라인 평가는 **플레이리스트 기반 implicit feedback** 상황을 가정한다.

---

## 3. 평가 데이터 정의

### 3.1 In-Catalog 곡 집합

오프라인 평가는 **모델이 실제로 다룰 수 있는 곡만 포함**하는 것이 원칙이다.  
Word2Vec(item2vec) 학습 시 `min_count=2`로 인해 2회 미만 등장 곡은 vocab에서 제외되어 임베딩이 없다.

- `IN_CATALOG_SONGS` 정의:

  - Stage 1 모델의 vocab에서 song_id를 추출:
    - `IN_CATALOG_SONGS = { int(k) for k in model.wv.key_to_index.keys() }`
  - 이 집합에 포함된 곡만 "추천 가능 곡"으로 간주한다.

이렇게 해야 **모델이 이론적으로 맞힐 수 없는 곡**이 정답 집합에 들어와서 Recall을 인위적으로 깎지 않게 된다.

### 3.2 플레이리스트 전처리

`train.json`의 각 플레이리스트에 대해:

1. 원래 곡 리스트에서 `IN_CATALOG_SONGS`에 포함된 곡만 남긴다.
2. 필터링 후 곡 수가 너무 적은 플레이리스트는 평가에서 제외
   - 최소 길이 예: `MIN_LEN = 5`
3. 남은 플레이리스트에 대해 다음 정보를 정리:
   - `playlist_id`
   - `song_ids_in_vocab` (리스트[int])

이렇게 만든 "in-catalog 플레이리스트 집합"을 이후 split 및 평가에 사용한다.

### 3.3 Train / Val / Test Split (플레이리스트 단위)

플레이리스트 단위로 **랜덤 split**을 수행한다.

- 비율 (초기 권장값)
  - Train: 80%
  - Validation: 10%
  - Test: 10%
- 무작위성:
  - 재현성을 위해 `random_seed = 42` 고정
- split 방법:
  - playlist 리스트를 섞은 뒤 인덱스로 80/10/10 분할
- 주의:
  - 이상적으로는 "시간 기반 split"이 더 안전하지만,
    - Melon Playlist Dataset에서 시간 정보 활용이 까다롭다면
    - 우선 랜덤 split을 사용하고, 추후 시간 기반 split으로 확장 가능하도록 여지를 남긴다.

### 3.4 Test 플레이리스트에서 Evaluation Case 생성

각 test 플레이리스트 `P = [s1, s2, …, sn]` (이미 `IN_CATALOG_SONGS`로 필터된 상태) 에 대해:

1. **Seed 선택**
   - 기본 전략: 플레이리스트 첫 곡을 seed로 사용
     - `seed_song_id = s1`
   - 확장 가능:
     - 추후 여러 seed (예: 앞 2~3곡)를 사용한 multi-seed 평가로 확장 가능

2. **Target 곡 집합**
   - `target_song_ids = [s2, s3, …, sn]`
   - 이 집합이 "정답(같이 들은 곡)"이 된다.

3. Evaluation case 구조 예시:

   ```python
   {
       "playlist_id": <int>,
       "seed_song_id": <int>,
       "target_song_ids": [<int>, <int>, ...]
   }
   ```

4. Test 전체에 대해 이런 case를 모아 `eval_cases` DataFrame 또는 리스트로 저장한다.

---

## 4. 공통 추천 함수 인터페이스

세 Stage를 동일한 평가 파이프라인에 꽂으려면, **공통 시그니처**를 맞춰두는 것이 중요하다.

평가용 추천 함수 인터페이스(파이썬):

```python
def recommend_stage1(seed_song_id: int, topk: int) -> list[int]:
    """
    Stage 1: item2vec 순수 CF.
    - 입력: seed_song_id
    - 출력: 추천 song_id 리스트 (길이 topk)
    - 필수 특징:
      - seed 자기 자신은 결과에서 제외
      - 모든 결과는 IN_CATALOG_SONGS에 포함된 곡이어야 함
    """
    ...

def recommend_stage1_5(seed_song_id: int, topk: int) -> list[int]:
    """
    Stage 1.5: item2vec + artist/genre re-ranking.
    - 내부적으로:
      - CF 후보 풀 (예: topn_cf=200)을 뽑은 뒤
      - artist/genre 페널티를 적용해 재정렬
      - 최종 상위 topk song_id를 반환
    """
    ...

def recommend_stage2(seed_song_id: int, topk: int) -> list[int]:
    """
    Stage 2: CF + Audio + Meta 하이브리드 추천.
    - 내부적으로:
      - CF score, audio 유사도, genre/연도 등 메타 score를 결합
      - score_final 기준으로 상위 topk song_id 반환
    """
    ...
```

평가 노트북에서는 이 세 함수를 **"검은 상자"처럼 호출만** 하고,
내부 구현은 각 Stage 노트북/모듈에서 관리한다.

---

## 5. 지표 체계: 3축 평가

오프라인 평가는 아래 세 축으로 본다.

### 5.1 축 1 – 정확도 / 랭킹 품질 (Relevance)

**목적:** "같은 플레이리스트 안에 있던 곡들을 얼마나 잘 다시 찾아오는가?"

사용 지표:

1. **Recall@K**

   * 정의:

     * `target_song_ids` 중 TopK 추천 안에 들어온 곡 비율
     * `Recall@K = |Recommended_K ∩ target_song_ids| / |target_song_ids|`
   * K는 기본 20 (Recall@20), 필요 시 50 등 추가로 볼 수 있다.

2. **nDCG@K (Normalized Discounted Cumulative Gain)**

   * 정의(이 프로젝트에선 binary relevance):

     * 정답 곡이면 rel=1, 아니면 0
     * 위에 있을수록 더 높은 가중치를 주는 랭킹 지표
   * DCG@K:

     * `DCG@K = Σ (rel_i / log2(i+1))`  (i는 1부터 K까지 순위)
   * IDCG@K:

     * 정답을 이상적인 순서(위에서부터 전부 rel=1)로 배치한다고 가정했을 때의 DCG
   * nDCG@K:

     * `nDCG@K = DCG@K / IDCG@K`
   * Stage 2에서 "위쪽 순위에 진짜 더 적절한 곡을 올려주는지" 확인하는 데 중요하다.

---

### 5.2 축 2 – 다양성 / 커버리지 (Diversity & Coverage)

**목적:** "곡은 맞는데, 한두 아티스트만 도배되는 게 아니라 적당히 다양한가?"
또는 "전체 카탈로그 중 얼마나 많은 곡이 실제 추천에서 쓰이는가?"를 본다.

사용 지표:

1. **리스트 내부 다양성 (간단 버전)**

   각 evaluation case의 TopK 추천 리스트에 대해:

   * `Unique Artists@K`:

     * TopK 내 서로 다른 아티스트 수
   * `Unique Genres@K`:

     * TopK 내 서로 다른 메인 장르 수

   전체 test case에 대해 평균을 내서:

   * `mean_unique_artists@K`
   * `mean_unique_genres@K`

   을 Stage 1 / 1.5 / 2 간 비교한다.

2. **Catalog Coverage**

   * 정의:

     * 전체 in-catalog 곡 중, 평가 시 한 번이라도 추천 결과에 등장한 곡 비율
   * 계산 방법:

     1. 모든 evaluation case에 대해 TopK 추천을 모아 `recommended_song_ids` 집합 생성
     2. `coverage@K = len(recommended_song_ids) / len(IN_CATALOG_SONGS)`
   * Stage 2에서 audio를 사용하면 CF만 쓰던 때보다 **조금 더 다양한 곡이 추천되는지** 볼 수 있다.

---

### 5.3 축 3 – UX / 편중·안전성 지표

**목적:** 단순 정확도 외에,
"사람이 봤을 때 이상해 보이는 리스트(한 가수 도배, 장르 튐 등)를 막고 있는지"를 본다.

사용 지표:

1. **최대 아티스트 점유율 (Max Artist Share)**

   각 리스트(TopK)에 대해:

   * 가장 많이 나온 아티스트의 곡 개수를 찾고,
   * `max_artist_share = (해당 아티스트 곡 수) / K` 로 정의

   예:

   * Top10에서 아이유 7곡이면 max_artist_share = 0.7

   Stage 1에서는 인기 아티스트가 0.7~0.9까지 갈 수 있고,
   Stage 1.5 / 2에서는 하드컷/다양성 덕분에 이 값이 눈에 띄게 낮아지는지 본다.

2. **Seed-Genre 일관성 비율**

   * `seed_main_genre`와 동일한 장르의 곡 비율:

     * `genre_consistency = (TopK에서 seed_main_genre와 같은 장르 곡 수) / K`

   장르별로 평균:

   * 영화음악 seed에서:

     * Stage 1: 60%
     * Stage 1.5: 100%
     * Stage 2: 90~100%
       이런 식으로 비교.

3. (선택) **인기도 편향 지표**

   * playlist 등장 빈도로 곡 인기(popularity)를 정의하고,
   * 추천 리스트의 평균 popularity를 Stage 1 / 1.5 / 2에서 비교할 수도 있다.
   * 이 스펙에서는 필수는 아니지만, Stage 2 튜닝 시 필요하면 추가한다.

---

## 6. 정성 평가용 고정 시드 리스트

수치 지표와 별개로, 실제 곡 이름 기준으로 Stage 1 / 1.5 / 2 추천 결과를 비교하기 위한 "고정 시드 리스트"를 둔다.

### 6.1 아티스트 선택

* **박효신** – 국내 발라드 대표
* **아이유** – 팝/발라드/싱어송라이터 대표
* **잔나비** – 밴드/록/인디 대표

세 아티스트 모두 충분히 메이저이며, 서로 다른 장르를 대표하도록 선정하였다.

### 6.2 시드 곡 선택 (TODO)

각 아티스트별로 1곡씩 시드 곡을 고정한다. 예시:

* 박효신: `야생화`
* 아이유: `밤편지`
* 잔나비: `주저하는 연인들을 위해`

실제 구현 시에는 Melon Playlist Dataset에서의 `song_id`를 찾아
`seed_artist_fixed.md` 등으로 별도 정리해두고,
Stage 1 / 1.5 / 2 모두 동일한 시드로 Top10 추천을 뽑아 비교한다.

---

## 7. 실행 순서 요약

Stage 2까지 구현이 완료되었을 때, 오프라인 평가는 다음 순서로 수행한다.

1. **eval_offline.ipynb 준비**

   * 별도의 노트북에서:

     * `train.json`, `song_meta.json`, `v2_item2vec.model` 등을 로드
     * IN_CATALOG_SONGS 계산
     * in-catalog 플레이리스트 필터링 및 train/val/test split
     * test에서 evaluation cases(`seed_song_id`, `target_song_ids`) 생성

2. **추천 함수 래퍼 준비**

   * Stage 1 / 1.5 / 2에 대해:

     * `recommend_stage1`
     * `recommend_stage1_5`
     * `recommend_stage2`
       를 공통 시그니처로 구현/임포트

3. **지표 계산**

   * 각 Stage에 대해:

     * Recall@20, nDCG@20
     * mean_unique_artists@20, mean_unique_genres@20
     * catalog_coverage@20
     * mean_max_artist_share@20
     * mean_seed_genre_ratio@20
   * 결과를 dict/JSON/CSV로 저장

4. **정성 평가**

   * 박효신/아이유/잔나비 고정 시드에 대해:

     * 각 Stage에서 Top10 추천을 곡 이름/아티스트/장르 형태로 출력
   * Stage 1 → 1.5 → 2로 갈수록:

     * 아티스트 편중이 완화되는지,
     * 장르 일관성과 "vibe"가 더 좋아지는지 직접 눈/귀로 확인

5. **리포트 작성**

   * Stage 1 / 1.5 / 2 결과를 표/그래프로 요약하고,
   * 포트폴리오/면접용으로 설명 가능한 스토리 템플릿을 따로 정리한다.

---

이 파일(eval_offline_spec.md)은
VibeCurator 프로젝트에서 Stage 1 / 1.5 / 2를 비교하는 **공식 오프라인 평가 스펙**으로 사용한다.

---

## v1 베이스라인 오프라인 평가 요약

이 문서는 **VibeCurator v1** 기준으로, Stage1(item2vec), Stage1.5(CF+메타데이터 re-ranking), Stage3(CF+메타+오디오 하이브리드)의 **오프라인 평가 설정과 결과를 정리한 베이스라인 문서**입니다. 이후 v2/v3와 비교할 때 기준점으로 사용할 계획입니다.

### 1. 평가 데이터·세트 구성

* **Seed 곡 개수**: 1,000개
* **Seed 추출 방식**: 
  * Test 플레이리스트에서 첫 곡을 seed로 사용
  * `IN_CATALOG_SONGS`에 포함된 곡만 사용 (item2vec vocab 기준, min_count=2 이상 등장 곡)
  * 플레이리스트 길이가 2곡 이상인 경우만 평가 케이스로 포함
* **Ground truth 정의**: 
  * 각 플레이리스트에서 seed 곡을 제외한 나머지 곡들을 `target_song_ids`로 정의
  * "같은 플레이리스트에 포함된 다른 곡들"을 정답으로 간주
* **평가 세트 구성**: 
  * 플레이리스트 단위 랜덤 split (80/10/10)
  * Test 세트에서 생성된 evaluation cases 사용
  * 실제 평가는 속도 테스트를 위해 1,000개 샘플로 수행 (`MAX_CASES = 1000`)

### 2. 지표 정의

#### 2.1 정확도 / 랭킹 품질 지표

* **Recall@K**
  * 정의: 각 seed 곡에 대해 추천 Top-K 안에 원래 같은 플레이리스트에 있던 곡(target_song_ids)이 몇 개나 들어왔는지 비율을 계산하고, 전체 seed에 대해 평균낸 값
  * 수식: `Recall@K = |Recommended_K ∩ target_song_ids| / |target_song_ids|` (seed별 계산 후 평균)
  * K=20 사용

* **nDCG@K (Normalized Discounted Cumulative Gain)**
  * 정의: 정답 곡이 위쪽 순위에 있을수록 높은 점수를 주는 랭킹 품질 지표
  * Binary relevance: 정답 곡이면 rel=1, 아니면 0
  * DCG@K = Σ (rel_i / log2(i+1)) (i는 1부터 K까지 순위)
  * IDCG@K: 이상적인 순서(모든 정답이 위에)일 때의 DCG
  * nDCG@K = DCG@K / IDCG@K
  * K=20 사용

#### 2.2 다양성 지표

* **아티스트 다양성 (mean_unique_artists@K)**
  * 정의: 추천 Top-K 안에서 서로 다른 아티스트 수를 각 seed별로 계산하고, 전체 seed에 대해 평균낸 값
  * 높을수록 다양한 아티스트가 추천됨을 의미

* **장르 다양성 (mean_unique_genres@K)**
  * 정의: 추천 Top-K 안에서 서로 다른 메인 장르 수를 각 seed별로 계산하고, 전체 seed에 대해 평균낸 값
  * 높을수록 다양한 장르가 추천됨을 의미

#### 2.3 UX / 편중·안전성 지표

* **최대 아티스트 점유율 (mean_max_artist_share@K)**
  * 정의: 각 seed별로 Top-K 추천 리스트에서 가장 많이 나온 아티스트의 곡 개수를 K로 나눈 비율을 계산하고, 전체 seed에 대해 평균낸 값
  * 낮을수록 아티스트 편중이 완화됨을 의미 (예: Top10에서 아이유 7곡이면 0.7)

* **Seed-Genre 일관성 비율 (mean_seed_genre_ratio@K)**
  * 정의: 각 seed별로 Top-K 추천 리스트에서 seed 곡과 같은 메인 장르를 가진 곡의 비율을 계산하고, 전체 seed에 대해 평균낸 값
  * 높을수록 seed 장르와 일관된 추천을 의미

### 3. v1 수치 요약 (Stage별 비교)

| 모델 스테이지 | Recall@20 | nDCG@20 | 아티스트 다양성@20 | 장르 다양성@20 | 최대 아티스트 점유율@20 | Seed-Genre 일관성@20 | 비고 |
|--------------|----------|---------|-------------------|---------------|----------------------|---------------------|------|
| Stage1       | 0.0313   | 0.0572  | 15.011            | 3.814         | 0.2018               | 0.5695              | item2vec CF만 사용 |
| Stage1.5     | 0.0253   | 0.0501  | 16.844            | 3.280         | 0.0972               | 0.6781              | CF + 메타(아티스트/장르 레일가드) |
| Stage3       | 0.0251   | 0.0485  | 17.020            | 3.316         | 0.0968               | 0.6725              | CF + 메타 + 오디오 하이브리드 |

**주요 변화 요약:**

* **Recall@20**: Stage1 → Stage1.5에서 소폭 하락 (0.0313 → 0.0253), Stage3에서 거의 유지 (0.0251)
* **nDCG@20**: Stage1 → Stage1.5에서 소폭 하락 (0.0572 → 0.0501), Stage3에서 약간 하락 (0.0485)
* **아티스트 다양성**: Stage1 → Stage1.5에서 개선 (15.011 → 16.844), Stage3에서 추가 개선 (17.020)
* **장르 다양성**: Stage1 → Stage1.5에서 약간 하락 (3.814 → 3.280), Stage3에서 소폭 회복 (3.316)
* **최대 아티스트 점유율**: Stage1 → Stage1.5에서 크게 개선 (0.2018 → 0.0972), Stage3에서 거의 유지 (0.0968)
* **Seed-Genre 일관성**: Stage1 → Stage1.5에서 개선 (0.5695 → 0.6781), Stage3에서 약간 하락 (0.6725)

**인사이트**: Stage1.5에서 메타데이터 re-ranking을 통해 아티스트 편중이 크게 완화되고 장르 일관성이 개선되었으나, Recall은 소폭 하락. Stage3에서는 오디오 임베딩을 추가했지만 Recall/nDCG는 추가 하락, 다양성은 소폭 개선.

### 4. 대표 seed 기반 정성 비교 요약

`v1_추천 결과물 비교.md`에서 확인한 4개 seed 곡(로켓트-잔나비, 와리가리-혁오, 삐삐-아이유, Illumination-SEKAI NO OWARI)에 대한 패턴 요약:

* **발라드/록 계열 seed (로켓트, 와리가리)**:
  * Stage1에서는 같은 아티스트 위주 추천이 많았으나 (예: 혁오 seed에서 혁오 곡 4곡 상위권)
  * Stage1.5에서 아티스트가 다양해지고 장르 일관성은 유지됨
  * Stage3에서는 오디오 유사도가 반영되어 순위가 재조정되지만, 전체적인 다양성은 유지

* **팝/K-pop seed (삐삐-아이유)**:
  * Stage1에서 다양한 아티스트가 추천되었으나 장르가 혼재 (GN2500, GN0400, GN0100 등)
  * Stage1.5에서 장르 일관성은 유지되나 순위 변화는 적음
  * Stage3에서 오디오 기반 재랭킹이 일부 반영되어 순위가 재조정됨

* **일본 음악 seed (Illumination-SEKAI NO OWARI)**:
  * Stage1.5에서 장르 레일가드가 작동하여 일본 음악(GN1900) 위주로 재정렬됨
  * Stage3에서도 오디오 유사도가 반영되어 일본 음악 위주 추천 유지

**전체 패턴**: Stage1.5의 메타데이터 re-ranking이 아티스트 편중 완화와 장르 일관성 개선에 효과적. Stage3의 오디오 하이브리드는 순위 재조정에 기여하나 정량 지표 개선은 제한적.

### 5. v1에서 사용한 핵심 하이퍼파라미터 요약

#### 5.1 Stage1 (item2vec)

* `min_count = 2`: 최소 출현 횟수 (2회 미만 곡은 vocab에서 제외)
* `window = 10`: 컨텍스트 윈도우 크기
* `vector_size = 128`: 임베딩 차원
* `epochs = 5`: 학습 에폭 수
* `negative = 10`: Negative sampling 개수
* `sg = 1`: Skip-gram 모드 사용
* `hs = 0`: Hierarchical softmax 미사용

#### 5.2 Stage1.5 재랭킹

* **CF 후보 추출**: `topn_cf = 200` (item2vec에서 상위 200곡 후보 추출)
* **동일 아티스트 soft penalty**:
  * `max_per_artist_soft = 3`: 아티스트당 최대 3곡까지 페널티 없음
  * `penalty_per_extra = 0.05`: 3곡 초과 시 곡당 0.05씩 점수 차감
* **장르 레일가드**:
  * `offrail_penalty_general = 0.008`: 일반 장르 불일치 시 페널티
  * `offrail_penalty_special = 0.03`: 특수 장르(트로트, CCM 등) 불일치 시 페널티
* **최종 아티스트 hardcut**:
  * `max_per_artist_final = 2`: 최종 Top-K에서 아티스트당 최대 2곡만 허용
  * `topk_final = 30`: 최종 반환 곡 수 (평가 시에는 topk=20으로 재슬라이싱)

#### 5.3 Stage3 하이브리드

* **CF+메타 점수 vs 오디오 점수 가중치**:
  * `alpha = 0.7`: CF+메타 정규화 점수 가중치
  * `beta = 0.3`: 오디오 유사도 정규화 점수 가중치
* **CF 후보 개수**: `topn_cf = 200` (Stage1.5와 동일)
* **하이브리드 점수 계산**:
  * CF+메타 점수와 오디오 유사도를 각각 min-max 정규화 (0~1 범위)
  * `score_hybrid = alpha * score_cf_norm + beta * score_audio_norm`
  * 오디오 임베딩이 없는 곡은 `score_audio_norm = 0.0`으로 처리

### 6. 향후 버전 비교 시 활용 계획

이 문서는 **v1 기준선**이며, 이후 Stage2/3 구조·가중치·데이터를 바꾼 v2/v3를 만들었을 때, 같은 평가 세트/지표로 다시 측정해 이 표/정의와 직접 비교할 계획입니다.

정량 지표(Recall@K, nDCG@K, 다양성 지표 등)뿐 아니라, `v1_추천 결과물 비교.md`와 같은 정성 비교도 v2/v3 버전으로 추가해서 **"숫자 + 실제 추천 리스트" 모두로 개선 여부를 판단**할 예정입니다.

주요 비교 포인트:
* 하이퍼파라미터 변경(예: alpha/beta 비율, penalty 값)이 지표에 미치는 영향
* 오디오 인코더 모델 변경(예: 아키텍처, 학습 방식)이 추천 품질에 미치는 영향
* 새로운 re-ranking 규칙 추가 시 정량/정성 지표 변화