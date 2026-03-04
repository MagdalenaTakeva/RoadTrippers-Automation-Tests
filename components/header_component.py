from selenium.webdriver.common.by import By


class HeaderComponent:

    AVATAR_BUTTON = (
        By.CSS_SELECTOR,
        "a[href*='https://maps.roadtrippers.com/people']"
    )

    MY_TRIPS_LINK = (
        By.CSS_SELECTOR,
        "a[href*='a[href*='/people/'][href*='/trips']']"
    )

    def __init__(self, driver, base_page):
        self.driver = driver
        self.base_page = base_page

    def click_avatar(self):
        # Use base_page methods
        avatar_btn = self.base_page.wait_for_element_to_be_clickable_with_timeout(self.AVATAR_BUTTON)
        avatar_btn.click()
        self.base_page.log("Avatar clicked", level="debug")

    def go_to_my_trips(self):
        self.click_avatar()
        # Again — use base_page
        my_trips_link = self.base_page.wait_for_element_to_be_clickable_with_timeout(self.MY_TRIPS_LINK)
        my_trips_link.click()
        self.base_page.log("Navigated to My Trips", level="info")