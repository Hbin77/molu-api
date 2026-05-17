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

## 서버 배포 (Ubuntu + Docker, 외부 노출 X)

**아키텍처**: 백엔드는 인터넷에 직접 노출되지 않습니다. molu-mvp(프론트)와 같은
docker 네트워크 `molu-net`에 들어가고, Next.js가 서버 사이드에서 `/api/v1/*` 요청을
컨테이너 이름(`http://molu-api:8000`)으로 프록시합니다. Cloudflare Tunnel은
**프론트(`molu.likelionscnu.site`)에만** 연결되어 있으면 됩니다.

### 1) Gemini API 키 발급 (5분, 무료)

1. https://aistudio.google.com 접속 → Google 로그인
2. 좌측 상단 **Get API key** → **Create API key** → **Create API key in new project**
3. 생성된 `AIza...` 키 복사 (한 번만 보임)

### 2) 공유 docker 네트워크 만들기 (처음 한 번만)

```bash
docker network create molu-net 2>/dev/null || echo "이미 있음"
```

### 3) 백엔드 가져오기 + 설정 + 기동

```bash
cd ~/apps
git clone https://github.com/Hbin77/molu-api.git
cd molu-api
cp .env.example .env
nano .env       # GEMINI_API_KEY=AIza... 채우기. HOST_PORT는 더 이상 안 씀

docker compose up -d --build
docker compose ps                       # healthy 확인
docker compose logs --tail=20 api       # 시작 로그
```

호스트 포트가 안 열린 게 정상입니다 (`docker compose ps` STATUS에 PORTS 컬럼 비어있음).
컨테이너끼리는 `http://molu-api:8000`으로만 닿습니다.

### 4) 프론트 재기동 (`molu-net`에 합류시키기)

프론트 docker-compose도 같은 외부 네트워크를 사용하도록 이미 설정돼 있습니다.
서버에서 프론트 컨테이너를 재기동만 하면 됩니다:

```bash
cd ~/apps/molu-mvp
git pull
docker compose up -d --build
```

### 5) 검증

```bash
# 같은 네트워크의 컨테이너 안에서는 닿음 (외부에선 X)
docker exec molu-mvp wget -qO- http://molu-api:8000/health
# {"status":"ok"}

# 그리고 브라우저에서 https://molu.likelionscnu.site 데모로 사진 업로드
# Next.js가 자동으로 /api/v1/diagnose → http://molu-api:8000/api/v1/diagnose 프록시
```

호스트에서 직접 `curl http://127.0.0.1:8000/health` 같은 건 더 이상 작동하지 않습니다
(의도된 결과 — 외부 노출 안 함). 디버깅이 필요하면 `docker compose logs api` 사용.

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
