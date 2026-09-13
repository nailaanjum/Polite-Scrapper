import requests, os, time

CACHE_DIR = "cache"
USER_AGENT = "FlyRankInternshipA9/1.0 (+github.com/nailaanjum/Polite-Scrapper)"

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


def main():
    fetch_page(
        "https://books.toscrape.com/catalogue/page-1.html",
        "catalogue-page-1.html"
    )


if __name__ == "__main__":
    main()