# VPS deployment

The backend runs on a Linux VPS as a systemd-managed `uvicorn` worker bound
to localhost, fronted by `nginx` for TLS. No Docker. The frontend is a
static Next.js export served by Cloudflare Pages.

## Prerequisites on the VPS

Ubuntu 22.04 or 24.04. Tested with:

- Python 3.12
- PostgreSQL 17 (apt: `postgresql-17`)
- nginx + certbot (`apt install nginx python3-certbot-nginx`)

## One-time setup

1. Create a dedicated unix user and clone the repo.

   ```bash
   sudo adduser --system --group --home /home/arxrec --shell /bin/bash arxrec
   sudo -iu arxrec git clone https://github.com/scottcampbelldata/arxiv-recommender.git
   ```

2. Create the database, role, schemas, and grants.

   ```bash
   sudo -u postgres bash /home/arxrec/arxiv-recommender/platform/deploy/setup-database.sh
   ```

   Copy the generated app password into
   `/home/arxrec/arxiv-recommender/platform/.env` (use `.env.example` as a
   template).

3. Install Python dependencies inside a virtualenv owned by the `arxrec` user.

   ```bash
   sudo -iu arxrec bash -c '
     cd /home/arxrec/arxiv-recommender/platform
     python3 -m venv .venv
     .venv/bin/pip install --upgrade pip
     .venv/bin/pip install -e .[dev] --extra-index-url https://download.pytorch.org/whl/cpu
   '
   ```

4. Pull the OpenAlex data, load it into Postgres, and train the first
   set of models. This writes pickled artefacts and the leaderboard JSON
   into `data/models/`.

   ```bash
   sudo -iu arxrec bash -c '
     cd /home/arxrec/arxiv-recommender/platform
     .venv/bin/python -m arxrec.data.openalex
     .venv/bin/python -m arxrec.data.loader
     OPENBLAS_NUM_THREADS=1 .venv/bin/python -m arxrec.train --max-eval-seeds 2000
   '
   ```

5. Install the systemd units.

   ```bash
   sudo cp /home/arxrec/arxiv-recommender/platform/deploy/systemd/*.service /etc/systemd/system/
   sudo cp /home/arxrec/arxiv-recommender/platform/deploy/systemd/*.timer   /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now arxrec-api.service
   sudo systemctl enable --now arxrec-refresh.timer
   sudo systemctl status arxrec-api.service
   curl -s http://127.0.0.1:8820/healthz | jq
   ```

6. Install the nginx site and issue a TLS cert.

   ```bash
   sudo cp /home/arxrec/arxiv-recommender/platform/deploy/nginx/api.papers.scottcampbell.io.conf \
            /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/api.papers.scottcampbell.io.conf \
              /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d api.papers.scottcampbell.io
   ```

7. Verify end-to-end.

   ```bash
   curl -s https://api.papers.scottcampbell.io/healthz
   curl -s "https://api.papers.scottcampbell.io/similar/1?k=5&algo=hybrid"
   ```

## DNS records to set up

| Type  | Name             | Target                                 | Proxy   |
|-------|------------------|----------------------------------------|---------|
| A     | `api.papers`     | VPS public IP                          | DNS only|
| CNAME | `papers`         | `<project>.pages.dev` (Cloudflare)     | proxied |

Cloudflare Pages issues the TLS cert for `papers.scottcampbell.io`
automatically once the CNAME is in place. The VPS handles its own TLS for
the API subdomain via certbot.

## Frontend on Cloudflare Pages

The frontend is a fully static Next.js export. There is no Node runtime
in production.

1. Verify the build locally:

   ```bash
   cd frontend
   cp .env.local.example .env.local
   npm install
   npm run build               # writes ./out
   ```

2. In the Cloudflare Pages dashboard create a project pointed at the
   GitHub repository, with build settings:

   - Build command: `cd frontend && npm install && npm run build`
   - Build output directory: `frontend/out`
   - Environment variable: `NEXT_PUBLIC_API_BASE = https://api.papers.scottcampbell.io`
   - Production branch: `main`

3. Add the custom domain `papers.scottcampbell.io` in
   Pages -> Custom Domains. Pages provisions the TLS cert automatically.

Every push to `main` triggers a Cloudflare build and an atomic deploy.

## Updating

```bash
sudo -iu arxrec bash -c '
  cd /home/arxrec/arxiv-recommender
  git fetch origin main
  git reset --hard origin/main
  cd platform
  .venv/bin/pip install -e .
'
sudo systemctl restart arxrec-api.service
```

Cloudflare Pages rebuilds the frontend automatically on every push.
