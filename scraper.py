import time
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SEARCH_QUERY = "video games"
NUM_PAGES = 5
OUTPUT_FILE = "data/aliexpress_games.csv"


def scrape_aliexpress_page(page, page_num):
    url = f"https://www.aliexpress.com/w/wholesale-{SEARCH_QUERY.replace(' ', '-')}.html?page={page_num}"
    print(f"[+] Fetching Page {page_num}: {url}")

    page.goto(url, wait_until="networkidle", timeout=60000)

    # Scroll down to trigger dynamic loading of items
    for _ in range(4):
        page.mouse.wheel(0, 1000)
        time.sleep(1)

    html_content = page.content()
    soup = BeautifulSoup(html_content, "html.parser")

    items = []
    cards = soup.select('a[href*="/item/"]')

    for card in cards:
        title_el = card.select_one("h1, h3, div[class*='title'], span[class*='title']")
        title = title_el.get_text(strip=True) if title_el else None

        if not title:
            continue

        price_el = card.select_one("div[class*='price'], span[class*='price']")
        price = price_el.get_text(strip=True) if price_el else "N/A"

        rating_el = card.select_one("span[class*='evaluation'], span[class*='rating']")
        rating = rating_el.get_text(strip=True) if rating_el else "N/A"

        link = card.get("href", "")
        if link.startswith("//"):
            link = "https:" + link

        items.append({
            "page_scraped": page_num,
            "title": title,
            "price": price,
            "rating": rating,
            "url": link
        })

    print(f"    --> Found {len(items)} items on page {page_num}")
    return items


def main():
    all_products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, h3c) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for page_num in range(1, NUM_PAGES + 1):
            try:
                products = scrape_aliexpress_page(page, page_num)
                all_products.extend(products)
                time.sleep(2)
            except Exception as e:
                print(f"[!] Error scraping page {page_num}: {e}")

        browser.close()

    df = pd.DataFrame(all_products)
    if not df.empty:
        df.drop_duplicates(subset=["title", "url"], inplace=True)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n[✓] Successfully scraped {len(df)} total unique items!")
        print(f"[✓] Saved results to '{OUTPUT_FILE}'")
    else:
        print("\n[!] No products scraped. Check selectors or bot-detection verification.")


if __name__ == "__main__":
    main()