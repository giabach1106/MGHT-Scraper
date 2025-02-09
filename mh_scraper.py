
#!/usr/bin/env python3
import argparse
import asyncio
import os
import re
import json

from typing import List, Dict, Tuple

from playwright.async_api import async_playwright, Response
from PyPDF2 import PdfMerger
from bs4 import BeautifulSoup

# ------------------------------------------------------------------------------
# 1) USER: Paste your fresh cookies here
# ------------------------------------------------------------------------------
COOKIES = [
    {
        "name": "CloudFront-Key-Pair-Id",
        "value": "[REPLACE WITH YOUR COOKIE'S VALUE]",
        "domain": "epub-factory-cdn.mheducation.com",
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
    },
    {
        "name": "CloudFront-Signature",
        "value": "[REPLACE WITH YOUR COOKIE'S VALUE]",
        "domain": "epub-factory-cdn.mheducation.com",
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
    },
    {
        "name": "CloudFront-Policy",
        "value": "[REPLACE WITH YOUR COOKIE'S VALUE]",
        "domain": "epub-factory-cdn.mheducation.com",
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
    },
]

# ------------------------------------------------------------------------------
# 2) USER: Adjust if your domain / path is different
# ------------------------------------------------------------------------------
BASE_URL = (
    "https://epub-factory-cdn.mheducation.com/publish/sn_abcdef/5/1080mp4/OPS/s9ml/"
    "chapter{chapter_3digits}/ch{chapter_2digits}_reader_{page}.xhtml"
)

# ------------------------------------------------------------------------------

