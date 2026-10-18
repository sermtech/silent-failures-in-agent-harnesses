"""Index vs stable ref. Needs only playwright. Run: python -X utf8 demo.py"""
import pathlib, sys
from playwright.sync_api import sync_playwright

class StaleRef(Exception): pass

STAMP = """() => { window.__n = window.__n || 0;
  return [...document.querySelectorAll('button.item')].map(b => {
    if (!b.dataset.ref) b.dataset.ref = ++window.__n;   // identity: stamped once, never reused
    return [b.textContent, +b.dataset.ref]; }); }"""

def read_state(page):  # list of (index, ref, text); index = traversal position
    return [(i, ref, text) for i, (text, ref) in enumerate(page.evaluate(STAMP))]

def click_index(page, i):  # naive: re-resolves a remembered position
    page.locator("button.item").nth(i).click()

def click_ref(page, ref):  # identity: resolves to the same element or fails loudly
    loc = page.locator(f'button.item[data-ref="{ref}"]')
    if loc.count() == 0: raise StaleRef(f"ref {ref} no longer resolves; re-read state")
    loc.click()

def clicked(page): return page.locator("#log").inner_text().split()

def fresh(p):
    page = p.chromium.launch(channel="chrome").new_page()
    page.goto(pathlib.Path(__file__).with_name("fixture.html").resolve().as_uri())
    return page

with sync_playwright() as p:
    page = fresh(p)
    state = read_state(page)
    idx, ref, _ = next(s for s in state if s[2] == "delete-account")
    print(f"agent reads: {state}\nagent wants 'delete-account': index={idx} ref={ref}")
    page.evaluate("window.scrollTo(0, 300)"); page.wait_for_timeout(300)  # page re-renders: promo items inserted on top
    print("after scroll:", read_state(page))
    try:
        click_index(page, idx); print("(a) click_index returned normally, no error")
    except Exception as e: print("(a) raised:", e)
    wrong = clicked(page)
    print("    element actually clicked:", wrong)
    page.close(); page = fresh(p)
    read_state(page); page.evaluate("window.scrollTo(0, 300)"); page.wait_for_timeout(300); read_state(page)
    click_ref(page, ref)
    right = clicked(page); print("(b) click_ref -> element actually clicked:", right)
    page.evaluate("document.querySelector('[data-ref=\"%d\"]').remove()" % ref)
    try: click_ref(page, ref); print("(b2) click on removed element: no error (BAD)"); stale = False
    except StaleRef as e: print("(b2) removed element ->", type(e).__name__, "-", e); stale = True
    ok = len(wrong) == 1 and wrong != ["delete-account"] and right == ["delete-account"] and stale
    print("RESULT:", "PASS" if ok else "FAIL", "(naive click hit the wrong element silently; ref hit the right one or failed loudly)")
    sys.exit(0 if ok else 1)
