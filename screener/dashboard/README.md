# 📈 Stock Screener Dashboard

Zero-cost automated stock screening dashboard using GitHub Actions + GitHub Pages.

## Features

- **Daily automated runs** via GitHub Actions (free cron)
- **Visual dashboard** on GitHub Pages (free hosting)
- **Zero AI tokens** - pure Python screeners
- **Mobile responsive** design
- **Real-time updates** (refreshes every 5 minutes)

## Screeners

1. **Structure Break + SMMA 15/29**: Bullish structure breaks with moving average crossovers
2. **Mark Minervini SEPA**: 8-point trend template for Stage 2 uptrends

## Setup (5 minutes)

### 1. Push to GitHub

```bash
# From your workspace root
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/stock-screener.git
git push -u origin main
```

### 2. Enable GitHub Pages

1. Go to your repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** → Folder: **/ (root)**
4. Click **Save**

### 3. Update GitHub Pages Path

Edit `.github/workflows/daily-screener.yml` and add this step after "Run daily screeners":

```yaml
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./screener/dashboard
          publish_branch: gh-pages
```

OR configure GitHub Pages to serve from `screener/dashboard` directory:
1. Settings → Pages
2. Source: Deploy from branch
3. Branch: `main` → Folder: `/screener/dashboard`

### 4. Enable Workflow Permissions

1. Go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select:
   - ✅ **Read and write permissions**
3. Click **Save**

### 5. Test It

Trigger manually first:
1. Go to **Actions** tab
2. Select "Daily Stock Screener"
3. Click **Run workflow**
4. Wait 5-10 minutes for completion

### 6. Access Dashboard

Your dashboard will be live at:
```
https://YOUR_USERNAME.github.io/stock-screener/
```

## Customization

### Change Schedule

Edit `.github/workflows/daily-screener.yml`:

```yaml
on:
  schedule:
    # Run at 2 PM UTC (10 AM EST) every weekday
    - cron: '0 14 * * 1-5'
```

Cron syntax: `minute hour day month weekday`

### Filter Tickers

Edit `screener/tickers.csv` to modify the universe.

### Styling

Edit `screener/dashboard/index.html` CSS section.

## Costs

**$0.00** - Everything runs on free GitHub infrastructure:
- GitHub Actions: 2,000 minutes/month (free)
- GitHub Pages: Free for public repos
- No API costs, no cloud hosting, no AI tokens

## Local Testing

```bash
cd screener
source venv/bin/activate
python run_daily_json.py

# Open dashboard locally
cd dashboard
python -m http.server 8000
# Visit: http://localhost:8000
```

## Troubleshooting

**Screener fails?**
- Check Actions logs for Python errors
- Verify `requirements.txt` is complete
- Ensure tickers.csv is valid

**Dashboard not updating?**
- Check GitHub Pages is enabled
- Verify workflow has write permissions
- Check Actions tab for failed runs

**No data showing?**
- Run workflow manually first
- Check `screener/dashboard/data/` has JSON files
- Open browser console for errors

## Future Enhancements

- Historical data graphs
- Email alerts for signals
- Customizable filters
- Performance tracking
- Sector breakdown
