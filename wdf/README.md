# WeddingDealsFinder — Setup Guide

Find the best wedding deals, discounts, and coupons — updated automatically every day.

---

## How it works

```
Every day at 7am UTC
       ↓
GitHub Actions runs fetch_deals.py
       ↓
Script pulls deals from ShareASale API
       ↓
Filters & ranks wedding-relevant deals
       ↓
Writes deals.json to site/
       ↓
Deploys site/ folder to Netlify
       ↓
WeddingDealsFinder.com updates live ✓
```

---

## One-time setup (~45 minutes total)

### Step 1 — Buy your domain
Go to Namecheap.com and purchase weddingdealsfinder.com (~$12/year)

---

### Step 2 — Create GitHub account & upload this project
1. Go to github.com → Sign up (free)
2. Click New repository → name it `weddingdealsfinder` → Public → Create
3. Click "uploading an existing file" → drag in all project files → Commit

---

### Step 3 — Create Netlify account
1. Go to netlify.com → Sign up with GitHub (free)
2. Add new site → Import from GitHub → select weddingdealsfinder
3. Set publish directory to: `site`
4. Click Deploy
5. Note your Site ID from Site settings → General
6. Connect your domain under Domain Management

---

### Step 4 — Get your Netlify API token
1. Netlify → avatar → User settings → Applications
2. New access token → name it "GitHub Actions" → Generate
3. Copy and save it (only shown once)

---

### Step 5 — Sign up for ShareASale
1. Go to shareasale.com → Affiliate Sign Up
2. Use your Netlify URL as your website
3. Once approved, go to Account → API Access to get your credentials
4. Apply to wedding merchants: search "wedding", "bridal", "flowers", "invitations"

---

### Step 6 — Add secrets to GitHub
Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add these five secrets:

| Secret name              | Value                        |
|--------------------------|------------------------------|
| SHAREASALE_AFFILIATE_ID  | Your ShareASale affiliate ID |
| SHAREASALE_API_TOKEN     | Your ShareASale API token    |
| SHAREASALE_SECRET_KEY    | Your ShareASale secret key   |
| NETLIFY_AUTH_TOKEN       | Token from Step 4            |
| NETLIFY_SITE_ID          | Site ID from Step 3          |

---

### Step 7 — Add your merchant IDs
1. Open scripts/fetch_deals.py
2. Find the MERCHANT_IDS list
3. Replace example IDs with your real approved merchant IDs
   (find these in ShareASale under Merchants → My Merchants)

---

### Step 8 — Trigger your first run
1. Go to GitHub repo → Actions tab
2. Click "Refresh deals & deploy" → Run workflow
3. Wait ~2 minutes → visit your Netlify URL
4. Deals are live!

After this, it runs automatically every day at 7am UTC.

---

## File structure

```
weddingdealsfinder/
├── .github/
│   └── workflows/
│       └── refresh_deals.yml   ← Daily schedule
├── scripts/
│   └── fetch_deals.py          ← Deal fetcher
├── site/
│   ├── index.html              ← Your website
│   └── deals.json              ← Auto-generated daily
└── README.md
```

---

## Costs

| Service        | Cost         |
|----------------|--------------|
| GitHub         | Free         |
| Netlify        | Free         |
| ShareASale     | Free         |
| Domain name    | ~$12/year    |
| **Total**      | **~$12/year**|
