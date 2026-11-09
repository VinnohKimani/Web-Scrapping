import time
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SEARCH_QUERY = "video games"
NUM_PAGES = 5
OUTPUT_FILE = "data/aliexpress_games.csv"


def scrape_page(page, page_num):
    # Convert query into AliExpress URL format 
    formatted_query = SEARCH_QUERY.replace(" ", "-")
    url = f"https://www.aliexpress.com/w/wholesale-{formatted_query}.html?page={page_num}"
    print(f"Scraping Page {page_num}: {url}")

    # Load page and wait until network activity settles
    page.goto(url, wait_until="networkidle", timeout=60000)

    # Scroll down 4 times so lazy-loaded items appear
    for _ in range(4):
        page.mouse.wheel(0, 1000)
        time.sleep(1)

    # Parse the fully rendered HTML using BeautifulSoup
    soup = BeautifulSoup(page.content(), "html.parser")

    # Each product card on AliExpress contains a link with '/item/'
    cards = soup.select('a[href*="/item/"]')
    items = []

    for card in cards:
        # Extract product title
        title_element = card.select_one("h1, h3, div[class*='title'], span[class*='title']")
        if not title_element:
            continue  # Skip non-product links
        title = title_element.get_text(strip=True)

        # Extract price (or 'N/A' if missing)
        price_element = card.select_one("div[class*='price'], span[class*='price']")
        price = price_element.get_text(strip=True) if price_element else "N/A"

        # Extract rating (or 'N/A' if missing)
        rating_element = card.select_one("span[class*='evaluation'], span[class*='rating']")
        rating = rating_element.get_text(strip=True) if rating_element else "N/A"

        # Extract product link 
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

    print(f" -> Found {len(items)} items on page {page_num}")
    return items


def main():
    all_products = []

    # Launch Playwright browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0  AppleWebKit/537.36  Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for page_num in range(1, NUM_PAGES + 1):
            try:
                products = scrape_page(page, page_num)
                all_products.extend(products)
                time.sleep(2)  
            except Exception as e:
                print(f"Could not scrape page {page_num}: {e}")

        browser.close()

    # Convert scraped records to a pandas DataFrame
    df = pd.DataFrame(all_products)

    if not df.empty:
        # Remove duplicate items that appeared across multiple pages
        df.drop_duplicates(subset=["title", "url"], inplace=True)

        # Save to CSV file
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSuccess! Saved {len(df)} unique products to '{OUTPUT_FILE}'")
    else:
        print("\nNo products were found. Please check your selectors or connection.")


if __name__ == "__main__":
    main()