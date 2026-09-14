import requests, os, time
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
    current_url = START_URL
    page_count = 0

    while current_url and page_count < max_pages:
        page_count += 1
        cache_filename = f"catalogue-page-{page_count}.html"
        html = fetch_page(current_url, cache_filename)

        all_links += extract_book_links(html, current_url)
        current_url = find_next_page(html, current_url)

    unique_links = list(dict.fromkeys(all_links))
    print(f"catalogue_pages={page_count} discovered={len(all_links)} unique_urls={len(unique_links)}")
    return unique_links


def main():
    discover_book_urls()


if __name__ == "__main__":
    main()