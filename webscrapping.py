import asyncio
from playwright.async_api import async_playwright
import re

async def scrape_gmail_emails(url):
    """
    Scrape Gmail contact numbers (emails) from a given website URL using Playwright.

    Args:
        url (str): The website URL to scrape.

    Returns:
        list: A list of unique Gmail email addresses found on the page.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        # Wait for the page to load completely
        await page.wait_for_load_state('networkidle')
        content = await page.content()
        await browser.close()

    # Regex pattern to match Gmail email addresses
    gmail_pattern = r'\b[A-Za-z0-9._%+-]+@gmail\.com\b'
    emails = re.findall(gmail_pattern, content, re.IGNORECASE)
    # Return unique emails
    return list(set(emails))

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python webscrapping.py <url>")
        print("Example: python webscrapping.py https://example.com")
        sys.exit(1)

    url = sys.argv[1]
    try:
        emails = asyncio.run(scrape_gmail_emails(url))
        if emails:
            print("Gmail emails found:")
            for email in emails:
                print(email)
        else:
            print("No Gmail emails found on the page.")
    except Exception as e:
        print(f"Error: {e}")