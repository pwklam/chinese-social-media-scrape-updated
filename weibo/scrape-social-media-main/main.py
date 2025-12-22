import asyncio
import sqlite3
import utils
import config
import scrape_weibo_post
import scrape_weixin_post
import scrape_douyin_post
from logging_config import get_logger

logger = get_logger()

if __name__ == '__main__':
    conn = sqlite3.connect(config.db_name)
    logger.info(f"connect to database successful: {config.db_name}")
    utils.create_table(conn, config.table_name)

    with open('urls.txt', 'r', encoding='utf-8') as f:
        # read urls from urls.txt that to be scraped
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        logger.info('Prepare to scrape url: ' + url)
        if 'weibo.com/' in url:
            try:
                asyncio.run(scrape_weibo_post.scrape_post(url, conn))
            except Exception as e:
                print(f"An unexpected error occurred during scrape weibo post with {url}: {e}")
        elif 'mp.weixin.qq.com/' in url:
            try:
                asyncio.run(scrape_weixin_post.scrape_post(url, conn))
            except Exception as e:
                print(f"An unexpected error occurred during scrape weixin post with {url}: {e}")
        elif 'www.iesdouyin.com/' in url or 'www.douyin.com/' in url:
            try:
                asyncio.run(scrape_douyin_post.scrape_post(url, conn))
            except Exception as e:
                print(f"An unexpected error occurred during scrape douyin post with {url}: {e}")

    conn.close()