async def scrape_page_content(html: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    data = {
        "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
        "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
        "paragraphs": [p.get_text(strip=True) for p in soup.find_all("p")],
    }
    return data


async def fetch_chapter_pages(context, chapter_number: int, scrape_json: bool) -> Tuple[List[str], List[Dict]]:
    """
    - Loops over pages for `chapter_number`, returning:
       1) a list of PDF filepaths
       2) a list of scraped data dicts (if `scrape_json=True`), else empty
    - If the first page is 403/404 => no such chapter => returns empty lists.
    """
    chapter_3 = f"{chapter_number:03d}"  # eg: 1 -> "001"
    chapter_2 = f"{chapter_number:02d}"  # eg. 1 -> "01"

    pdf_files = []
    json_pages_data = []  # each element is a dict with headings, paragraphs, etc.
    page_index = 0

    # Output folder for pages
    chapter_folder = f"chapters/{chapter_number}"
    os.makedirs(chapter_folder, exist_ok=True)

    while True:
        url = BASE_URL.format(chapter_3digits=chapter_3, chapter_2digits=chapter_2, page=page_index)
        print(f"[Chapter {chapter_number}] Fetching page {page_index}: {url}")

        page = await context.new_page()
        response: Response = await page.goto(url, wait_until="networkidle")

        # If 403/404 => no more pages
        if not response or response.status in (403, 404):
            print(f"  -> Stopping at page {page_index}, status={response.status if response else 'No response'}")
            await page.close()
            break

        # 1) Print to PDF
        pdf_filename = os.path.join(chapter_folder, f"chapter_{chapter_number}_page_{page_index}.pdf")
        await page.pdf(
            path=pdf_filename,
            format="A4",
            print_background=True,
            margin={"top": "1in", "bottom": "1in", "left": "1in", "right": "1in"},
        )
        pdf_files.append(pdf_filename)
        print(f"  -> Saved PDF: {pdf_filename}")

        # 2) Optionally scrape text for JSON
        if scrape_json:
            html = await page.content()
            page_data = await scrape_page_content(html)
            # Attach context info
            page_data["chapter"] = chapter_number
            page_data["page"] = page_index
            json_pages_data.append(page_data)

        await page.close()
        page_index += 1

    return pdf_files, json_pages_data


async def merge_pdfs(pdf_list: List[str], output_path: str):
    """Merge a list of PDFs into one file."""
    merger = PdfMerger()
    for pdf in pdf_list:
        merger.append(pdf)
    merger.write(output_path)
    merger.close()


def parse_chapters_arg(chapters_arg: str) -> Tuple[bool, List[int]]:
    """
    Parse --chapters argument.
    - "all" => (True, [])
    - "1,2,5" => (False, [1,2,5])
    - "1-4" => (False, [1,2,3,4])
    """
    chapters_arg = chapters_arg.strip().lower()
    if chapters_arg == "all":
        return True, []

    if "-" in chapters_arg:
        # Range, e.g. "1-4"
        match = re.match(r"(\d+)-(\d+)", chapters_arg)
        if not match:
            raise ValueError(f"Invalid range format for chapters: {chapters_arg}")
        start, end = match.groups()
        return False, list(range(int(start), int(end) + 1))

    # Otherwise, comma-separated
    chapter_nums = []
    for item in chapters_arg.split(","):
        item = item.strip()
        if not item.isdigit():
            raise ValueError(f"Invalid chapter number '{item}'")
        chapter_nums.append(int(item))
    return False, chapter_nums


async def main():
    parser = argparse.ArgumentParser(description="Scrape McGraw-Hill eBook chapters to PDF and optional JSON.")
    parser.add_argument(
        "--chapters",
        type=str,
        default="all",
        help="Which chapters to scrape? 'all' (default), '3', '1,2,5', or '1-4'."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also scrape headings/paragraphs into a JSON file per chapter."
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run browser in a visible window (for debugging)."
    )

    args = parser.parse_args()
    is_all, chapters_list = parse_chapters_arg(args.chapters)
    scrape_json = args.json

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headful)

        all_merged_pdfs = []

        if is_all:
            chapter_num = 1
            while True:
                print(f"=== Trying Chapter {chapter_num} ===")
                context = await browser.new_context()
                await context.add_cookies(COOKIES)

                pdf_files, pages_data = await fetch_chapter_pages(context, chapter_num, scrape_json)
                await context.close()

                if not pdf_files:
                    print(f"No valid pages for chapter {chapter_num}; assuming no more chapters.")
                    break

                # Merge the PDF pages for this chapter
                chapter_folder = f"chapters/{chapter_num}"
                merged_pdf = os.path.join(chapter_folder, f"chapter_{chapter_num}_merged.pdf")
                await merge_pdfs(pdf_files, merged_pdf)
                print(f"✅ Chapter {chapter_num} merged -> {merged_pdf}")
                all_merged_pdfs.append(merged_pdf)

                # Write JSON if requested
                if scrape_json and pages_data:
                    json_path = os.path.join(chapter_folder, f"chapter_{chapter_num}.json")
                    with open(json_path, "w", encoding="utf-8") as jf:
                        json.dump(pages_data, jf, indent=2)
                    print(f"✅ Chapter {chapter_num} JSON -> {json_path}")

                chapter_num += 1

        else:
            # Specific chapters
            for chapter_num in chapters_list:
                print(f"=== Scraping Chapter {chapter_num} ===")
                context = await browser.new_context()
                await context.add_cookies(COOKIES)

                pdf_files, pages_data = await fetch_chapter_pages(context, chapter_num, scrape_json)
                await context.close()

                if not pdf_files:
                    print(f"Warning: Chapter {chapter_num} had no valid pages (403/404). Check cookies/URL.")
                    continue

                # Merge
                chapter_folder = f"chapters/{chapter_num}"
                merged_pdf = os.path.join(chapter_folder, f"chapter_{chapter_num}_merged.pdf")
                await merge_pdfs(pdf_files, merged_pdf)
                print(f"✅ Chapter {chapter_num} merged -> {merged_pdf}")
                all_merged_pdfs.append(merged_pdf)

                # JSON
                if scrape_json and pages_data:
                    json_path = os.path.join(chapter_folder, f"chapter_{chapter_num}.json")
                    with open(json_path, "w", encoding="utf-8") as jf:
                        json.dump(pages_data, jf, indent=2)
                    print(f"✅ Chapter {chapter_num} JSON -> {json_path}")

        # Merge all chapters' PDFs if more than one
        if len(all_merged_pdfs) > 1:
            final_merged = "all_chapters_merged.pdf"
            await merge_pdfs(all_merged_pdfs, final_merged)
            print(f"🎉 All chapters merged into {final_merged}")
        else:
            print("No multi-chapter merge needed or only one chapter found.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
