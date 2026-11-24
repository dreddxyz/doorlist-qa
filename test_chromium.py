import httpx
from playwright.sync_api import sync_playwright, expect

def test_reservation_and_sold_out(server):
    show=httpx.post(server+"/shows",json={"capacity":1}).json()["id"]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page()
        page.goto(server+"/?show="+show)
        book=page.get_by_role("button",name="Забронировать")
        book.click()
        expect(page.locator("output")).to_have_text("Бронь подтверждена")
        expect(page.locator("#left")).to_have_text("0")
        book.click()
        expect(page.locator("output")).to_have_text("Недостаточно мест")
        browser.close()
