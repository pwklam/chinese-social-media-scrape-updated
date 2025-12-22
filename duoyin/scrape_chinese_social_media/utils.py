import os
import sqlite3
import re
import cv2
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import pytesseract
from PIL import ImageGrab
from logging_config import get_logger
from dashscope import MultiModalConversation
import dashscope
import config

logger = get_logger()

script_dir = os.path.dirname(os.path.abspath(__file__))
# Setting Tesseract path（Windows）
pytesseract.pytesseract.tesseract_cmd = config.tesseract_cmd
like_icon_path = os.path.join(script_dir, "ocr_icon", "like_icon.png")
share_icon_path = os.path.join(script_dir, "ocr_icon", "share_icon.png")
favorite_icon_path = os.path.join(script_dir, "ocr_icon", "favorite_icon.png")
comment_icon_path = os.path.join(script_dir, "ocr_icon", "comment_icon.png")
search_icon_path = os.path.join(script_dir, "ocr_icon", "search_icon.png")

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

def output_zero_if_no_digit(s):
    if not any(char.isdigit() for char in s):
        return 0
    return s

def ocr_image_recognition_ai(image_path):
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    messages = [
        {
            "role": "user",
            "content": [
                {"image": image_path},
                {
                    "text": "请识别图片中从左到右固定的点赞、转发、喜欢和评论四个图标及其相邻的数字，结果输出只需要数字，去掉其他字符。例如“赞 1234”，“评论 56”只需要返回“1234”和“56”，特别要注意如果其中某一个图标不显示，则输出对应位置的数字为 0。"
                },
            ],
        }
    ]

    response = MultiModalConversation.call(model="qwen-vl-plus", messages=messages)

    if response.status_code == 200:
        content = response.output.choices[0].message.content
        logger.info(f"OCR Recognition Result: {content}")
        return content
    else:
        logger.info(f"OCR request failed: {response}")
        return None


def find_icon_and_read_number(template_path, screenshot, icon_width=30, icon_height=30):
    """
    Find the icon position in the screenshot based on the template, and read the number to its right
    :param template_path: Icon template path
    :param screenshot: Icon screenshot image (numpy array)
    :param icon_width, icon_height: Icon size (for cropping number area)
    :return: Number value
    """
    try:
        # Read template
        template = cv2.imread(template_path, 0)  # Grayscale
        if template is None:
            logger.info(f"❌ Template image {template_path} not found")
            return 0

        # Template matching
        res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        # if max_val < 0.7:  # Matching score below 70% is considered not found
        #     logger.info(f"⚠️ Not found {template_path}")
        #     return 0

        # Get top-left coordinates of the icon
        top_left = max_loc
        h, w = template.shape[:2]

        # Crop the number area to the right of the icon
        # (assuming the number starts 5px to the right of the icon, width 60px, height same as icon)
        number_region = screenshot[
            top_left[1] : top_left[1] + h,
            # top_left[0] + w + 5:top_left[0] + w + 60
            top_left[0] + w - 3 : top_left[0] + w + 59,
        ]

        # Image preprocessing (improve OCR accuracy)
        _, thresh = cv2.threshold(number_region, 150, 255, cv2.THRESH_BINARY_INV)

        # OCR recognize numbers
        text = pytesseract.image_to_string(
            # thresh, config="--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789 "
            thresh, config="--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789 "
        )
        # text = pytesseract.image_to_string(thresh, config='--psm 9 -c tessedit_char_whitelist=0123456789 ')
        numbers = [int(n) for n in text.split() if n.isdigit()]

        if numbers:
            logger.info(f"OCR numbers success: {numbers}")
            return numbers[0]
        else:
            logger.info("❌ No numbers recognized")
            return 0
    except Exception as e:
       logger.info(f"OCR error: {e}")


def ocr_wechat_article_metrics(left, top, right, bottom):
    """OCR WeChat article metrics: likes, shares, favorites, comments"""
    # Screenshot the entire WeChat article window (adjust according to your coordinates)
    # L, T, R, B = config.wechat_article_area_coords  # The coordinates of article area
    L, T, R, B = left, top, right, bottom  # The coordinates of article area
    screenshot = np.array(ImageGrab.grab(bbox=(L, T, R, B)))
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # Recognize the four metrics respectively
    likes = find_icon_and_read_number(like_icon_path, screenshot_gray)
    shares = find_icon_and_read_number(share_icon_path, screenshot_gray)
    favorites = find_icon_and_read_number(favorite_icon_path, screenshot_gray)
    comments = find_icon_and_read_number(comment_icon_path, screenshot_gray)

    return likes, shares, favorites, comments

def find_search_icon_coordination(left, top, right, bottom):
    template_path = search_icon_path
    L, T, R, B = left, top, right, bottom  # The coordinates of article area
    screenshot = np.array(ImageGrab.grab(bbox=(L, T, R, B)))
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(template_path, 0)  # Grayscale
    if template is None:
        logger.info(f"❌ Template image {template_path} not found")
        return 0

    # Template matching
    res = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    # Get top-left coordinates of the icon
    top_left = max_loc
    h, w = template.shape[:2]
    return top_left[1]+2, top_left[0]+2

