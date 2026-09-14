import requests, os, time
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin

CACHE_DIR = "cache"
USER_AGENT = "FlyRankInternshipA9/1.0 (+github.com/nailaanjum/Polite-Scrapper)"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"


def fetch_page(url, cache_filename):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_filename} ({len(html)} bytes)")
        return html

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=5)
    if response.status_code != 200:
        raise Exception(f"Fetch failed {url}: {response.status_code}")

    response.encoding = "utf-8"   # <-- add this line, before reading .text
    html = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"FETCH: {cache_filename} ({len(html)} bytes)")
    time.sleep(0.5)
    return html


def extract_book_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a_tag in soup.select("article.product_pod h3 a"):
        href = a_tag["href"]
        absolute_url = urljoin(page_url, href)
        links.append(absolute_url)
    return links


def find_next_page(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    next_tag = soup.select_one("li.next a")
    if next_tag:
        return urljoin(page_url, next_tag["href"])
    return None


def discover_book_urls(max_pages=3):
    all_links = []
    page_url_map = {}   # book_url -> which catalogue page it came from
    current_url = START_URL
    page_count = 0

    while current_url and page_count < max_pages:
        page_count += 1
        cache_filename = f"catalogue-page-{page_count}.html"
        html = fetch_page(current_url, cache_filename)

        links_on_this_page = extract_book_links(html, current_url)
        all_links += links_on_this_page
        for link in links_on_this_page:
            page_url_map[link] = current_url

        current_url = find_next_page(html, current_url)

    unique_links = list(dict.fromkeys(all_links))
    print(f"catalogue_pages={page_count} discovered={len(all_links)} unique_urls={len(unique_links)}")
    return unique_links, page_url_map


def extract_book_record(html, product_url, source_page):
    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.select_one("div.product_main")

    title = product_main.select_one("h1").text.strip()
    price_text = product_main.select_one("p.price_color").text.strip()
    availability_text = product_main.select_one("p.instock.availability").text.strip()

    rating_tag = product_main.select_one("p.star-rating")
    rating_text = rating_tag["class"][1] if rating_tag else None

    desc_heading = soup.select_one("#product_description")
    if desc_heading:
        description = desc_heading.find_next_sibling("p").text.strip()
    else:
        description = None

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
    for i, url in enumerate(book_urls, start=1):
        cache_filename = f"book-{i}.html"
        html = fetch_page(url, cache_filename)
        source_page = page_url_map.get(url, "unknown")
        record = extract_book_record(html, url, source_page)
        records.append(record)

    print(f"detail_pages={len(records)}")
    return records


def main():
    book_urls, page_url_map = discover_book_urls()
    records = extract_all_books(book_urls, page_url_map)

    # Print one complete record to prove all 8 keys are present
    print(records[0])


if __name__ == "__main__":
    main()