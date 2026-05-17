# 몰루? — API

FastAPI 백엔드. 멀티모달 AI(Gemini)로 사진 한 장에서 가전·DIY 진단을 한국어로 풀어주는 엔드포인트 제공.

- **현재 (v0.1)**: Gemini 단독 호출 + post-hoc 안전 가드
- **v0.2 예정**: Tavily Search + Corrective RAG로 매뉴얼 근거 보강

## API

### `POST /api/v1/diagnose`
multipart/form-data
- `image`: file (JPEG/PNG/WebP, ≤10MB)
- `hint` (옵션): 사용자가 추가로 알려주는 텍스트

응답: `DiagnosisResponse` (스키마는 `app/schemas/diagnose.py` 참조)

### `GET /health`
헬스체크. `{"status":"ok"}`

---

## 로컬 개발

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env       # GEMINI_API_KEY 채우기
uvicorn app.main:app --reload --port 8000

# 테스트
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/v1/diagnose \
  -F "image=@samples/washer.jpg" \
  -F "hint=세탁기 디스플레이에 E13이 떴어요"
```

---

## 서버 배포 (Ubuntu + Docker + Cloudflare Tunnel)

### 1) Gemini API 키 발급 (5분, 무료)

1. https://aistudio.google.com 접속 → Google 로그인
2. 좌측 상단 **Get API key** → **Create API key** → **Create API key in new project**
3. 생성된 키 복사 (한 번만 보임. 분실 시 재발급 필요)

### 2) 코드 가져오기

```bash
cd ~/apps
git clone https://github.com/Hbin77/molu-api.git
cd molu-api
```

### 3) .env 만들기 (API 키 주입)

```bash
cp .env.example .env
nano .env       # GEMINI_API_KEY=AIza... 채우기
# HOST_PORT=8000이 이미 쓰이면 다른 포트로 (예: 8200)
```

### 4) 빌드 + 실행

```bash
docker compose up -d --build
docker compose ps                    # healthy 확인
curl -sf http://127.0.0.1:8000/health  # {"status":"ok"}
```

### 5) Cloudflare Tunnel에 서브도메인 추가

대시보드 https://one.dash.cloudflare.com → Networks → Tunnels → **Ubuntu-server** → **호스트 이름 경로** 탭 → **+ 호스트 이름 추가**:

| 필드 | 값 |
|---|---|
| Subdomain | `api.molu` |
| Domain | `likelionscnu.site` |
| Type | `HTTP` |
| URL | `localhost:8000` (또는 HOST_PORT 바꿨으면 그 포트) |

저장하면 https://api.molu.likelionscnu.site/health 에 즉시 접근 가능.

### 6) 프론트가 사용하는 환경변수

`molu-mvp/.env` 에 다음 한 줄 추가 후 재빌드:

```
NEXT_PUBLIC_API_BASE=https://api.molu.likelionscnu.site
```

```bash
cd ~/apps/molu-mvp
git pull
nano .env       # NEXT_PUBLIC_API_BASE 줄 추가
docker compose up -d --build
```

이제 https://molu.likelionscnu.site 의 데모 섹션이 진짜로 동작합니다.

---

## 운영

```bash
docker compose logs -f api          # 라이브 로그
docker compose restart api          # 재기동
docker compose down                 # 정지
docker compose up -d --build        # 코드 갱신 후 재배포 (cd 후 git pull)
```

### 비용·쿼터 모니터

Google AI Studio 대시보드에서 일일 호출 수 확인. 무료 티어 한도 넘기 전에 자동 차단됨. 본격 운영 시 결제 등록.

---

## 디렉토리

```
app/
  main.py              FastAPI 진입 + CORS
  core/config.py       환경변수 (pydantic-settings)
  routers/
    health.py
    diagnose.py        POST /api/v1/diagnose
  services/
    gemini.py          Gemini 호출 + JSON parse + normalize
    safety.py          post-hoc 위험 단어 재검사
  schemas/diagnose.py  응답 Pydantic 모델
  prompts/
    diagnose_system.md Gemini 시스템 프롬프트 (한국어)
Dockerfile             python:3.12-slim, non-root, healthcheck
docker-compose.yml     127.0.0.1 바인딩 only
```
