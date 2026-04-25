import asyncio
import sys
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SKIP_PATTERNS = [
    "/blog/", "/changelog/", "/release/", "/releases/",
    "/login", "/signup", "/register", "/pricing",
    "/search", "/404", "/500"
]

def should_skip(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(pattern in path for pattern in SKIP_PATTERNS)


async def _crawl_async(start_url: str, max_pages: int) -> list[dict]:
    visited = set()
    results = []
    base_domain = urlparse(start_url).netloc
    to_visit = [start_url]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)

            if url in visited:
                continue
            if urlparse(url).netloc != base_domain:
                continue
            if should_skip(url):
                continue

            try:
                print(f"Crawling: {url}")

                # Use domcontentloaded — faster and more reliable
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                # Wait for JS to render links — try common doc site selectors
                for selector in ["nav a", "aside a", ".sidebar a", "[class*='nav'] a", "a[href]"]:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        break
                    except:
                        continue

                # Give JS frameworks a moment to finish
                await asyncio.sleep(1.5)

                # Get fully rendered HTML
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Grab ALL links BEFORE stripping nav/sidebar
                all_links = []
                for link in soup.find_all("a", href=True):
                    full_url = urljoin(url, link["href"]).split("#")[0]
                    all_links.append(full_url)

                # Clean content for storage
                for tag in soup(["nav", "footer", "header", "aside", "script", "style"]):
                    tag.decompose()

                title = soup.title.string if soup.title else url
                content = soup.get_text(separator="\n", strip=True)

                if len(content) > 100:
                    results.append({"url": url, "title": title, "content": content})

                visited.add(url)

                # Queue new links
                for full_url in all_links:
                    full_parsed = urlparse(full_url)
                    if (
                        full_url not in visited
                        and full_parsed.netloc == base_domain
                        and not should_skip(full_url)
                        and full_parsed.path not in ("", "/")
                        and full_parsed.scheme in ("http", "https")
                    ):
                        to_visit.append(full_url)

                print(f"  → found {len(all_links)} links, queue: {len(to_visit)}")

            except Exception as e:
                print(f"Failed to crawl {url}: {e}")
                visited.add(url)

        await context.close()
        await browser.close()

    print(f"Crawled {len(results)} pages.")
    return results


def crawl_in_thread(start_url: str, max_pages: int) -> list[dict]:
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_crawl_async(start_url, max_pages))
    finally:
        loop.close()