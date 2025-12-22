import time
import os
import random
import sqlite3
import json
import psutil
import pywinauto
from pywinauto.application import Application
from pywinauto import mouse, Desktop
import pyautogui
import pyperclip
from PIL import ImageGrab
from logging_config import get_logger
import config
import utils

logger = get_logger()

def paste_text(text: str):
    pyperclip.copy(text)
    # should check os is windows or mac
    if pyautogui.platform.system() == "Windows":
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.hotkey("command", "a")
        pyautogui.hotkey("command", "v")


def close_article_tab():
    # should check os is windows or mac
    if pyautogui.platform.system() == "Windows":
        pyautogui.hotkey("ctrl", "w")
    else:
        pyautogui.hotkey("command", "w")


# def ensure_comments_raw_column(conn: sqlite3.Connection, table_name: str):
#     """
#     Ensure the table has a 'comments_raw' TEXT column. If missing, add it.
#     """
#     try:
#         cursor = conn.cursor()
#         cursor.execute(f"PRAGMA table_info({table_name});")
#         cols = [row[1] for row in cursor.fetchall()]  # name is at index 1
#         if "comments_raw" not in cols:
#             logger.info(f"Adding 'comments_raw' column to table {table_name}")
#             cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN comments_raw TEXT;")
#             conn.commit()
#     except Exception as e:
#         logger.error(f"Failed to ensure comments_raw column: {e}")


def copy_article_text_from_window() -> str:
    """
    Select all text in the active window and copy it to clipboard,
    then return the clipboard content as string.
    Uses Ctrl/Cmd + A then Ctrl/Cmd + C.
    """
    try:
        if pyautogui.platform.system() == "Windows":
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "c")
        else:
            pyautogui.hotkey("command", "a")
            time.sleep(0.1)
            pyautogui.hotkey("command", "c")
        time.sleep(0.2)  # wait for clipboard to be populated
        text = pyperclip.paste()
        return text if isinstance(text, str) else ""
    except Exception as e:
        logger.error(f"Failed to copy article text via clipboard: {e}")
        return ""


def get_post_metrics_data(url):
    try:
        main_window = None
        for _ in range(30):
            for win in Desktop(backend="uia").windows():
                title = win.window_text()
                if (
                    "微信" in title or "WeChat" in title or "Weixin" in title
                ) and win.is_visible():
                    rect = win.rectangle()
                    if rect.width() > 500 and rect.height() > 400:
                        main_window = win
                        break
            if main_window:
                break
        if not main_window:
            raise Exception("❌ Can't find the Wechat window, please check it.")
        main_window.restore()
        main_window.maximize()
        main_window.set_focus()
        time.sleep(2)

        rect = main_window.rectangle()
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        width = right - left
        height = bottom - top
        logger.info(f"Read Wechat window size: {width} {height}")
        # search_icon_x, search_icon_y = utils.find_search_icon_coordination(
        #     left, top, right, bottom)
        search_area_x = left + int(width / 2)
        search_area_y = top + 110
        pyautogui.click(search_area_x, search_area_y)
        paste_text(url)
        time.sleep(random.uniform(0.5, 1.5))
        pyautogui.press("enter")
        time.sleep(random.uniform(0.5, 1.5))
        link_x = search_area_x
        link_y = search_area_y + 120
        pyautogui.click(link_x, link_y)
        time.sleep(random.uniform(2, 3))

        # Using local OCR to read data from image (metrics)
        like_count, shared_count, favorite_count, comment_count = (
            utils.ocr_wechat_article_metrics(left, bottom - 200, right, bottom)
        )

        # Copy all article text via select-all + copy and return raw text
        comments_raw = copy_article_text_from_window()
        comments = utils.extract_wechat_comments_from_text(comments_raw)
        comments = json.dumps(comments, ensure_ascii=False) if comments else None
        # Close Article Tab
        close_article_tab()

        return main_window, like_count, shared_count, favorite_count, comment_count, comments

    except Exception as e:
        logger.error(f"Error during WeChat article ocr process: {e}")
        return None, None, None, None, None, ""


if __name__ == "__main__":
    conn = sqlite3.connect(config.db_name)
    logger.info(f"connect to database successful: {config.db_name}")
    utils.create_table(conn, config.table_name)

    # Ensure the table has comments_raw column
    # _ensure_comments_raw_column(conn, config.table_name)

    with open("urls.txt", "r", encoding="utf-8") as f:
        # read urls from urls.txt that to be scraped
        urls = [line.strip() for line in f if line.strip()]

    for i, url in enumerate(urls):
        logger.info("Prepare to scrape url: " + url)
        if "mp.weixin.qq.com" in url:
            (
                main_window,
                like_count,
                shared_count,
                favorite_count,
                comment_count,
                comments,
            ) = get_post_metrics_data(url)

            if main_window is None:
                logger.error(f"Failed to get data for {url}, skipping.")
                continue

            item = [
                {
                    "unnamed": None,
                    "user_name": None,
                    "publication_date": None,
                    "content": None,
                    "shared_count": shared_count,
                    "comment_count": comment_count,
                    "like_count": like_count,
                    "link1": url,
                    "link2": None,
                    "content_segmented": None,
                    "is_agriculture_related": None,
                    "index_number": None,
                    "comments": comments,  # new field with copied article text
                }
            ]
            logger.info(
                f"💾 Inserting Wechat post metrics data into the database...: {item}"
            )
            utils.insert_data(conn, config.table_name, item, is_update_metrics=True)

        if i + 1 == len(urls) and main_window:
            main_window.minimize()
            logger.info(f"Complete get wechat posts metrics.")