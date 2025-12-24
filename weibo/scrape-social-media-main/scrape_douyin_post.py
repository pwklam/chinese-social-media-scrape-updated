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

async def extract_comments(page, max_comments=500):
    logger.info(f"Extracting comments (max: {max_comments})...")
    comments = []
    
    try:
        # Scroll to load comments and click load more if available
        logger.info("Scrolling to load comments...")
        previous_count = 0
        no_change_count = 0
        
        for i in range(50):  # Increased to 50 for more attempts
            try:
                # Scroll down
                await page.evaluate("window.scrollBy(0, 1000)")  # Increased scroll distance
                await page.wait_for_timeout(3000)  # Increased wait time
                
                # Try to click "load more" button (Douyin uses "查看更多评论" or similar)
                try:
                    load_more_selectors = [
                        'text=查看更多评论',
                        'text=展开更多',
                        '[data-e2e="comment-load-more"]',  # If it has a data-e2e
                        'button:has-text("更多")'
                    ]
                    for selector in load_more_selectors:
                        load_more = page.locator(selector)
                        if await load_more.count() > 0 and await load_more.is_visible():
                            await load_more.click()
                            logger.info(f"Clicked load more button at scroll {i+1}")
                            await page.wait_for_timeout(3000)
                            break
                except Exception as e:
                    logger.debug(f"Load more click failed: {e}")
                
                # Count loaded comments
                comment_elems = await page.locator('[data-e2e="comment-item"]').all()
                current_count = len(comment_elems) if comment_elems else 0
                
                if i % 5 == 0:
                    logger.info(f"Scroll {i+1}/50: {current_count} comments loaded")
                
                # Stop if no new comments
                if current_count == previous_count:
                    no_change_count += 1
                    if no_change_count >= 10:  # Increased patience
                        logger.info("No new comments loading. Stopping.")
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
            '.comment-item',
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
        logger.error(f"Comment extraction error: {e}")
    
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
