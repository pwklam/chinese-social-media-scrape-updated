import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
import json
import utils
import config
from logging_config import get_logger

logger = get_logger()

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
        # details["title"] = await page.locator(
        #     'xpath=//div[@data-e2e="user-info"]/following-sibling::div[1]/a[contains(@href, "www.douyin.com/user/")]/div'
        # ).inner_text()
        title = await page.locator(
            'xpath=(//div[@data-e2e="user-info"]/div[2]/a/div)[2]'
        ).inner_text()
        details["title"] = title.split("\n")[0]
        print(f"scrape title: {details['title']}")
    except Exception as e:
        print(f"scrape title error: {e}")
        pass

    try:
        details["content"] = await page.locator('xpath=//div[@data-e2e="detail-video-info"]/div[1]/div/h1').inner_text()
        print(f"scrape content: {details['content']}")
    except Exception as e:
        print(f"scrape content error: {e}")
        pass

    try:
        details["like_count"] = await page.locator('xpath=//div[@data-e2e="detail-video-info"]/div[2]/div[1]/div[1]/span').inner_text()
        print(f"scrape like_count: {details['like_count']}")
    except Exception as e:
        print(f"scrape like_count error: {e}")
        pass

    try:
        details["comment_count"] = await page.locator('xpath=//div[@data-e2e="detail-video-info"]/div[2]/div/div[2]/span').inner_text()
        print(f"scrape comment_count: {details['comment_count']}")
    except Exception as e:
        print(f"scrape comment_count error: {e}")
        pass

    try:
        details["share_count"] = await page.locator('xpath=//div[@data-e2e="detail-video-info"]/div[2]/div/div[4]/span').inner_text()
        print(f"scrpae share_count: {details['share_count']}")
    except Exception as e:
        print(f"scrape share_count error: {e}")
        pass

    try:
        publish_time = await page.locator('span[data-e2e="detail-video-publish-time"]').inner_text()
        publish_time  = publish_time.replace('发布时间：', '').strip()
        dt_object = datetime.strptime(publish_time.strip(), '%Y-%m-%d %H:%M')
        # Format to YYYY-MM-DD HH:MM:SS (adding ':00' for seconds)
        details["publish_time"] = dt_object.strftime('%Y-%m-%d %H:%M:%S')
        print(f"scrape publish_time: {details['publish_time']}")
    except Exception as e:
        print(f"scrape publish_time error: {e}")
        pass

    return details

