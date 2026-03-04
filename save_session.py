import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

""" 
One time Cookie Saver Script

How to use it:
    1. Run the script in bash: python save_session.py
    2. A browser opens.
    3. Log in manually
    4. Confirm you are logged in (avatar visible)
    5. roadtrippers_cookies.pkl is saved
    6. We're authenticated instantly. No bot detection triggered. 

This should not be repeated until session expires

Note: A reusable login method is created in base page: 
login_via_cookies(self, cookie_file="roadtrippers_cookies.pkl")


WHY THIS WORKS

    1. We’re not automating login.
    2. We're reusing:
        - Auth cookies
        - Valid session
        - Server-issued tokens
        - From a real browser session.

Automation detection only blocks login flow — not valid sessions.
"""

options = Options()
driver = webdriver.Chrome(service=Service(), options=options)

driver.get("https://roadtrippers.com")

print("👉 Please log in manually in the opened browser.")
print("👉 The script will automatically detect when login succeeds.")

# Wait until avatar (logged-in indicator) appears
avatar_locator = (By.CSS_SELECTOR, ".rt-user-img [href*='/people']")

WebDriverWait(driver, 300).until(
    EC.presence_of_element_located(avatar_locator)
)

print("✅ Login detected. Saving cookies...")

pickle.dump(driver.get_cookies(), open("roadtrippers_cookies.pkl", "wb"))

print("✅ Cookies saved successfully.")
driver.quit()
