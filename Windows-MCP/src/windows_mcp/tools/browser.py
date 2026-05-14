import sys
import os
from playwright.sync_api import sync_playwright

def search_google(query: str, output_file: str):
    """Searches Google for the query and saves the top results to output_file."""
    print(f"Searching for: {query}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"https://html.duckduckgo.com/html/?q={query}")
            page.wait_for_load_state("networkidle", timeout=10000)
            
            # Extract top search results text
            text = page.evaluate("() => document.body.innerText")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Search Results for: {query}\n")
                f.write("="*40 + "\n\n")
                f.write(text[:5000]) # save first 5000 chars
            
            print(f"Successfully saved results to {output_file}")
        except Exception as e:
            print(f"Error during search: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "search":
        search_google(sys.argv[2], sys.argv[3])
    else:
        print("Usage: python -m windows_mcp.tools.browser search <query> <output_file>")
