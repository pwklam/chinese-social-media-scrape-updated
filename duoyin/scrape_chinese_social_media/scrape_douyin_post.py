import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import json
import os
import sqlite3
import pandas as pd
import re
import config
from logging_config import get_logger

logger = get_logger()

# Path to save login session
SESSION_FILE = "douyin_session.json"

# Inlined functions from utils.py

def create_table(conn, table_name):
    """
    create table for scraped data
    """
    cursor = conn.cursor()
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unnamed TEXT,
            user_name TEXT,
            publication_date TEXT,
            content TEXT,
            shared_count TEXT,
            comment_count TEXT, 
            like_count TEXT,
            link1 TEXT UNIQUE,
            link2 TEXT,
            content_segmented TEXT,
            is_agriculture_related TEXT,
            index_number TEXT,
            comments TEXT
        )
    """
    )
    conn.commit()

def insert_data(conn, table_name, data, is_update_metrics=False):
    """
    insert DataFrame data into database
    """
    if not data:
        logger.info(f"Scraped data is empty")
        return
    df = pd.DataFrame(data)
    
    # Check if comments column exists in the dataframe
    columns = [
        "unnamed",
        "user_name",
        "publication_date",
        "content",
        "shared_count",
        "comment_count",
        "like_count",
        "link1",
        "link2",
        "content_segmented",
        "is_agriculture_related",
        "index_number",
    ]
    
    if "comments" in df.columns:
        columns.append("comments")
        
    data_to_insert = df[columns].values.tolist()

    if is_update_metrics:
        if "comments" in df.columns:
            sql = f"""
                    INSERT OR REPLACE INTO {table_name} (
                        'unnamed', 'user_name', 'publication_date', 
                        'content', 'shared_count', 'comment_count', 
                        'like_count', 'link1', 'link2', 
                        'content_segmented', 'is_agriculture_related', 'index_number', 'comments'
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(link1) DO UPDATE SET
                        shared_count = excluded.shared_count,
                        comment_count = excluded.comment_count,
                        like_count = excluded.like_count,
                        comments = excluded.comments"""
        else:
            sql = f"""
                    INSERT OR REPLACE INTO {table_name} (
                        'unnamed', 'user_name', 'publication_date', 
                        'content', 'shared_count', 'comment_count', 
                        'like_count', 'link1', 'link2', 
                        'content_segmented', 'is_agriculture_related', 'index_number'
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(link1) DO UPDATE SET
                        shared_count = excluded.shared_count,
                        comment_count = excluded.comment_count,
                        like_count = excluded.like_count"""
    else:
        if "comments" in df.columns:
            sql = f"""
                    INSERT INTO {table_name} (
                        'unnamed', 'user_name', 'publication_date', 
                        'content', 'shared_count', 'comment_count', 
                        'like_count', 'link1', 'link2', 
                        'content_segmented', 'is_agriculture_related', 'index_number', 'comments'
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(link1) DO UPDATE SET
                        shared_count = excluded.shared_count,
                        comment_count = excluded.comment_count,
                        like_count = excluded.like_count,
                        comments = excluded.comments"""
        else:
            sql = f"""
                    INSERT INTO {table_name} (
                        'unnamed', 'user_name', 'publication_date', 
                        'content', 'shared_count', 'comment_count', 
                        'like_count', 'link1', 'link2', 
                        'content_segmented', 'is_agriculture_related', 'index_number'
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(link1) DO UPDATE SET
                        shared_count = excluded.shared_count,
                        comment_count = excluded.comment_count,
                        like_count = excluded.like_count"""

    cursor = conn.cursor()
    for row in data_to_insert:
        try:
            cursor.execute(sql, row)
        except sqlite3.Error as e:
            logger.info(f"insert scraped data error: {e}")
    conn.commit()

def chinese_unit_to_number(text: str) -> float:
    if not text:
        return 0
    text = text.strip()
    unit_map = {
        "千": 1_000,
        "K": 1_000,
        "k": 1_000,
        "万": 10_000,
        "亿": 100_000_000,
        "百万": 1_000_000,
        "千万": 10_000_000,
        "十亿": 1_000_000_000,
        "b": 1_000_000_000,
        "B": 1_000_000_000,  # billion
        "m": 1_000_000,
        "M": 1_000_000,  # million
    }
    match = re.fullmatch(r"([+-]?\d*\.?\d+)(.*)", text)
    if not match:
        raise ValueError(f"Can't extract Chinese unit: {text}")

    num_str, unit_str = match.groups()
    num = float(num_str)

    if not unit_str:
        return num

    unit_clean = unit_str.strip().lower()

    if unit_str in unit_map:
        return num * unit_map[unit_str]

    for unit in ["亿", "万", "千", "百万", "千万", "十亿"]:
        if unit in unit_str:
            return num * unit_map[unit]

    if "m" in unit_clean:
        return num * unit_map["M"]
    if "k" in unit_clean:
        return num * unit_map["K"]
    if "b" in unit_clean:
        return num * unit_map["B"]

    raise ValueError(f"Unsupport Chinese unit: {unit_str}")

def _parse_relative_time(time_str: str) -> str:
    """
    Convert relative time strings like '2年前·天津', '1月前', '3天前', '2周前' to 'YYYY-MM-DD 00:00:00'
    """
    now = datetime.now()
    s = time_str.strip()

    # Extract location if present (after ·)
    s = s.split("·")[0].strip()

    # Match year pattern
    m = re.search(r'(\d+)\s*年前', s)
    if m:
        years = int(m.group(1))
        dt = now - timedelta(days=years * 365)
        return dt.strftime("%Y-%m-%d 00:00:00")

    # Match month pattern
    m = re.search(r'(\d+)\s*月前', s)
    if m:
        months = int(m.group(1))
        dt = now - timedelta(days=months * 30)
        return dt.strftime("%Y-%m-%d 00:00:00")

    # Match week pattern (new): '2周前' or '2星期前'
    m = re.search(r'(\d+)\s*(?:周|星期)前', s)
    if m:
        weeks = int(m.group(1))
        dt = now - timedelta(weeks=weeks)
        return dt.strftime("%Y-%m-%d 00:00:00")

    # Match day pattern
    m = re.search(r'(\d+)\s*天前', s)
    if m:
        days = int(m.group(1))
        dt = now - timedelta(days=days)
        return dt.strftime("%Y-%m-%d 00:00:00")

    # Match hour pattern
    m = re.search(r'(\d+)\s*小时前', s)
    if m:
        hours = int(m.group(1))
        dt = now - timedelta(hours=hours)
        return dt.strftime("%Y-%m-%d 00:00:00")

    # Match minute pattern
    m = re.search(r'(\d+)\s*分钟前', s)
    if m:
        minutes = int(m.group(1))
        dt = now - timedelta(minutes=minutes)
        return dt.strftime("%Y-%m-%d 00:00:00")

    # Default to today
    return now.strftime("%Y-%m-%d 00:00:00")

def extract_douyin_comments_from_text(text: str) -> list:
    """
    Extract comments from text string with format:
    'username\n...\ncontent\nrelative_time·location\n\nlikes\n\n分享\n回复'
    
    Returns list of dicts:
    {
      'username': "魏哥",
      'content': "为您加油",
      'time': "2024-11-27 00:00:00",
      'likes': '12'
    }
    """
    comments = []
    
    # Handle input as list or string
    if isinstance(text, list):
        entries = text
    else:
        # If it's a string, split by newline and filter
        entries = [line.strip() for line in text.split('\n') if line.strip()]
    
    for entry in entries:
        entry = str(entry).strip()
        if not entry or entry == "'":
            continue
        
        # Remove surrounding quotes
        entry = entry.strip("'\"")
        
        # Split by actual \n (newline character in the string)
        lines = entry.split("\n")
        lines = [ln.strip() for ln in lines if ln.strip() and ln.strip() not in ("...", "分享", "回复", "展开1条回复")]
        
        if len(lines) < 2:
            continue
        
        try:
            # Extract username (first line, or second if first is "...")
            username = lines[0]
            if username == "...":
                username = "Unknown"
            
            # Extract content (usually after "..." marker)
            content = ""
            content_idx = 1
            # Skip "..." if present
            if lines[content_idx] == "...":
                content_idx = 2
            
            if content_idx < len(lines):
                content = lines[content_idx]
            
            # Find time and likes info
            time_str = datetime.now().strftime("%Y-%m-%d 00:00:00")
            likes = "0"
            
            # Look for time pattern (e.g., "2年前·天津")
            for ln in lines:
                if "年前" in ln or "月前" in ln or "天前" in ln or "小时前" in ln or "分钟前" in ln or "周前" in ln:
                    time_str = _parse_relative_time(ln)
                    break
            
            # Look for numeric likes (should be a standalone digit line)
            for ln in lines:
                if ln.isdigit():
                    likes = ln
                    break

            if "年前" in content or "月前" in content or "天前" in content or "小时前" in content or "分钟前" in content or "周前" in content:
                content = ""
            
            comments.append({
                "username": username,
                "content": content,
                "time": time_str,
                "likes": likes
            })
        except Exception as e:
            print(f"Error parsing entry: {e}")
            continue
    
    return comments

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
        details["title"] = title.split("\n")[0]
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
        dt_object = datetime.strptime(publish_time.strip(), '%Y-%m-%d %H:%M')
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
                comment_elems = await page.locator('[data-e2e="comment-item"]').all()
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
        logger.error(f"Comment extraction error: {e}")
    
    return comments


async def scrape_post(url, conn):
    logger.info("=" * 50)
    logger.info("Launching Playwright browser...")
    logger.info(f"Target url: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Changed to True for Colab
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
        
        page = await context.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_timeout(5000)

            # Try to dismiss login popup
            try:
                close_btn = page.locator('xpath=//div[contains(text(), "登录后免费畅享高清视频")]/following-sibling::div[1]')
                if await close_btn.count() > 0:
                    await close_btn.click()
                    logger.info("Dismissed login popup")
                    await page.wait_for_timeout(2000)
            except:
                pass
            
            # Save session for future use
            if not os.path.exists(SESSION_FILE):
                try:
                    await context.storage_state(path=SESSION_FILE)
                    logger.info("💾 Session saved for future use")
                except:
                    pass

            details = await extract_details_new(page)
            
            # Extract comments
            comments = await extract_comments(page, max_comments=500)
            comments = extract_douyin_comments_from_text(comments)
            
            comments_json = json.dumps(comments, ensure_ascii=False) if comments else None
            
            item = [{
                'unnamed': None,
                'user_name': details['title'].strip() if details['title'] else None,
                'publication_date': details['publish_time'].strip() if details['publish_time'] else None,
                'content': details['content'].strip() if details['content'] else None,
                'shared_count': chinese_unit_to_number(details['share_count'].strip()) if details['share_count'] else 0,
                'comment_count': chinese_unit_to_number(details['comment_count'].strip()) if details['comment_count'] else 0,
                'like_count': chinese_unit_to_number(details['like_count'].strip()) if details['like_count'] else 0,
                'link1': url,
                'link2': None,
                'content_segmented': None,
                'is_agriculture_related': None,
                'index_number': None,
                'comments':  comments_json
            }]
            
            logger.info(f"Saving:  {details['title'][: 30] if details['title'] else 'Unknown'}...")
            create_table(conn, config.table_name)
            insert_data(conn, config.table_name, item)
            logger.info("✅ Saved!")
            
        except Exception as e: 
            logger.error(f"Error scraping {url}: {e}")
        finally:
            await browser.close()