async def extract_comments(page, max_comments=20):
    """
    Extracts comments from a Douyin post page.
    
    Args:
        page: Playwright page object
        max_comments: Maximum number of comments to extract (default: 20)
    
    Returns:
        List of dictionaries containing comment data
    """
    comments = []
    
    try:
        logger.info(f"[LOAD] Starting comment extraction (max: {max_comments})...")
        
        # Scroll to load more comments
        logger.info("[SCROLL] Scrolling to load comments...")
        for i in range(3):
            try:
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(2000)
                logger.info(f"Scroll {i+1}/3 completed")
            except Exception as e:
                logger.error(f"Scroll error: {e}")
        
        # Try to locate comment elements using different selectors
        comment_selectors = [
            '[data-e2e="comment-item"]',
            '.comment-item',
            '[class*="comment"]'
        ]
        
        comment_elements = None
        for selector in comment_selectors:
            try:
                comment_elements = await page.locator(selector).all()
                if comment_elements and len(comment_elements) > 0:
                    logger.info(f"[OK] Found {len(comment_elements)} comments using selector: {selector}")
                    break
            except Exception as e:
                logger.info(f"Selector {selector} failed: {e}")
                continue
        
        if not comment_elements or len(comment_elements) == 0:
            logger.warning("[WARN] No comment elements found on page")
            return comments
        
        # Extract data from each comment (limit to max_comments)
        for idx, comment_elem in enumerate(comment_elements[:max_comments]):
            try:
                # comment_data = {
                #     'username': None,
                #     'content': None,
                #     'time': None,
                #     'likes': '0'
                # }
                
                text = await comment_elem.inner_text()
                comments.append(text)
                '''
                # Try to extract username
                username_selectors = [
                    '[data-e2e="comment-author-name"]',
                    '.user-name',
                    '[class*="author"]',
                    '[class*="username"]'
                ]
                for selector in username_selectors:
                    try:
                        username_elem = comment_elem.locator(selector).first
                        if await username_elem.count() > 0:
                            comment_data['username'] = await username_elem.inner_text()
                            break
                    except:
                        continue
                
                # Try to extract comment content
                content_selectors = [
                    '[data-e2e="comment-content"]',
                    '.comment-text',
                    '[class*="comment-content"]',
                    '[class*="text"]'
                ]
                for selector in content_selectors:
                    try:
                        content_elem = comment_elem.locator(selector).first
                        if await content_elem.count() > 0:
                            comment_data['content'] = await content_elem.inner_text()
                            break
                    except:
                        continue
                
                # Try to extract comment time
                time_selectors = [
                    '[data-e2e="comment-time"]',
                    '.comment-time',
                    '[class*="time"]',
                    '[class*="date"]'
                ]
                for selector in time_selectors:
                    try:
                        time_elem = comment_elem.locator(selector).first
                        if await time_elem.count() > 0:
                            comment_data['time'] = await time_elem.inner_text()
                            break
                    except:
                        continue
                
                # Try to extract like count
                like_selectors = [
                    '[data-e2e="comment-like-count"]',
                    '.like-count',
                    '[class*="like"]'
                ]
                for selector in like_selectors:
                    try:
                        like_elem = comment_elem.locator(selector).first
                        if await like_elem.count() > 0:
                            comment_data['likes'] = await like_elem.inner_text()
                            break
                    except:
                        continue

                # Only add comment if at least content or username was extracted
                if comment_data['content'] or comment_data['username']:
                    comments.append(comment_data)
                    logger.info(f"[OK] Extracted comment {idx+1}: {comment_data['username'][:20] if comment_data['username'] else 'Unknown'}")
                '''
                
            except Exception as e:
                logger.error(f"Error extracting comment {idx+1}: {e}")
                continue
        
        logger.info(f"[OK] Successfully extracted {len(comments)} comments")
        
    except Exception as e:
        logger.error(f"[ERROR] Error during comment extraction: {e}")
    
    return comments

async def scrape_post(url, conn):
    """
    Scrapes the title, publish date, content, and interaction counts 
    (Share, Comment, Like) for a specific Douyin post using Playwright.
    """
    logger.info("[START] Launching Playwright browser...")
    logger.info(f"Target url: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--start-maximized'])
        # Create a new page context to maintain login state (e.g., cookies)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()
        await page.goto(url)
        await page.wait_for_timeout(5000)

        await page.locator('xpath=//div[contains(text(), "登录后免费畅享高清视频")]/following-sibling::div[1]').click()

        details = await extract_details_new(page)
        
        # Extract comments
        comments = await extract_comments(page, max_comments=20)
        comments = utils.extract_douyin_comments_from_text(comments)
        
        # Serialize comments to JSON string for database storage (only if comments exist)
        comments_json = json.dumps(comments, ensure_ascii=False) if comments else None
        
        item = [{
            'unnamed': None,
            'user_name': details['title'].strip() if details['title'] else None,
            'publication_date': details['publish_time'].strip() if details['publish_time'] else None,
            'content': details['content'].strip() if details['content'] else None,
            'shared_count': utils.chinese_unit_to_number(details['share_count'].strip()) if details['share_count'] else 0,
            'comment_count': utils.chinese_unit_to_number(details['comment_count'].strip()) if details['comment_count'] else 0,
            'like_count': utils.chinese_unit_to_number(details['like_count'].strip()) if details['like_count'] else 0,
            'link1': url,
            'link2': None,
            'content_segmented': None,
            'is_agriculture_related': None,
            'index_number': None,
            'comments': comments_json
        }]
        logger.info(f"[SAVE] Inserting scraped data into the database...: {item}")

        utils.insert_data(conn, config.table_name, item)