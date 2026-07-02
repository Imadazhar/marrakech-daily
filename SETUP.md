# Marrakech Daily — AI Agent Setup Guide

## What this system does

Every morning at **06:00 Morocco time**, a GitHub Actions workflow:

1. Scrapes today's news from three French sources:
   - [fr.kech24.com](https://fr.kech24.com)
   - [madein.city/marrakech](https://www.madein.city/marrakech/fr/stories)
   - [alphabourse.ma](https://alphabourse.ma)

2. Passes each article through an AI pipeline (GPT-4o-mini) that:
   - Extracts the key facts
   - Writes a completely **original English article** (never a translation)
   - Generates SEO title, description, tags, slug, excerpt
   - Assigns category and reading time
   - Adds attribution to the original source

3. Checks for duplicates and skips already-published stories

4. Publishes up to **20 new articles** per day

5. Rebuilds `index.html` and commits to GitHub → triggers GitHub Pages automatically

---

## One-time setup

### Step 1 — Add your OpenAI API key as a GitHub Secret

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `OPENAI_API_KEY`
5. Value: your OpenAI API key (starts with `sk-...`)
6. Click **Add secret**

Get your key at: https://platform.openai.com/api-keys

**Estimated cost:** ~$1–3/month at 20 articles/day with gpt-4o-mini.

### Step 2 — Enable GitHub Actions

1. Go to your repository → **Actions** tab
2. If prompted, click **"I understand my workflows, go ahead and enable them"**

### Step 3 — (Optional) Run immediately to test

Go to **Actions** → **Daily News — Marrakech Daily AI Agent** → **Run workflow** → **Run workflow**

The first run will publish 20 articles and rebuild your site.

---

## Manual publish

### Via GitHub Actions (recommended)

1. Go to **Actions** → **Manual Publish — Marrakech Daily**
2. Click **Run workflow**
3. Enter a headline:
   ```
   New luxury hotel opens in Marrakech
   ```
4. Click **Run workflow**

An article is generated and published within ~30 seconds.

### Via command line (local)

```bash
# Install dependencies
pip install -r agent/requirements.txt

# Set your API key
export OPENAI_API_KEY="sk-..."

# Publish an article
python agent/manual_publish.py "New luxury hotel opens in Marrakech"

# Or run the full daily pipeline
python agent/main.py

# Dry run (test without saving)
python agent/main.py --dry-run
```

---

## File structure

```
.github/workflows/
  daily-news.yml          ← Daily scheduler (06:00 Morocco time)
  manual-publish.yml      ← Manual publish from GitHub Actions

agent/
  config.py               ← All configuration (sources, categories, authors...)
  scraper.py              ← Web scrapers for kech24, madein.city, alphabourse
  ai_pipeline.py          ← OpenAI rewriting pipeline
  deduplicator.py         ← Duplicate detection
  publisher.py            ← Article JSON persistence
  site_builder.py         ← Rebuilds index.html from template
  main.py                 ← Main entry point (daily run)
  manual_publish.py       ← CLI / manual publish entry point
  requirements.txt        ← Python dependencies
  logs/                   ← Run logs (not committed)

templates/
  site.html.j2            ← Jinja2 HTML template for the full site

_data/
  articles.json           ← All published articles (source of truth)
  published_hashes.json   ← Deduplication store

index.html                ← Generated site (auto-rebuilt by agent)
```

---

## Configuration

Edit `agent/config.py` to customise:

| Setting | Description |
|---|---|
| `MAX_ARTICLES_PER_RUN` | Articles per daily run (default: 20) |
| `OPENAI_MODEL` | AI model (default: gpt-4o-mini) |
| `NEWS_SOURCES` | Sources to scrape |
| `AUTHORS` | Byline pool |
| `CATEGORIES` | Article categories |
| `SITE_TITLE` | Site name |

---

## Troubleshooting

**Agent runs but publishes 0 articles**
- Check the Actions log (download artifact from the run)
- Make sure `OPENAI_API_KEY` secret is set correctly
- The sources may have changed structure — check scraper output in logs

**Site doesn't update after a run**
- Check that GitHub Pages is enabled: Settings → Pages → Source: main branch / root
- Confirm the workflow pushed (check the commit history)

**Duplicate articles appearing**
- The deduplication store is in `_data/published_hashes.json`
- It's committed after every run; if a run fails mid-way, some hashes may not be saved

**Rate limits / API errors**
- The agent has built-in retry logic (3 attempts with exponential backoff)
- If OpenAI is down, the run fails gracefully with an error in the log

---

## Morocco time schedule

Morocco uses **UTC+1** year-round (since 2019). The cron is set to `0 5 * * *` (05:00 UTC = 06:00 Morocco time).

> **Note:** During Ramadan, Morocco temporarily reverts to UTC+0. The published articles will still appear — just one hour early in local time.
