# 🚀 Quick Start Guide

## What You Have

A **zero-cost automated stock screener** that:
- ✅ Runs daily via GitHub Actions (free cron)
- ✅ Hosts dashboard on GitHub Pages (free hosting)  
- ✅ Uses **zero AI tokens** - pure Python
- ✅ Works on mobile

## Setup in 3 Steps

### 1. Create GitHub Repo

```bash
cd ~/.openclaw/workspace
git init
git add .
git commit -m "Initial commit: Stock screener dashboard"

# Create repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/stock-screener.git
git push -u origin main
```

### 2. Enable GitHub Pages

1. Go to your repo on GitHub
2. Click **Settings** → **Pages**
3. Under "Build and deployment":
   - Source: **Deploy from a branch**
   - Branch: **main**
   - Folder: **/screener/dashboard**
4. Click **Save**

### 3. Enable GitHub Actions

1. Go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions":
   - Select: **Read and write permissions**
3. Click **Save**

## First Run

Trigger manually to test:

1. Go to **Actions** tab on GitHub
2. Click **"Daily Stock Screener"** workflow
3. Click **"Run workflow"** dropdown
4. Click green **"Run workflow"** button
5. Wait 5-10 minutes

## Access Dashboard

After the first run completes:

```
https://YOUR_USERNAME.github.io/stock-screener/
```

## Automatic Schedule

The workflow runs automatically at **9:00 AM UTC** every weekday (Monday-Friday).

To change the time, edit `.github/workflows/daily-screener.yml`:

```yaml
on:
  schedule:
    # Run at 2 PM UTC (10 AM EST)
    - cron: '0 14 * * 1-5'
```

Cron format: `minute hour day month weekday`

## Test Locally

```bash
cd ~/.openclaw/workspace/screener
source venv/bin/activate

# Run screeners
python run_daily_json.py

# Start local server
cd dashboard
python -m http.server 8000

# Visit: http://localhost:8000
```

## Costs

**$0.00** - Everything is free:
- GitHub Actions: 2,000 minutes/month
- GitHub Pages: Free for public repos
- No cloud hosting fees
- No AI tokens used

## Troubleshooting

**Dashboard shows "Loading..."?**
- Run the GitHub Action workflow once
- Check that `screener/dashboard/data/*.json` files exist
- Open browser dev console for errors

**Workflow fails?**
- Check Actions tab for error logs
- Verify permissions are set to "Read and write"
- Check Python dependencies in `requirements.txt`

**Need help?**
Read full docs in `README.md`
