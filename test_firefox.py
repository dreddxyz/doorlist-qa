import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_reload_retains_available_count(server):
    show=httpx.post(server+"/shows",json={"capacity":3}).json()["id"]
    options=webdriver.FirefoxOptions()
    options.add_argument("-headless")
    with webdriver.Firefox(options=options) as driver:
        driver.get(server+"/?show="+show)
        wait=WebDriverWait(driver,12)
        qty=driver.find_element(By.TAG_NAME,"input")
        qty.clear()
        qty.send_keys("2")
        wait.until(EC.element_to_be_clickable((By.TAG_NAME,"button"))).click()
        wait.until(EC.text_to_be_present_in_element((By.TAG_NAME,"output"),"Бронь подтверждена"))
        driver.refresh()
        wait.until(EC.text_to_be_present_in_element((By.ID,"left"),"1"))
