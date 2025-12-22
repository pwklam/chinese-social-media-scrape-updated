import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
from logging_config import get_logger
import utils
import config

logger = get_logger()

async def scrape_post(url, conn):
    """
    Scrape WeChat article.
    """
    logger.info("[START] Launching Playwright browser for WeChat article...")
    logger.info(f"Target url: {url}")

    async with async_playwright() as p:
        # WeChat articles are usually publicly viewable, so we can use headless mode.
        browser = await p.chromium.launch(headless=True, args=['--start-maximized'])
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()

        try:
            # Navigate and wait for the page to be fully loaded
            # await page.goto(url, wait_until="networkidle")
            await page.goto(url)
            await page.wait_for_timeout(5000)

            # Article Title
            # Common selector for the WeChat article title
            title_locator = page.locator("#activity-name")
            # Wait for the title element to be visible
            await title_locator.wait_for(timeout=10000)
            title = await title_locator.inner_text()
            
            # Publish Date
            # Common selector for the WeChat publish date
            date_locator = page.locator("#publish_time")
            original_publish_date = await date_locator.inner_text()
            
            original_publish_date = original_publish_date.strip()
            # Attempt to convert to standard format: YYYY-MM-DD HH:MM:SS
            try:
                # Try format: YYYY-MM-DD HH:MM (e.g., '2023-11-22 14:56')
                dt_object = datetime.strptime(original_publish_date, '%Y年%m月%d日 %H:%M')
                formatted_date = dt_object.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                # Fallback to original text if parsing fails (e.g., relative date strings)
                logger.info(f"[WARN] Warning: Could not parse date '{formatted_date}'. Keeping original format.")
            
            publish_date = formatted_date

            # Article Content
            # Common selector for the main article content body
            content_locator = page.locator("#js_article")
            # We strip the text to remove leading/trailing whitespace
            content = (await content_locator.inner_text()).strip()

            # Post user
            user_name_locator = page.locator("#js_wx_follow_nickname")
            user_name = await user_name_locator.inner_text()

            item = [{
                'unnamed': None,
                'user_name': user_name,
                'publication_date': publish_date,
                'content': f"{title}\n{content}",
                'shared_count': None,
                'comment_count': None,
                'like_count': None,
                'link1': url,
                'link2': None,
                'content_segmented': None,
                'is_agriculture_related': None,
                'index_number': None
            }]
            logger.info(f"[SAVE] Inserting scraped data into the database...: {item}")

            utils.insert_data(conn, config.table_name, item)

        except Exception as e:
            logger.info(f"[ERROR] An error occurred: {e}")
            logger.info("Possible reasons: Page structure changed or main selectors failed.")
        finally:
            logger.info("[CLOSE] Closing browser.")
            await browser.close()
