# AliExpress Product Web Scraper

A Python web scraper that collects product listings for a given search query from AliExpress and saves them to a CSV file. Built for a web scraping assignment.

## What the project is about

The goal was to build a working scraper that can handle a **modern, JavaScript-heavy e-commerce site** — something a simple `requests` + BeautifulSoup approach cannot do, because the product listings are rendered dynamically by JavaScript after the page loads.

The scraper visits the AliExpress wholesale search results for the query **"video games"**, walks through **5 pages** of results, extracts the **title, price, rating, and product URL** of each listing, and writes everything into a single CSV file:

```
data/aliexpress_games.csv
```

The current dataset contains **155 unique products** across 5 pages.

| Column         | Description                                              |
| -------------- | -------------------------------------------------------- |
| `page_scraped` | Which results page the item came from (1–5)              |
| `title`        | Full product title                                       |
| `price`        | Price text as displayed on the page (currency: KES)      |
| `rating`       | Seller/product rating (`N/A` when not shown in the card) |
| `url`          | Direct link to the product page                          |

## 🗂 Project structure

```
web-scraping/
├── scraper.py                 # The scraper itself
├── Pipfile / Pipfile.lock     # Dependency definitions (pipenv)
├── data/
│   └── aliexpress_games.csv   # Scraped output
└── README.md
```

## 🛠 How I did it (approach)

### 1. Chose the right tool: Playwright

AliExpress renders its search results with JavaScript, so plain HTTP requests return an empty page. I used **Playwright** to launch a real Chromium browser that executes the page's JavaScript, exactly like a normal user would see it.

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ... Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
```

A realistic **User-Agent** header was set on the browser context so the request looks like it comes from a normal desktop Chrome browser.

### 2. Navigated page by page

The search URL is built from a constant query and a page number:

```python
SEARCH_QUERY = "video games"
NUM_PAGES = 5
url = f"https://www.aliexpress.com/w/wholesale-{SEARCH_QUERY.replace(' ', '-')}.html?page={page_num}"
```

Each page is loaded with `wait_until="networkidle"`, which waits until the browser stops making network requests — a good signal that the page (and its lazy-loaded content) has finished rendering.

### 3. Handled lazy/infinite-scroll loading

AliExpress only loads a portion of the product grid initially. To force more items to render, I simulated a human scrolling down the page four times:

```python
for _ in range(4):
    page.mouse.wheel(0, 1000)   # scroll down 1000px
    time.sleep(1)               # give the page time to load more items
```

After scrolling, the full rendered HTML is captured with `page.content()`.

### 4. Parsed the HTML with BeautifulSoup

Once the rendered HTML was in hand, **BeautifulSoup** did the extraction. Product cards were located by targeting anchor tags whose `href` contains `/item/` — the URL pattern AliExpress uses for every product page:

```python
soup = BeautifulSoup(html_content, "html.parser")
cards = soup.select('a[href*="/item/"]')
```

Within each card, I used tolerant CSS selectors so small class-name changes don't break the scraper:

- **Title** → `h1`, `h3`, or any element whose class contains `title`
- **Price** → any element whose class contains `price`
- **Rating** → any element whose class contains `evaluation` or `rating`

Relative links (`//www.aliexpress.com/...`) were converted to absolute URLs by prefixing `https:`.

### 5. Rate limiting and error handling

- A `time.sleep(2)` pause between pages keeps the request rate polite and reduces the chance of triggering bot detection.
- Each page is wrapped in a `try/except`, so one failed page doesn't kill the whole run — the scraper just logs the error and continues with the next page.

### 6. Cleaning and saving with pandas

All items from all pages are collected into one list, converted to a **pandas** DataFrame, and cleaned:

```python
df = pd.DataFrame(all_products)
df.drop_duplicates(subset=["title", "url"], inplace=True)  # remove repeated listings
df.to_csv(OUTPUT_FILE, index=False)
```

De-duplicating on `title` + `url` is important because sponsored/recommended products often appear on multiple pages. The result is written to `data/aliexpress_games.csv`.

## Running it

**Requirements:** Python 3.14, [pipenv](https://pipenv.pypa.io/)

```bash
# 1. Install dependencies
pipenv install

# 2. Install the Playwright Chromium browser
pipenv run playwright install chromium

# 3. Run the scraper (a browser window will open — it runs headed)
pipenv run python scraper.py
```

Output:

```
[+] Fetching Page 1: https://www.aliexpress.com/w/wholesale-video-games.html?page=1
    --> Found 30 items on page 1
...
[✓] Successfully scraped 155 total unique items!
[✓] Saved results to 'data/aliexpress_games.csv'
```

To scrape a different keyword or number of pages, change the constants at the top of `scraper.py`:

```python
SEARCH_QUERY = "video games"
NUM_PAGES = 5
OUTPUT_FILE = "data/aliexpress_games.csv"
```

## Dependencies

| Package          | Purpose                                                    |
| ---------------- | ---------------------------------------------------------- |
| `playwright`     | Drives a real Chromium browser to render the JS-heavy page |
| `beautifulsoup4` | Parses the rendered HTML and extracts the fields           |
| `pandas`         | Cleans, de-duplicates, and exports the data to CSV         |

## Notes & limitations

- The scraper runs **headed** (`headless=False`) by default — this is intentional, as AliExpress is more likely to serve content (or show a bot-verification challenge) to a visible browser. If you switch to `headless=True` and get no results, this is likely why.
- **Ratings** frequently come back as `N/A` because AliExpress does not always render the rating inside the search-result card.
- **Prices** are stored as raw display text (including discount text such as `KSh3,372KSh3,372KSh 638.00saved`) and are not yet parsed into clean numeric values — a possible follow-up step for analysis.
- AliExpress's markup and anti-bot measures change over time; if the scraper stops finding items, the CSS selectors in `scrape_aliexpress_page()` may need updating.
- Always check a website's `robots.txt` and Terms of Service, and scrape responsibly (low frequency, small volumes).
# Web-Scrapping