def _parse_relative_date(time_str: str, now: datetime | None = None) -> str:
    """Convert relative time strings like '2天前', '昨天', '4小时前', '41分钟前' to 'YYYY-MM-DD'."""
    now = now or datetime.now()
    s = time_str.strip()
    if not s:
        return now.date().isoformat()
    m = re.search(r'(\d+)\s*天前', s)
    if m:
        return (now - timedelta(days=int(m.group(1)))).date().isoformat()
    if '昨天' in s:
        return (now - timedelta(days=1)).date().isoformat()
    m = re.search(r'(\d+)\s*小时', s) or re.search(r'(\d+)\s*小时前', s)
    if m:
        # keep same day unless crosses midnight; produce date only
        return (now - timedelta(hours=int(m.group(1)))).date().isoformat()
    m = re.search(r'(\d+)\s*分', s) or re.search(r'(\d+)\s*分钟前', s)
    if m:
        return (now - timedelta(minutes=int(m.group(1)))).date().isoformat()
    if '今天' in s or '刚刚' in s:
        return now.date().isoformat()
    # try parse explicit date formats (YYYY-MM-DD, YYYY/MM/DD, etc.)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    # fallback: return original string (safer) or today's date
    return now.date().isoformat()

def _parse_relative_date(time_str: str, now: datetime | None = None) -> str:
    # ...existing code...
    now = now or datetime.now()
    s = time_str.strip()
    if not s:
        return now.date().isoformat()
    m = re.search(r'(\d+)\s*天前', s)
    if m:
        return (now - timedelta(days=int(m.group(1)))).date().isoformat()
    if '昨天' in s:
        return (now - timedelta(days=1)).date().isoformat()
    m = re.search(r'(\d+)\s*小时', s) or re.search(r'(\d+)\s*小时前', s)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).date().isoformat()
    m = re.search(r'(\d+)\s*分', s) or re.search(r'(\d+)\s*分钟前', s)
    if m:
        return (now - timedelta(minutes=int(m.group(1)))).date().isoformat()
    if '今天' in s or '刚刚' in s:
        return now.date().isoformat()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return now.date().isoformat()

def extract_wechat_comments_from_text(text: str) -> List[Dict]:
    """
    Extract comment blocks from Weixin article text (text extracted from UI).
    Handles patterns like:
      username
      location (optional)
      time (e.g. '2天前' / '昨天' / '41分钟前' / explicit date)
      optional likes (a number on the next line)
      content (one or more lines)
    Returns list of dicts:
      {'username': ..., 'content': ..., 'time': 'YYYY-MM-DD', 'likes': '10'}
    """
    if not text:
        return []

    lines = [ln.strip() for ln in text.splitlines()]
    # find start of comments section
    start_idx = 0
    for i, ln in enumerate(lines):
        if re.match(r'^\s*\d+\s*comment', ln, re.I) or ln.strip().lower() == "comment" or ln.strip().lower() == "comments":
            start_idx = i + 1
            break

    sub = [ln for ln in lines[start_idx:] if ln != ""]  # drop empty lines to simplify indexing
    if not sub:
        return []

    # helper regex to detect time-like lines
    time_re = re.compile(r'^(?:\d+\s*天前|\d+\s*小时前|\d+\s*小时|\d+\s*分钟前|昨天|今天|刚刚|\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})$')
    # find indices of lines that match time pattern
    time_indices = [i for i, ln in enumerate(sub) if time_re.match(ln)]

    comments = []
    if not time_indices:
        return comments

    for idx_pos, t_idx in enumerate(time_indices):
        # determine username: usually two lines above time (username, location, time)
        username = "Unknown"
        possible_username_idx = t_idx - 2
        if possible_username_idx >= 0:
            username = sub[possible_username_idx]
        else:
            # fallback: previous non-time non-numeric line
            j = t_idx - 1
            while j >= 0 and (time_re.match(sub[j]) or re.match(r'^\d+$', sub[j])):
                j -= 1
            if j >= 0:
                username = sub[j]

        # determine if likes present: next line after time that is purely digits
        likes = "0"
        next_idx = t_idx + 1
        if next_idx < len(sub) and re.match(r'^\d+$', sub[next_idx]):
            likes = sub[next_idx]
            content_start = t_idx + 2
        else:
            # no likes line, content starts immediately after time
            content_start = t_idx + 1

        # content end: before next comment's username (which is next_time_idx - 2) or EOF
        if idx_pos + 1 < len(time_indices):
            next_t_idx = time_indices[idx_pos + 1]
            content_end = max(content_start, next_t_idx - 2)
        else:
            content_end = len(sub)

        # filter out reply-count lines like '20条回复'
        content_lines = []
        for ln in sub[content_start:content_end]:
            if re.search(r'\d+条回复', ln):
                continue
            # skip lines that look like simple location strings (e.g., just a province) if they duplicate earlier location
            content_lines.append(ln)
        content = "\n".join(content_lines).strip()

        time_line = sub[t_idx] if t_idx < len(sub) else ""
        parsed_date = _parse_relative_date(time_line)

        comment_data = {
            "username": username,
            "content": content,
            "time": parsed_date,
            "likes": likes
        }
        comments.append(comment_data)

    return comments


