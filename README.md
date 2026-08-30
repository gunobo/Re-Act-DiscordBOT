# 리액트봇 (RE-ACT Discord Bot)

동아리 RE-ACT 전용 디스코드 앱. 학교 이메일로 부원 인증하고, 대회를 등록하면 디스코드에
카테고리별 채널과 "참가하기" 버튼이 자동으로 생성된다. 부원 화이트리스트, 공지, 대회, 각종
설정은 관리용 웹(`react.bssm.dev`)에서 운영진이 관리한다.

- `discord-bot/` — Node.js(discord.js) 슬래시 커맨드(`/인증`, `/인증확인`, `/포인트`, `/랭킹`) + 참가 버튼 처리
- `backend/` — Python(FastAPI + SQLModel). 기능별 디렉토리(`app/<feature>/{models.py,router.py,service.py}`)
- 두 서비스는 내부 HTTP API(`X-Internal-Key` 헤더)로 통신한다.

Discord REST 호출(채널 생성, 임베드 전송/수정, 역할 부여, 닉네임 변경, DM)은 전부 backend가
봇 토큰으로 직접 수행한다. `discord-bot`은 게이트웨이 인터랙션(슬래시 커맨드, 버튼 클릭)만
받아 backend에 위임하고 결과를 보여준다.

## 배포 방식

- **backend**: 라즈베리파이에서 Docker Compose로 실행 (`docker-compose.yml`).
- **discord-bot**: 컨테이너화하지 않고 **PM2**로 직접 실행 (`pm2 start ecosystem.config.js`).
- 공인 도메인은 `https://react.bssm.dev`. 라즈베리파이가 포트포워딩 없이 학교/집 네트워크
  안에 있는 경우가 보통이므로, `docker-compose.yml`에 포함된 **Cloudflare Tunnel**
  (`cloudflared` 서비스)로 backend(8000)를 그 도메인에 연결한다. Discord OAuth 콜백이
  동작하려면 `WEB_BASE_URL`이 실제로 외부에서 접속 가능한 HTTPS 주소여야 하므로 필수 단계다.

### Cloudflare Tunnel 연결

