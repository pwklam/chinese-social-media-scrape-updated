# 🤖 Social Media Post Scraper

This project is designed to collect data from various social media (Douyin/Weibo/Weixin) posts, including the **title, content, publish date, like count, share count, and comment count**. For Douyin posts, it also extracts **individual comment content** including comment author, text, timestamp, and likes.

***

## 📁 Code Structure


| File/Directory | Description |
| :--- | :--- |
| `main.py` | The **main entry point**. It calls the scraping scripts (`scrape_douyin_post.py`, etc.) and saves all collected data into the SQLite database, `data.db`, upon completion. |
| `scrape_douyin_post.py` | Scrapes **Douyin** post data, including post details and up to 20 individual comments with author, content, timestamp, and likes. |
| `scrape_weibo_post.py` | Scrapes **Weibo** post data. |
| `scrape_weixin_post.py` | Scrapes basic **Weixin (WeChat)** post data (title, content, and publish date only). |
| `scrape_weixin_post_ui.py` | **Extra step** to scrape advanced Weixin post data, including **like count, share count, and comment count** (requires APP UI automation). |
| `export_excel_data.py` | Exports all scraped data from the `data.db` SQLite database to **Excel format**. |
| `urls.txt` | Stores the **list of URLs** for the posts you intend to scrape. |
| `utils.py` | Contains helper methods and utility functions. |
| `config.py` | Stores custom configuration variables. |
| `logging_config.py` | Defines the logger configuration for the project. |
| `requirements.txt` | Lists all necessary Python packages for this project. |
| `ocr_icon/` | Stores icon images used by **OCR** (Optical Character Recognition) when scraping Weixin data via the Windows Weixin application. |
| `data.db` | The SQLite database file. It is generated automatically after executing `main.py`. |
| `data.xlsx` | The final data export file in Excel format. It is generated automatically after executing `export_excel_data.py`. |
| `app.log` | Stores the log history for this project. |
| `README.md` | This project description file. |

***

## 🚀 Execution Steps

### 1. Environment Setup

* **Create Python Virtual Environment (Venv):**
    * Python >= 3.10
    * Navigate to the project directory.
    * Execute: `python -m venv .venv`
    * Activate the environment: `source .venv/Scripts/activate`
* **Install Packages:**
    * Execute: `pip install -r requirements.txt`
* **Install Playwright Environment:**
    * Execute: `playwright install`
* **Install Tesseract-OCR:**  
    * Go to https://github.com/tesseract-ocr/tesseract/releases and download the .exe installer.
    * During installation, make sure to select the language packages chi_sim, chi_tra, and eng under the Additional language data section.
    * After installation, add the installation directory (e.g., C:\Program Files\Tesseract-OCR) to your system PATH.
    * If you installed it in a different location, remember to update the tesseract_cmd variable in config.py accordingly.

### 2. Initial Data Scraping

* **Prepare URLs:** Paste the desired post URLs into the `urls.txt` file.
* **Run Initial Scrape:**
    * Execute: `python main.py`
    * **Note:** This step scrapes **Weibo, Douyin, and basic Weixin** data (title, content, and publish date). It **will not** collect like, share, and comment counts for Weixin, as those require subsequent UI automation and OCR.

### 3. Collecting Advanced Weixin Data (UI Automation)

To obtain the like, share, and comment counts for Weixin posts:

* **Prepare Weixin Client:** Open your **Weixin (WeChat) client** on **Windows**. Click the search pane to open the dedicated search window, and ensure this search window remains **in front of all other applications** (Please follow the steps at the end of this README.md).
* **Run UI Automation:**
    * Execute: `python scrape_weixin_post_ui.py`
    * Wait for the script to complete its process.

### 4. Final Output Generation

* **Convert to Excel:** All collected data is now stored in `data.db`. To generate the final output:
    * Execute: `python export_excel_data.py`
* **Check Results:** Review the final data in the **`data.xlsx`** file.

***

## 🔧 Maintenance Notes

Since this project relies on **web UI and PC application UI automation** technologies, be aware that the code may require modification if the target platform makes structural changes:

* If the **web page document structure** changes, you will need to modify the web element locating methods.
* If the **PC application UI** structure or icons change, the UI automation and OCR logic will need to be updated accordingly.

**I am available to assist with any failures during script execution. Please feel free to contact me if the scripts fail, and I will help to fix the issues promptly.**

***

## 💬 Douyin Comment Extraction

The Douyin scraper (`scrape_douyin_post.py`) automatically extracts up to 20 comments from each post, including:

* **Comment author/username**
* **Comment text content**
* **Comment timestamp**
* **Comment like count**

Comments are stored as JSON in the database's `comments` column. The extraction process:

1. Scrolls the page 3 times to load comments dynamically
2. Uses multiple fallback selectors for robustness
3. Gracefully handles cases where comments are not available
4. Continues scraping even if individual comments fail

The comment data is automatically included when you export to Excel using `export_excel_data.py`.

***

## 📦 Deliverables

* All source code files.

## 💻 Prepare Weixin Client for UI Automation

These steps ensure the Weixin (WeChat) client is correctly positioned for the UI automation script.

### 1. Access the Search Window

Open the **Weixin application** on Windows. Click the main **search bar** (or search pane), then click the title/header, typically labeled **'Search result'**, to open the dedicated search window.

<img src="./images/wechat-main-window.png" />

### 2. Perform an Initial Search

Type a keyword into the search text area, and then click the **'Search' button** to populate the search results.

<img src="./images/wechat-search-window-1.png" />

### 3. Position the Window

**Keep this search window visible** and **in front of any other applications** on your desktop, and **minimize the Wechat main window**.

<img src="./images/wechat-search-window-2.png" />

### 4. Execute and Calibrate the Script

You can now execute the script: `python export_weixin_post_ui.py`.


## Update
- To scrape all comments from a Weibo post, valid authentication cookies from weibo.com are required. Please copy the cookie string from the Chrome DevTools console (refer to the attached screenshot) and save it in a file named weibo_cookie.txt in the project's root directory.

<img src="./images/weibo-get-cookies.png" />