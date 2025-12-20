# Song Curator 프론트엔드 파일 구조 및 기능 설명

---

## 📁 프로젝트 구조

```
FE/
├── package.json            # 의존성 및 스크립트 정의
├── vite.config.ts          # Vite 빌드 설정
├── tsconfig.json           # TypeScript 설정
├── tailwind.config.cjs     # Tailwind CSS 설정
├── postcss.config.cjs      # PostCSS 플러그인 설정
├── .env.local              # 환경변수 (API_BASE_URL)
├── index.html              # HTML 엔트리 포인트
│
└── src/
    ├── main.tsx            # React 앱 마운트
    ├── App.tsx             # 전체 레이아웃 래퍼
    │
    ├── styles/
    │   └── index.css       # Tailwind 지시어 + 다크 테마 기본 스타일
    │
    ├── lib/
    │   ├── types.ts        # API 응답 타입 (Song, RecommendResponse 등)
    │   ├── config.ts       # 설정 상수 (API_BASE_URL, DEFAULT_K)
    │   └── api.ts          # fetchRecommendations() - 백엔드 API 호출
    │
    ├── pages/
    │   └── SongCuratorPage.tsx   # 메인 페이지 (상태 관리 + 뷰 전환)
    │
    └── components/
        ├── common/
        │   ├── PrimaryButton.tsx   # 초록색 주요 버튼
        │   ├── SecondaryButton.tsx # 아웃라인 보조 버튼
        │   ├── Spinner.tsx         # 로딩 애니메이션
        │   └── ErrorMessage.tsx    # 에러 메시지 텍스트
        │
        ├── layout/
        │   └── Header.tsx          # 로고 + 부제
        │
        ├── input/
        │   └── SeedInputSection.tsx # 시드 ID 입력 폼
        │
        ├── loading/
        │   └── AnalyzingScreen.tsx  # 로딩 화면
        │
        └── playlist/
            ├── PlaylistView.tsx     # 결과 화면 전체
            ├── PlaylistHeader.tsx   # "당신을 위한 플레이리스트" 헤더
            └── TrackItem.tsx        # 개별 곡 카드
```

---

## 🔄 3단계 뷰 상태

| 상태 | 화면 | 구성 |
|------|------|------|
| `input` | 입력 화면 | 로고 + 곡 ID 입력창 + "추천받기" 버튼 |
| `loading` | 로딩 화면 | 스피너 + "당신의 Vibe를 분석 중입니다..." |
| `result` | 결과 화면 | 플레이리스트 카드 + 추천 곡 리스트 |

---

## 🛠 주요 기능

1. **시드 곡 ID 입력** → 숫자만 허용, 잘못된 입력 시 에러 메시지 표시
2. **백엔드 API 호출** → `GET /recommend?seed_id={id}&k=20`
3. **로딩 상태 표시** → 원형 스피너 애니메이션
4. **추천 결과 렌더링** → 곡 리스트를 스크롤 가능한 영역에 표시
5. **재시도** → "다른 노래로 다시 추천받기" 버튼으로 입력 화면 복귀
6. **에러 처리** → API 실패 시 입력 화면으로 돌아가며 에러 메시지 표시

---

## 🔗 백엔드 연동

- **Base URL**: `.env.local`의 `VITE_API_BASE_URL` (기본값 `http://localhost:8000`)
- **엔드포인트**: `GET /recommend`
- **필수 파라미터**: `seed_id` (곡 ID), `k` (추천 개수, 기본 20)
