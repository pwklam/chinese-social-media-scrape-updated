Step 1 – Install packages

Download Install packages.ipynb from the GitHub repository
chinese-social-media-scrape-updated/Install packages.ipynb.

I have separated the scraping of Weibo and Douyin into two different processes.

Scraping Weibo

Go to chinese-social-media-scrape-updated/weibo.

Download the file scrape-social-media-main.

Before starting the scraping task, update the contents of Url.txt and weibo_cookie.txt:

Url.txt stores the URLs that you intend to scrape.

weibo_cookie.txt stores the cookie information used to log in to a Weibo account. This allows you to scrape all visible comments from Weibo. To obtain the cookie, copy the cookie string from the Chrome DevTools console (see the attached screenshot) and save it in a file named weibo_cookie.txt in the project’s root directory.

Use Dec 18.ipynb to run the scraping task. Make sure to update the file paths in the notebook before running it.
