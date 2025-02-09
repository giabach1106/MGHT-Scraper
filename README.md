# McGraw-Hill eBook Scraper with PDF & JSON Exports

This Python project uses [Playwright](https://playwright.dev/python/) to:
- **Render** McGraw-Hill eBook chapters in a **headless Chromium** browser.  
- **Export** each page as a PDF.  
- **Scrape** text (headings, paragraphs) into a **chapter-level JSON** file.  

It then merges each chapter’s PDFs into one `chapter_{N}_merged.pdf`. If you scrape multiple chapters, it can also merge all chapters into **`all_chapters_merged.pdf`**. For JSON, each chapter gets a **`chapter_{N}.json`**.

> **Disclaimer**: Ensure you have permission to save these materials. Respect copyright and the platform’s policies.

## Features

1. **Automatic Chapter Discovery**: `--chapters all` will start at chapter 1, increment up until a missing chapter.  
2. **Custom Chapters**: `--chapters 1,2,5` or `--chapters 1-3`.  
3. **PDF Merging**:  
   - Each chapter’s pages → one merged PDF.  
   - All chapters → `all_chapters_merged.pdf`.  
4. **JSON Extraction** (`--json`):  
   - Uses BeautifulSoup to parse `<h1>`, `<h2>`, `<p>` from each page.  
   - Combines them into a single `chapter_{N}.json` file.  

## Installation

1. **Python 3.9+** recommended.  
2. **Clone** or **download** this repo.  
3. **Install Dependencies**:
    ```console 
    user@machine$ git clone https://github.com/giabach1106/MGHT-Scraper.git
    ```

    Install requirements:
   ```bash
   cd MGHT-Scraper
   python -m venv venv         # optional but recommended
   source venv/bin/activate    # (Windows: venv\Scripts\activate)
   pip install -r requirements.txt
   playwright install
   ```

 ## How to use
1. **Add Fresh Cookies in mh_scraper.py (the COOKIES list)**
    * There are 3 cookies that you will need to find: 'CloudFront-Key-Pair-Id, CloudFront-Signature, CloudFront-Policy'
    * You can get it directly from this link in Chrome or Edge
    - chrome://settings/content/all?searchSubpage=epub-factory-cdn.mheducation.com
    - edge://settings/content/cookies/siteData?searchSubpage=epub-factory-cdn.mheducation.com
    * Or others browser when look for requests to 'epub-factory-cdn.mheducation.com'
2. **Adjust BASE_URL.**
    * Login and Open your eBook 
    * Open the broswer's DevTools (Ctrl+Shift+I or F12)
    * Navigate to the Networktab and watch while navigating between pages or chapters in the eBook.
    * Look for a request where the URL includes something like:
    ```bash https://epub-factory-cdn.mheducation.com/publish/sn_abc123/OPS/s9ml/chapter005/ch05_reader_10.xhtml" ```
    * Replace the numeric parts with placeholders in BASE_URL:
    
    ```bash
    BASE_URL = (
    "https://epub-factory-cdn.mheducation.com/publish/sn_abc123/OPS/s9ml/"
    "chapter{chapter_3digits}/ch{chapter_2digits}_reader_{page}.xhtml"
    )
    ```
3. **When you ready, run this command.**
    ```
    python mh_scraper.py --chapters all [--json] [--headful]
    ```
    Options:
    `--chapters all` → scrape from chapter 1 up until no more exist (scrape the whole book).
    `--chapters 3` or `--chapters 1,2,4` or `--chapters 1-5`.
    `--json` → also parse textual data into chapter_{N}.json.
    `--headful` → run Chromium with a visible window (for debugging).
4. **Examples Usage** 
    * 1) Scrape all chapters (PDF only)
    `python mh_scraper.py --chapters all`

    * 2) Scrape chapters 1 & 2, export JSON as well:
    `python mh_scraper.py --chapters 1,2 --json`

    * 3) Scrape chapters 1-3 with a visible browser
    `python mh_scraper.py --chapters 1-3 --headful`
   