def extract_weibo_comments_from_text(text: str) -> List[Dict[str, str]]:
    """
    Read text and extract comments into list of dicts:
    {
      'username': "用户A",
      'content': "test",
      'time': "YYYY-MM-DD 00:00:00",
      'likes': '10'
    }
    """
    comments: List[Dict[str, str]] = []

    if not text:
        return comments
    
    line_re = re.compile(
        r"""^['"]?                       # optional leading quote
             (?P<username>[^:：]+?)      # username (up to colon)
             [:：]\s*                    # colon separator
             (?P<content>.*?)\s+        # content (lazy) then whitespace before date
             (?P<date>\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,2})  # date (yy-mm-dd or yyyy-mm-dd)
             (?:\s+(?P<time>\d{1,2}:\d{2}))?              # optional hh:mm
             (?:\s+(?P<likes>\d+))?      # optional likes number
             ['"]?\s*$                   # optional trailing quote and end
        """,
        re.VERBOSE,
    )

    try:
        for raw in text.splitlines():
            s = raw.strip()
            if not s:
                continue
            m = line_re.match(s)
            if not m:
                # try a simpler fallback: split by last two tokens (date time)
                parts = s.strip("'\" ").rsplit(maxsplit=3)
                if len(parts) >= 3 and re.match(r'\d{1,2}:\d{2}', parts[-2]) or re.match(r'\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,2}', parts[-2]):
                    # best-effort parse
                    username, rest = (parts[0].split(":", 1) + [""])[:2]
                    content = rest.strip() if rest else ""
                    date_token = parts[-3] if len(parts) >= 3 else parts[-2]
                    likes = parts[-1] if parts[-1].isdigit() else "0"
                    date_str = date_token
                    # normalize date
                    try:
                        dt = datetime.strptime(date_str, "%y-%m-%d")
                    except Exception:
                        try:
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                        except Exception:
                            dt = datetime.now()
                    time_str = dt.strftime("%Y-%m-%d") + " 00:00:00"
                    comments.append({
                        "username": username.strip(),
                        "content": content.strip(),
                        "time": time_str,
                        "likes": likes if likes.isdigit() else "0",
                    })
                continue

            username = m.group("username").strip()
            content = m.group("content").strip()
            date_part = m.group("date").strip()
            # prefer to ignore captured time and use midnight as requested
            # Normalize date: handle two-digit year => 2000s
            dt = None
            for fmt in ("%y-%m-%d", "%Y-%m-%d", "%y/%m/%d", "%Y/%m/%d", "%y.%m.%d", "%Y.%m.%d"):
                try:
                    dt = datetime.strptime(date_part, fmt)
                    break
                except Exception:
                    continue
            if dt is None:
                # fallback: try to extract numbers and build date
                digits = re.findall(r"\d+", date_part)
                try:
                    if len(digits) >= 3:
                        y = int(digits[0])
                        mth = int(digits[1])
                        d = int(digits[2])
                        if y < 100:
                            y += 2000
                        dt = datetime(year=y, month=mth, day=d)
                    else:
                        dt = datetime.now()
                except Exception:
                    dt = datetime.now()

            time_str = dt.strftime("%Y-%m-%d") + " 00:00:00"
            likes = m.group("likes") or "0"

            comments.append(
                {
                    "username": username,
                    "content": content,
                    "time": time_str,
                    "likes": likes,
                }
            )
    except Exception as e:
        logger.info(f"❌ An error occurred while extract comments: {e}")

    return comments


def extract_douyin_comments_from_text(text: str) -> List[Dict[str, str]]:
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
    comments: List[Dict[str, str]] = []
    
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

def chrome_cookies_to_playwright(chrome_cookies):
    pw_cookies = []

    for c in chrome_cookies:
        cookie = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
        }

        if "expirationDate" in c:
            cookie["expires"] = c["expirationDate"]

        if "secure" in c:
            cookie["secure"] = c["secure"]

        if "httpOnly" in c:
            cookie["httpOnly"] = c["httpOnly"]

        if "sameSite" in c:
            # Chrome: Lax / Strict / None
            cookie["sameSite"] = c["sameSite"].lower()

        pw_cookies.append(cookie)

    return pw_cookies

def cookie_str_to_playwright(cookie_str: str, domain: str):
    cookies = []

    for item in cookie_str.split(";"):
        item = item.strip()
        if not item:
            continue

        if "=" not in item:
            continue

        name, value = item.split("=", 1)

        cookies.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": "/",
        })

    return cookies