1. [Cloudflare Zero Trust 대시보드](https://one.dash.cloudflare.com/) → **Networks → Tunnels →
   Create a tunnel** → Connector 종류로 **Docker** 선택 → 터널 이름 입력(예: `react-bssm`)
2. 생성 화면에 나오는 `cloudflared tunnel run --token <...>`의 `--token` 뒤 문자열을 복사해
   루트 `.env`의 `CLOUDFLARE_TUNNEL_TOKEN`에 채운다 (`cp .env.example .env` 후 편집)
3. 같은 화면(또는 터널 상세 → **Public Hostname**)에서 Public Hostname 추가:
   - Subdomain/Domain: `react.bssm.dev` (bssm.dev가 이미 Cloudflare에 연결되어 있어야 함)
   - Service: `HTTP` / URL: `backend:8000` (compose 서비스명 — cloudflared 컨테이너가 같은
     도커 네트워크에 있어서 서비스명으로 접근 가능)
4. `backend/.env`의 `WEB_BASE_URL=https://react.bssm.dev` 확인
5. `docker compose up -d --build` (cloudflared도 기본으로 함께 뜬다)
6. Discord 개발자 포털의 OAuth2 Redirect에 `https://react.bssm.dev/auth/discord/callback`을
   등록 (`WEB_BASE_URL` + `/auth/discord/callback`과 정확히 일치해야 함)

## 처음 설정하기

### 1. Discord 개발자 포털

1. https://discord.com/developers/applications 에서 애플리케이션 생성
2. **Bot** 탭에서 토큰 발급 (`DISCORD_TOKEN`), `Manage Roles`/`Manage Channels`/`Manage Nicknames` 권한으로 서버에 초대
3. **OAuth2** 탭에서 `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` 확인, Redirect에
   `https://react.bssm.dev/auth/discord/callback` 등록
4. 봇 역할이 서버 역할 목록에서 `/설정`으로 부여할 역할들보다 **위에** 있어야 역할 부여/닉네임
   변경이 성공한다 (아래에 있으면 403 에러).

### 2. backend

`.env`부터 채운다 (로컬 개발/Docker 배포 공통):

```bash
cd backend
cp .env.example .env
# .env 채우기: DISCORD_TOKEN, DISCORD_GUILD_ID, DISCORD_CLIENT_ID/SECRET,
#              WEB_BASE_URL=https://react.bssm.dev, COOKIE_SECRET, INTERNAL_API_KEY,
#              SUPER_ADMIN_DISCORD_IDS(최초 관리자 본인 디스코드ID), SMTP_* (학교 이메일 발송용)
```

**로컬에서 Docker 없이 바로 테스트해볼 때만** 아래처럼 직접 실행한다 (라즈베리파이 배포에는 필요
없음 — 4번 항목의 `docker compose up`이 이 과정을 대신한다):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

DISCORD_TOKEN이나 SMTP_*가 비어 있으면 실제 호출 대신 콘솔 로그만 남기는 mock 모드로 동작해서,
디스코드/메일 서버 없이도 로컬에서 흐름을 확인할 수 있다.

### 3. discord-bot

```bash
cd discord-bot
npm install
cp .env.example .env
# .env 채우기: DISCORD_TOKEN, DISCORD_CLIENT_ID, DISCORD_GUILD_ID,
#              BACKEND_URL, INTERNAL_API_KEY (backend와 동일한 값)

npm run deploy-commands   # 슬래시 커맨드 등록 (최초 1회, 커맨드 추가/수정 시 재실행)
npm run dev               # 로컬 개발
```

라즈베리파이 운영 시:

```bash
npm install -g pm2
cd discord-bot
pm2 start ecosystem.config.js
pm2 save
```

### 4. 라즈베리파이 배포 (backend, Docker)

```bash
git clone <이 저장소 주소>
cd 리액트봇
cp backend/.env.example backend/.env   # 채우기
docker compose up -d --build
```

`sqlite` DB는 `backend_data` 볼륨에 저장되어 컨테이너를 재생성해도 유지된다.

## 사용 흐름

1. **운영진**: `https://react.bssm.dev/auth/login` 로 Discord 로그인 → `SUPER_ADMIN_DISCORD_IDS`에
   포함되어 있거나 `/admin/settings`에서 지정한 운영진 역할을 가지고 있으면 관리 페이지 진입.
2. **운영진**: `/admin/members`에서 학교 이메일 + 학번 + 이름을 화이트리스트에 등록.
3. **운영진**: `/admin/settings`에서 인증 시 부여할 역할(복수 선택), 닉네임 형식
   (기본 `{student_id} {name}`), 공지 채널을 지정.
4. **부원**: 디스코드에서 `/인증 이메일:학교이메일` → 코드 수신 → `/인증확인 코드:######` →
   설정된 역할 부여 + 닉네임이 학번/이름으로 자동 변경.
5. **운영진**: `/admin/categories`에서 카테고리(예: 웹개발/앱개발/게임개발)와 안내 템플릿 등록.
6. **운영진**: `/admin/competitions/new`에서 대회 등록 시 카테고리 선택 + 카테고리별 선착순 정원
   입력 → **대회명으로 된 디스코드 카테고리가 자동 생성**되고, 그 안에 카테고리별 채널과
   "참가하기" 버튼이 달린 안내가 게시됨. 대회 상세 페이지에서 언제든 삭제 가능 (디스코드
   카테고리/채널/역할도 함께 정리됨).
7. **부원**: 버튼 클릭 → 인증 여부/정원 확인 → 성공 시 대회명과 같은 이름의 역할이 자동 부여되고
   개인 DM으로 참가 완료 + 적립 포인트 안내, 임베드의 참가 인원 수 갱신 (정원 도달 시 버튼 비활성화).
8. **운영진**: `/admin/notices`에서 공지 작성 후 "게시"하면 설정된 채널에 자동 전송, `/notices`
   공개 페이지에서도 확인 가능.
9. **부원**: `/포인트`(본인 포인트 확인), `/랭킹`(상위 10명)으로 활동 포인트 확인. 참가 시
   자동 지급되는 포인트 양은 `/admin/settings`에서 조절, 출석 등 수동 지급/차감 및 잘못된
   내역 삭제는 `/admin/points`.
10. **운영진**: `/admin/attributes`에서 부원별 추가 정보 항목(연락처, 전공 등)을 자유롭게
    정의하고 `/admin/members`의 각 부원 "속성" 링크에서 값을 입력. 디스코드에는 반영되지 않으며,
    대회 참가자 CSV를 내보낼 때 어떤 속성을 포함할지 체크박스로 선택할 수 있다.
11. **운영진**: 대회 상세 페이지(`/admin/competitions/{id}`)에서 참가자 명단을 CSV로 다운로드.
12. **GitHub 연동**: 저장소 Settings → Webhooks에서 Payload URL을
    `https://react.bssm.dev/webhooks/github`, Secret을 `GITHUB_WEBHOOK_SECRET`과 동일하게,
    이벤트로 Pull requests/Issues를 등록하면 `/admin/settings`에서 지정한 채널에 PR/이슈 알림이 온다.
