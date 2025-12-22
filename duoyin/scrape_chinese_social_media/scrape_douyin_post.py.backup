import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
import json
import os
import utils
import config
from logging_config import get_logger

logger = get_logger()

# Path to save login session
SESSION_FILE = "douyin_session.json"

async def extract_details_new(page):
    details = {
        "title": None,
        "content": None,
        "like_count": None,
        "comment_count": None,
        "share_count": None,
        "publish_time": None
    }

    try:
        title = await page.locator(
            'xpath=(//div[@data-e2e="user-info"]/div[2]/a/div)[2]'
        ).inner_text()
        details["title"] = title. split("\n")[0]
        logger.info(f"Title: {details['title']}")
    except Exception as e: 
        logger.warning(f"Title error: {e}")

    try:
        details["content"] = await page.locator('xpath=//div[@data-e2e="detail-video-info"]/div[1]/div/h1').inner_text()
        logger.info(f"Content:  {details['content'][: 50]}...")
    except Exception as e: 
        logger.warning(f"Content error:  {e}")

    try:
        details["like_count"] = await page.locator('xpath=//div[@data-e2e="detail-video-info"]/div[2]/div[1]/div[1]/span').inner_text()
        logger.info(f"Likes: {details['like_count']}")
    except Exception as e:
        logger.warning(f"Like count error: {e}")

    try: 
        details["comment_count"] = await page.locator('xpath=//div[@data-e2e="detail-video-info"]/div[2]/div/div[2]/span').inner_text()
        logger.info(f"Comments:  {details['comment_count']}")
    except Exception as e: 
        logger.warning(f"Comment count error: {e}")

    try: 
        details["share_count"] = await page.locator('xpath=//div[@data-e2e="detail-video-info"]/div[2]/div/div[4]/span').inner_text()
        logger.info(f"Shares: {details['share_count']}")
    except Exception as e:
        logger.warning(f"Share count error:  {e}")

    try:
        publish_time = await page.locator('span[data-e2e="detail-video-publish-time"]').inner_text()
        publish_time = publish_time.replace('发布时间：', '').strip()
        dt_object = datetime.strptime(publish_time. strip(), '%Y-%m-%d %H:%M')
        details["publish_time"] = dt_object.strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Publish time: {details['publish_time']}")
    except Exception as e:
        logger.warning(f"Publish time error: {e}")

    return details


async def extract_comments(page, max_comments=500):
    logger.info(f"Extracting comments (max: {max_comments})...")
    comments = []
    
    try:
        # Scroll to load comments
        logger.info("Scrolling to load comments...")
        previous_count = 0
        no_change_count = 0
        
        for i in range(30):
            try:
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(2000)
                
                # Count loaded comments
                comment_elems = await page. locator('[data-e2e="comment-item"]').all()
                current_count = len(comment_elems) if comment_elems else 0
                
                if i % 5 == 0:
                    logger.info(f"Scroll {i+1}/30: {current_count} comments loaded")
                
                # Stop if no new comments
                if current_count == previous_count:
                    no_change_count += 1
                    if no_change_count >= 5:
                        logger.info("No new comments loading.  Stopping.")
                        break
                else:
                    no_change_count = 0
                
                previous_count = current_count
                
                if current_count >= max_comments: 
                    break
                    
            except Exception as e: 
                logger.error(f"Scroll error: {e}")
        
        # Extract comments
        comment_selectors = [
            '[data-e2e="comment-item"]',
            '. comment-item',
            '[class*="comment"]'
        ]
        
        comment_elements = None
        for selector in comment_selectors: 
            try: 
                comment_elements = await page.locator(selector).all()
                if comment_elements and len(comment_elements) > 0:
                    logger.info(f"Found {len(comment_elements)} comments")
                    break
            except: 
                continue
        
        if not comment_elements: 
            logger.warning("No comment elements found")
            return comments
        
        # Extract text from each comment
        for idx, comment_elem in enumerate(comment_elements[: max_comments]):
            try:
                text = await comment_elem.inner_text()
                comments.append(text)
            except: 
                continue
        
        logger.info(f"Extracted {len(comments)} raw comments")
        
    except Exception as e:
        logger. error(f"Comment extraction error: {e}")
    
    return comments


async def scrape_post(url, conn):
    logger.info("=" * 50)
    logger.info("Launching Playwright browser...")
    logger.info(f"Target url: {url}")

    async with async_playwright() as p:
        browser = await p. chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        # Check for saved session
        if os.path.exists(SESSION_FILE):
            logger.info("📂 Loading saved Douyin session...")
            context = await browser.new_context(
                storage_state=SESSION_FILE,
                viewport={"width": 1920, "height":  1080},
                ignore_https_errors=True
            )
        else:
            logger.info("🆕 No saved session.  May need to dismiss login popup.")
            context = await browser.new_context(
                viewport={"width": 1920, "height":  1080},
                ignore_https_errors=True
            )
        
        page = await context. new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_timeout(5000)

            # Try to dismiss login popup
            try:
                close_btn = page.locator('xpath=//div[contains(text(), "登录后免费畅享高清视频")]/following-sibling::div[1]')
                if await close_btn. count() > 0:
                    await close_btn.click()
                    logger.info("Dismissed login popup")
                    await page.wait_for_timeout(2000)
            except:
                pass
            
            # Save session for future use
            if not os.path. exists(SESSION_FILE):
                try:
                    await context.storage_state(path=SESSION_FILE)
                    logger.info("💾 Session saved for future use")
                except:
                    pass

            details = await extract_details_new(page)
            
            # Extract comments
            comments = await extract_comments(page, max_comments=500)
            comments = utils.extract_douyin_comments_from_text(comments)
            
            comments_json = json.dumps(comments, ensure_ascii=False) if comments else None
            
            item = [{
                'unnamed': None,
                'user_name': details['title']. strip() if details['title'] else None,
                'publication_date': details['publish_time'].strip() if details['publish_time'] else None,
                'content': details['content'].strip() if details['content'] else None,
                'shared_count': utils.chinese_unit_to_number(details['share_count']. strip()) if details['share_count'] else 0,
                'comment_count': utils. chinese_unit_to_number(details['comment_count'].strip()) if details['comment_count'] else 0,
                'like_count': utils.chinese_unit_to_number(details['like_count']. strip()) if details['like_count'] else 0,
                'link1': url,
                'link2': None,
                'content_segmented': None,
                'is_agriculture_related': None,
                'index_number': None,
                'comments':  comments_json
            }]
            
            logger.info(f"Saving:  {details['title'][: 30] if details['title'] else 'Unknown'}...")
            utils.insert_data(conn, config.table_name, item)
            logger.info("✅ Saved!")
            
        except Exception as e: 
            logger.error(f"Error scraping {url}: {e}")
        finally:
            await browser.close()
