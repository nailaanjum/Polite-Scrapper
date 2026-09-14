import requests, os, time, re, json
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pydantic import BaseModel, HttpUrl, ValidationError

CACHE_DIR = "cache"
OUTPUT_DIR = "output"
USER_AGENT = "FlyRankInternshipA9/1.0 (+github.com/nailaanjum/Polite-Scrapper)"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

# A URL that does not exist — used to prove failure-handling works.
# Remove this once you've confirmed the checkpoint, or keep it commented
# out for normal runs.
FAKE_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_0000/index.html"


class FetchError(Exception):
    def __init__(self, url, status_code):
        self.url = url
        self.status_code = status_code
        super().__init__(f"Fetch failed {url}: status {status_code}")


def fetch_page(url, cache_filename):
    """Returns (html, was_cache_hit)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_filename} ({len(html)} bytes)")
        return html, True

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=5)
    if response.status_code != 200:
        raise FetchError(url, response.status_code)

    response.encoding = "utf-8"
    html = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"FETCH: {cache_filename} ({len(html)} bytes)")
    time.sleep(0.5)
    return html, False


def fetch_with_retry(url, cache_filename, max_retries=1):
    for attempt in range(max_retries + 1):
        try:
            return fetch_page(url, cache_filename)
        except FetchError as e:
            if e.status_code in (404, 403):
                raise  # asking again won't help — give up immediately
            if attempt < max_retries:
                print(f"RETRY: {url} (status {e.status_code}), attempt {attempt + 1}")
                time.sleep(1)
                continue
            raise  # out of retries


def extract_book_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    return [urljoin(page_url, a["href"]) for a in soup.select("article.product_pod h3 a")]


def find_next_page(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    next_tag = soup.select_one("li.next a")
    return urljoin(page_url, next_tag["href"]) if next_tag else None


def discover_book_urls(max_pages=3):
    all_links = []
    page_url_map = {}
    current_url = START_URL
    page_count = 0
    fetched, cached = 0, 0

    while current_url and page_count < max_pages:
        page_count += 1
        html, was_cache_hit = fetch_with_retry(current_url, f"catalogue-page-{page_count}.html")
        cached += was_cache_hit
        fetched += not was_cache_hit

        links_on_page = extract_book_links(html, current_url)
        all_links += links_on_page
        for link in links_on_page:
            page_url_map[link] = current_url

        current_url = find_next_page(html, current_url)

    unique_links = list(dict.fromkeys(all_links))
    print(f"catalogue_pages={page_count} discovered={len(all_links)} unique_urls={len(unique_links)}")
    return unique_links, page_url_map, fetched, cached


def extract_book_record(html, product_url, source_page):
    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.select_one("div.product_main")

    title = product_main.select_one("h1").text.strip()
    price_text = product_main.select_one("p.price_color").text.strip()
    availability_text = product_main.select_one("p.instock.availability").text.strip()

    rating_tag = product_main.select_one("p.star-rating")
    rating_text = rating_tag["class"][1] if rating_tag else None

    desc_heading = soup.select_one("#product_description")
    description = desc_heading.find_next_sibling("p").text.strip() if desc_heading else None

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def extract_all_books(book_urls, page_url_map):
    records = []
    failed_pages = []
    fetched, cached = 0, 0

    for i, url in enumerate(book_urls, start=1):
        try:
            html, was_cache_hit = fetch_with_retry(url, f"book-{i}.html")
            cached += was_cache_hit
            fetched += not was_cache_hit

            source_page = page_url_map.get(url, "unknown")
            records.append(extract_book_record(html, url, source_page))
        except Exception as e:
            print(f"FAILED: {url} ({e})")
            failed_pages.append({"url": url, "reason": str(e)})
            continue  # one bad page never stops the run

    print(f"detail_pages={len(records)} failed={len(failed_pages)}")
    return records, failed_pages, fetched, cached


# ---------- Stage 4: schema, normalize, validate ----------

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


def parse_price(price_text):
    match = re.search(r"[\d.]+", price_text)
    if not match:
        raise ValueError(f"could not parse price from '{price_text}'")
    return float(match.group())


def normalize_and_validate(raw_records):
    valid_by_url = {}
    errors = []

    for raw in raw_records:
        try:
            price_gbp = parse_price(raw["price_text"])
            candidate = {**raw, "price_gbp": price_gbp}
            book = Book(**candidate)
            valid_by_url[str(book.product_url)] = json.loads(book.model_dump_json())
        except (ValidationError, ValueError, KeyError) as e:
            errors.append({"record": raw, "reason": str(e)})

    return list(valid_by_url.values()), errors


def save_output(valid_records, errors):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "books.json"), "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2)
    with open(os.path.join(OUTPUT_DIR, "errors.json"), "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2)


def save_run_report(report):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "run-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def main():
    start_time = datetime.now(timezone.utc)

    book_urls, page_url_map, cat_fetched, cat_cached = discover_book_urls()

    # --- Stage 5 proof: inject one fake URL on purpose ---
    book_urls.append(FAKE_URL)
    page_url_map[FAKE_URL] = "manual-test"
    # -------------------------------------------------------

    raw_records, failed_pages, det_fetched, det_cached = extract_all_books(book_urls, page_url_map)
    valid_records, errors = normalize_and_validate(raw_records)
    save_output(valid_records, errors)

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    report = {
        "start_time": start_time.isoformat(),
        "duration_seconds": duration,
        "pages_fetched": cat_fetched + det_fetched,
        "cache_hits": cat_cached + det_cached,
        "valid_records": len(valid_records),
        "invalid_records": len(errors),
        "failed_pages": len(failed_pages),
    }
    save_run_report(report)

    print(f"valid_records={len(valid_records)} errors={len(errors)} failed_pages={len(failed_pages)}")


if __name__ == "__main__":
    main()