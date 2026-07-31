"""Capture researcher browser flow screenshots for P0-5 verification."""

import json
import os
import time

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
API = "http://localhost:8000/api/v1"
OUT = "output/playwright/context25-v3"
os.makedirs(OUT, exist_ok=True)

results = []


def snap(page, name):
    path = f"{OUT}/{name}.png"
    page.screenshot(path=path, full_page=True)
    results.append({"step": name, "path": path, "url": page.url})
    print(f"  ✓ {name} → {path}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()

    # --- 1. Public Home ---
    t0 = time.time()
    page.goto(f"{BASE}/", wait_until="networkidle")
    snap(page, "01-public-home")
    print(f"    home loaded in {time.time() - t0:.1f}s")

    # --- 2. Login as Researcher ---
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.fill("#username", "researcher")
    page.fill("#password", "researcher123")
    page.click("button.login-btn")
    page.wait_for_timeout(3000)
    snap(page, "02-researcher-login-dashboard")
    print(f"    logged in as researcher, current URL: {page.url}")

    # --- 3. Literature → Books → Search for 《针灸甲乙经》 ---
    page.goto(f"{BASE}/literature", wait_until="networkidle")
    snap(page, "03-researcher-literature")

    # Try to find and click on 针灸甲乙经
    page.goto(f"{BASE}/books", wait_until="networkidle")
    snap(page, "04-researcher-books")

    # --- 4. Search for 针灸甲乙经 ---
    # Navigate to search or try direct document view
    page.goto(f"{BASE}/documents", wait_until="networkidle")
    snap(page, "05-researcher-documents")

    # Try to find search field
    try:
        search_input = page.locator(
            'input[placeholder*="搜索"], input[placeholder*="search"], input[aria-label*="搜索"]'
        ).first
        if search_input.is_visible(timeout=3000):
            search_input.fill("针灸甲乙经")
            search_input.press("Enter")
            page.wait_for_timeout(2000)
            snap(page, "06-researcher-search-results")
    except Exception as e:
        print(f"    search skipped: {e}")

    # --- 5. Academic RAG Query ---
    page.goto(f"{BASE}/research", wait_until="networkidle")
    snap(page, "07-researcher-research-portal")

    # Try to find a search/query input
    try:
        for sel in [
            'input[placeholder*="研究"], input[placeholder*="查询"], textarea[placeholder*="问题"]',
            'input[type="text"]',
            "textarea",
        ]:
            qinput = page.locator(sel).first
            if qinput.is_visible(timeout=2000):
                qinput.fill("《针灸甲乙经》的成书特点是什么？")
                break
        snap(page, "08-researcher-rag-query-input")
    except Exception as e:
        print(f"    query input skipped: {e}")

    # --- 6. Classical Versions ---
    page.goto(f"{BASE}/versions", wait_until="networkidle")
    snap(page, "09-researcher-versions")

    # --- 7. Persons ---
    page.goto(f"{BASE}/persons", wait_until="networkidle")
    snap(page, "10-researcher-persons")

    # --- 8. Graph/Knowledge Graph ---
    page.goto(f"{BASE}/graph", wait_until="networkidle")
    snap(page, "11-researcher-graph")

    # --- 9. V4 Research Portal ---
    page.goto(f"{BASE}/v4", wait_until="networkidle")
    snap(page, "12-researcher-v4")

    # --- 10. Workspace / Notes ---
    page.goto(f"{BASE}/workspace", wait_until="networkidle")
    snap(page, "13-researcher-workspace")

    browser.close()

# Write results
with open(f"{OUT}/browser-results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\nDone: {len(results)} screenshots captured")
