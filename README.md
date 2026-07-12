# MENA Job Monitor 🌍

**Automated job search pipeline for MENA-focused roles in Europe**

Built for: Moroccan MBA candidate targeting Spain EU Blue Card  
Profile: Arabic (native), English (strong), French (professional), MBA from University of Bradford

---

## What This System Does

This Python-based monitoring system automatically:

1. **Scrapes** 30+ target company career pages for new job openings
2. **Scores** each role based on your profile (Arabic requirement, MENA focus, sponsorship history, location)
3. **Filters** out duplicates, intern roles, and Spanish-required positions
4. **Ranks** opportunities from "HIGH PRIORITY" to "Skip"
5. **Notifies** you via email when high-priority roles appear
6. **Tracks** history so you never see the same job twice

---

## Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Your Profile

Edit `config.yaml`:
- Update your email in the `notification` section
- Adjust scoring weights if needed
- Add/remove companies from the tiers

### Step 3: Run the Monitor

```bash
python job_monitor.py
```

Results are saved to `./results/` as JSON and CSV files.

---

## Setting Up Daily Automation

### Option A: Cron Job (Linux/Mac)

```bash
# Open crontab editor
crontab -e

# Add this line to run every morning at 9 AM
0 9 * * * cd /path/to/job_monitor && python job_monitor.py >> cron.log 2>&1
```

### Option B: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task → Daily
3. Action: Start a program
4. Program: `python.exe`
5. Arguments: `job_monitor.py`
6. Start in: `C:\path	o\job_monitor`

### Option C: Cloud (Free Tier)

**GitHub Actions** (free for public repos, 2,000 min/month private):

Create `.github/workflows/job-monitor.yml`:

```yaml
name: Daily Job Monitor
on:
  schedule:
    - cron: '0 9 * * *'  # 9 AM UTC daily
  workflow_dispatch:  # Manual trigger

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python job_monitor.py
      - uses: actions/upload-artifact@v3
        with:
          name: job-results
          path: results/
```

**PythonAnywhere** (free tier, runs 24/7):
1. Upload files to PythonAnywhere
2. Set up a daily scheduled task
3. Results emailed to you automatically

---

## Understanding the Scoring System

| Factor | Points | Description |
|--------|--------|-------------|
| Arabic required | +15 | Your native language is the differentiator |
| French required | +10 | Second language asset |
| MENA/Africa focus | +15 | Direct market alignment |
| MBA level role | +10 | Education match |
| Spain location | +10 | Your visa target |
| Intern role | -30 | Not eligible for sponsorship |
| Spanish required | -20 | You don't speak Spanish |
| Entry-level | -15 | Below your experience level |
| High sponsorship company | +10 | Proven visa sponsor |
| Low sponsorship company | -10 | Unlikely to sponsor |

**Score Interpretation:**
- **85-100**: HIGH PRIORITY — Apply immediately
- **70-84**: Apply — Strong match, worth pursuing
- **60-69**: Monitor — Check back, may improve
- **0-59**: Skip — Not a fit

---

## Architecture

```
job_monitor.py (main orchestrator)
    ├── Config (config.yaml reader)
    ├── WebScraper (rate-limited HTTP client)
    ├── JobFetcher (fetches from LinkedIn, company pages, aggregators)
    ├── JobScorer (AI-like scoring based on your profile)
    ├── JobHistory (deduplication database)
    ├── ResultsManager (saves JSON/CSV/reports)
    └── Notifier (email alerts)
```

---

## Known Limitations & Workarounds

### 1. LinkedIn Blocks Scraping
**Problem**: LinkedIn aggressively blocks bots.  
**Solutions**:
- Use LinkedIn's RSS feeds: `https://www.linkedin.com/jobs/search?keywords=Arabic%20MENA&location=Spain&f_TPR=r86400`
- Use LinkedIn API (requires application)
- Manual: Set up LinkedIn job alerts and paste URLs into the monitor
- Use **Europe Language Jobs** and **Indeed** as proxies

### 2. Company Career Pages Use JavaScript
**Problem**: Many modern career pages (Greenhouse, Lever, Workday) load jobs via JS.  
**Solutions**:
- Use their JSON APIs directly (inspect network tab)
- Use Selenium/Playwright (heavier but works)
- Focus on aggregators that already scrape them

### 3. Rate Limiting
**Problem**: Too many requests get you blocked.  
**Built-in protection**:
- 2-second minimum delay between requests
- Random jitter added
- Session reuse with realistic headers
- Limited to 5 companies per run (adjust in code)

### 4. No Real-Time Notifications
**Problem**: System runs on schedule, not continuously.  
**Solutions**:
- Run every 2-4 hours instead of daily
- Use a cheap VPS ($3-5/month) for 24/7 operation
- Set up webhook to Slack/Discord/Telegram

---

## Recommended Enhancements

### Phase 1: Better Data Sources (Week 1)
- [ ] Add **Indeed** RSS feed scraping
- [ ] Add **Glassdoor** API integration
- [ ] Add **Europe Language Jobs** direct scraping
- [ ] Add **AngelList/Wellfound** for startup roles

### Phase 2: Smarter Matching (Week 2)
- [ ] Integrate OpenAI API for job description analysis
- [ ] Add semantic matching (not just keyword)
- [ ] Extract salary ranges from postings
- [ ] Identify hiring manager names from LinkedIn

### Phase 3: Application Automation (Week 3)
- [ ] Auto-fill application forms (Selenium)
- [ ] Generate tailored cover letters per role
- [ ] Track application status in Notion/Airtable
- [ ] Schedule follow-up reminders

### Phase 4: Intelligence Layer (Week 4)
- [ ] Monitor company hiring velocity (are they growing?)
- [ ] Track visa sponsorship success rates by company
- [ ] Alert when target hiring managers post on LinkedIn
- [ ] Predict which roles will open based on company expansion news

---

## File Structure

```
job_monitor/
├── job_monitor.py          # Main script
├── config.yaml             # Your profile & company list
├── requirements.txt        # Python dependencies
├── job_history.json        # Auto-generated: seen jobs database
├── results/                # Auto-generated: daily reports
│   ├── jobs_20260712_0900.json
│   ├── jobs_20260712_0900.csv
│   └── report_20260712.txt
├── cron.log                # Auto-generated: execution logs
└── README.md               # This file
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| No jobs found | Check internet connection; some sites block bots |
| Email not sending | Enable less secure apps or use app password in Gmail |
| Duplicate jobs | Delete `job_history.json` to reset |
| Score seems wrong | Adjust weights in `config.yaml` |

---

## Cost Breakdown

| Option | Cost | Effort | Reliability |
|--------|------|--------|-------------|
| Local computer + cron | Free | Low | Depends on PC being on |
| PythonAnywhere free | Free | Low | Good |
| PythonAnywhere paid | $5/month | Low | Excellent |
| VPS (DigitalOcean/Linode) | $5/month | Medium | Excellent |
| GitHub Actions | Free/$4/month | Medium | Good |
| Make.com/Zapier | $10-20/month | Low | Good (limited flexibility) |

---

## Next Steps

1. **Today**: Install and run manually to verify it works
2. **This week**: Set up daily automation (cron or cloud)
3. **Next week**: Add more data sources (Indeed, Europe Language Jobs)
4. **Ongoing**: Refine scoring based on which roles actually respond

---

*Built by Kimi K2.6 for a Moroccan MBA candidate targeting the EU Blue Card via Spain.*
*Last updated: 2026-07-12*
