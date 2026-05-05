# Deployment Checklist

Track off-code setup tasks here. Check items off as they're completed.

---

## GitHub Secrets

**Where:** github.com → swe-students-spring2026/5-final-dobsonfly_collective → Settings tab → Secrets and variables (left sidebar) → Actions → "New repository secret"

- [ ] `DOCKERHUB_USERNAME` — your Docker Hub username
- [ ] `DOCKERHUB_TOKEN` — hub.docker.com → your avatar (top right) → Account Settings → Security → Access Tokens → Generate new token
- [ ] `DO_HOST` — droplet IP address (e.g. `143.198.x.x`)
- [ ] `DO_USER` — `root` (default for new DO droplets)
- [ ] `DO_SSH_KEY` — paste the **private** key (the one paired with the public key added to the droplet); usually `~/.ssh/id_rsa` or `~/.ssh/id_ed25519`

---

## Digital Ocean Droplet

**Where:** cloud.digitalocean.com → Create → Droplets

- [ ] Droplet created — Ubuntu 22.04 LTS, Basic shared CPU, $6/mo (1 GB RAM is fine)
- [ ] SSH key added during creation (or after: droplet → Access → Add SSH key)
- [ ] SSH into droplet: `ssh root@<DO_IP>`
- [ ] Docker installed: `apt update && apt install -y docker.io && systemctl enable --now docker`
- [ ] Env file created: `mkdir -p /opt/vibe && nano /opt/vibe/.env`
  - [ ] `MONGODB_URI=<Atlas connection string from .env>`
  - [ ] `JWT_SECRET=<generate: python3 -c "import secrets; print(secrets.token_hex(32))">`
  - [ ] `JWT_EXPIRY_DAYS=7`
  - [ ] `FLASK_SECRET_KEY=<generate same way>`
  - [ ] `SPOTIFY_CLIENT_ID=<from Spotify dashboard>`
  - [ ] `SPOTIFY_CLIENT_SECRET=<from Spotify dashboard>`
  - [ ] `SPOTIFY_REDIRECT_URI=http://<DO_IP>:8000/api/spotify/callback`
  - [ ] `FRONTEND_URL=http://<DO_IP>:3000`
  - [ ] `CLOUDINARY_CLOUD_NAME=<from Cloudinary dashboard>`
  - [ ] `CLOUDINARY_API_KEY=<from Cloudinary dashboard>`
  - [ ] `CLOUDINARY_API_SECRET=<from Cloudinary dashboard>`

---

## MongoDB Atlas

**Where:** cloud.mongodb.com → your cluster

- [x] Atlas cluster created
- [x] Connection string added to local `.env`
- [ ] IP allowlist: cluster → Network Access → Add IP Address → `0.0.0.0/0` (allow all) or add the droplet IP specifically
- [ ] Same connection string copied into `/opt/vibe/.env` on the droplet

---

## Spotify Developer Dashboard

**Where:** developer.spotify.com → Dashboard → your app → Settings

- [ ] App created (or existing app used)
- [ ] Redirect URI added: `http://<DO_IP>:8000/api/spotify/callback` → Save
- [ ] Client ID and Client Secret copied into `/opt/vibe/.env` on the droplet

---

## Cloudinary

**Where:** cloudinary.com → Dashboard (shown on first login page)

- [ ] Account exists
- [ ] Cloud name, API key, API secret copied into `/opt/vibe/.env` on the droplet

---

## CI/CD

Push anything to `main` touching `backend/**` or `frontend/**` to trigger the pipeline.

- [ ] Backend CI green — github.com → Actions tab → "Backend CI/CD" → latest run all green
- [ ] Frontend CI green — github.com → Actions tab → "Frontend CI/CD" → latest run all green
- [ ] Docker images pushed — hub.docker.com → repositories → `vibe-backend:latest` and `vibe-frontend:latest` both updated
- [ ] Deploy SSH step green — in the Actions run, expand the "Deploy to Digital Ocean" step, no errors
- [ ] Verify on droplet: `ssh root@<DO_IP>` → `docker ps` → both `vibe-backend` and `vibe-frontend` containers are `Up`

---

## Post-deploy Smoke Test

Run from your local machine (replace `<DO_IP>`):

- [ ] Backend API docs load: `http://<DO_IP>:8000/docs`
- [ ] Frontend loads: `http://<DO_IP>:3000` → shows login page
- [ ] Register a new account end-to-end
- [ ] Log in with that account
- [ ] Connect Spotify (goes to Spotify → redirects back)
- [ ] Feed loads with profiles
- [ ] Like a user
- [ ] Check matches page

---

## Final Before Submit

- [x] Backend test coverage ≥ 80% — currently **99.69%** (186 tests)
- [x] Frontend test coverage ≥ 80% — currently **95.60%** (78 tests)
- [x] Coverage threshold set to 80% in `backend.yml`
- [ ] All team members' PRs merged to main
- [ ] `DEPLOY_CHECKLIST.md` fully checked off
