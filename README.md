# Polite Scraper — Books to Scrape

A cache-first scraper that fetches, validates, and reports on book
data from books.toscrape.com — with retry logic and graceful failure
handling.

## Target classification
- **Site:** https://books.toscrape.com
- **Why this site:** a purpose-built scraping sandbox (toscrape.com)
  intended for people to practice scraping techniques on.
- **Scope:** first 3 catalogue pages only (60 books).
- **Data collected:** title, product URL, price, availability, star
  rating, description, and provenance (source page + fetch timestamp).
- **robots.txt result:** 404 — no file found. A missing file is not
  permission on its own; permission here comes from the site's own
  stated purpose as a sandbox, not from the absence of a rules file.

I will not reuse this code on another site without checking its
rules and terms first.

## Install and run
```bash
pip install -r requirements.txt
python src/main.py
```
Running it produces `output/books.json` and `output/run-report.json`.

## Record schema
```python
class Book(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str | None
    description: str | None
    source_page: str
    fetched_at: str
```

## Politeness rules
- Identifies itself with a named User-Agent
  (`FlyRankInternshipA9/1.0`)
- 5-second timeout on every request
- 0.5-second delay between real (non-cached) requests only
- Every page is cached locally after first fetch — repeat runs read
  from disk, never re-hit the live site
- Failed requests retry once for timeouts/5xx only; 404/403 are never
  retried

## Sample run-report.json
```json
{PASTE YOUR CLEAN RUN'S ACTUAL OUTPUT HERE}
```

## Why this needed no browser
The catalogue and book data are already present in the HTML the
server sends on first request — a headless browser would only add
rendering cost with no additional data gained.

## Ethics note
Scrape only sites that explicitly allow it, or where terms/robots.txt
don't forbid it. Use an official API instead of scraping when one
exists. Never bypass logins, paywalls, or explicit blocks. Collect
only the data actually needed for the task, not everything reachable.

## Known limitation
Selectors assume the current page structure (fixed CSS classes for
price, availability, rating, description). If the site's HTML layout
changes, extraction will fail validation silently rather than adapt —
Stage 4's schema will catch bad data, but won't tell you *why* the
site changed.