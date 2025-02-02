'''
Welcome to the BETTER BEST BUY BATCH BUYING BOT (B6).

STEP 1a: Enter the URL(s) of your product page(s) into /product_urls.txt.
STEP 1b: Enter your credit card CVV (if desired for auto-checkout) here:
'''
FILENAME = r'./product_urls.txt'
#FILENAME = r'./product_urls_test.txt'

try:
    from secret import CVV
except:
    CVV = ''

'''
STEP 2: Provide the path to chromedriver.exe
        Get it here: https://developer.chrome.com/docs/chromedriver/downloads
'''
CHROMEDRIVER_PATH = r'./chromedriver.exe'

'''
STEP 3: Modify these Paths for your particular Chrome installation.
        This is used to keep user logged in to BestBuy.com
        Find Paths here: chrome://version/

        Note: Don't write profile name after "Chrome/User Data", because it will make a new folder in that path.
        Note: You need to close the Chrome browser manually, because only one Chrome browser can use the profile at a time
'''

PROFILE_PATH = r'C:\Users\David\AppData\Local\Google\Chrome\User Data'
PROFILE_NAME = "Default"

'''
STEP 4: Adjust the min and max delay times as desired.
'''
SHORT_DELAY_1 = 4
SHORT_DELAY_2 = 6

'''
STEP 5: Set the following flags for how far the bot will proceed in the checkout process.
'''
AUTO_ADD_TO_CART = True     # Open the product page in Chrome and clicks the "Add to Cart" button
AUTO_CHECKOUT = False        # Open the Shopping Cart page and clicks "Checkout". Fills in the CVV code.
AUTO_PLACE_ORDER = False     # From the checkout page, clicks "Place Order". WARNING: THIS WILL MAKE THE PURCHASE AND CHARGE YOUR CC

import alert
import winsound
import random
import time
from datetime import datetime
import bs4
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Product:
    def __init__(self, url, driver):
        self.url = url
        self.sku = url.split('skuId=')[1] # We use the SKU to find the right "Add to Cart" button, skipping over any recommended accessories.
        self.in_cart = False    # True after product successfully added to cart.
        self.checked_out = False
        
        self.last_notified = 0

        driver.switch_to.new_window('tab')
        driver.get(self.url)
        self.window_handle = driver.current_window_handle

    def check_stock(self, session):
        # Returns True/False whether a Product is in stock.
        # Takes a requests session as input.
        try:
            page = session.get(self.url)            
            if page.status_code != 200:
                print(f'{timestamp()} ERROR: Status Code {page.status_code}')
                print(f'{timestamp()} Unable to load {self.url}')
                return False
            
        except:
            print(f'{timestamp()} Unable to load {self.url}')
            return False    
        
        try:
            soup = bs4.BeautifulSoup(page.content, 'html.parser')
                
            #Extract Title and Price
            self.title = soup.find('div', class_='sku-title').h1.text
            self.price = soup.find('div', class_='priceView-hero-price priceView-customer-price').span.text

            #Look at the Big Add to Cart Button
            self.status = soup.find('button', {'data-sku-id':self.sku}).text

            #Print Results                
            print(timestamp(), self.title, self.price, self.status)

            if self.status == "Add to Cart":
            #Beep to alert user. Then open the product page in Chromedriver
                beep()
                if time.time() - self.last_notified > 3600: # Only notify once per hour
                    self.last_notified = time.time()
                    alert.email_alert(f'{timestamp()} {self.title} is in stock! {self.url}')
                    alert.pushover(f'{timestamp()} {self.title} is in stock! {self.url}')
                return True
            else:
                return False
        except:
            print(f'{timestamp()} ERROR: Cannot parse {self.url}')
            return False
        
    def add_to_cart(self, driver):
        # Switch to the product tab if it exists, and refresh. Else load a new page
        if self.window_handle in driver.window_handles:
            driver.switch_to.window(self.window_handle)
            try:
                driver.refresh()
            except:
                print(f"{timestamp()} ERROR: Unable to open product page for {self.title} in Chromedriver.")
                return

        else:
            driver.switch_to.new_window('tab')
            try:
                driver.get(self.url)
                self.window_handle = driver.current_window_handle
            except:
                print(f"{timestamp()} ERROR: Unable to open product page for {self.title} in Chromedriver.")
                return
                
        print(f"{timestamp()} Attempting to add {self.title} to cart...")    
        # Click the Add to Cart Button
        try:
            add_to_cart_xpath = f'//button[@data-sku-id={self.sku}]'
            cart_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, add_to_cart_xpath)))
            cart_button.click()
            print(f'{timestamp()} SUCCESS: {self.title} added to cart!')
            self.in_cart = True
            return
        
        except:
            input(f'ERROR: Unable to click "Add to Cart" for {self.title}. ADD TO CART MANUALLY!') # We don't want to keep refreshing. Give the user a chance to click manually!
            self.in_cart = True  
            return

    def checkout(self, driver):         
        print(f'{timestamp()} Attempting Checkout for {self.title}...')

        #Open the Best Buy Cart Page in a new tab.
        try:
            driver.switch_to.new_window('tab')
            driver.get('https://www.bestbuy.com/cart')
        except:
            print(f'{timestamp()} Unable to open shopping cart page. Checkout aborted!')
            return False

        #Find and click the checkout button.
        try:
            checkout_xpath = '//button[@type="button"][. = "Checkout"]'
            checkout_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, checkout_xpath)))
            checkout_button.click()
            print(f"{timestamp()} SUCCESS: Checkout Successful!")
            self.checked_out = True

        except:
            input(f"{timestamp()} FAILURE: Unable to click Checkout Button. USER MUST CLICK MANUALLY!") # Pause to allow user to click manually
            True
 
        #Fill in the CVV field
        try:
            cvv_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "cvv")))
            cvv_field.send_keys(CVV)
        except:
            pass
        
        #If we got here we've reached the checkout page.
        return True
    

    def place_order(self, driver):
        # Just another safety check
        if not AUTO_PLACE_ORDER:
            return False
        
        print(f'{timestamp()} Attempting to Place Order for {self.title}...')
        # From the Checkout page
        try:
            order_xpath = '//button[contains(@data-track, "Place your Order")]'
            order_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, order_xpath)))
            order_button.click()
            print(f'{timestamp()} SUCCESS: Order Placed!')
            return True
        except:
            input(f'{timestamp()} FAILURE: Unable to click Place Order Button. USER MUST CLICK MANUALLY')
            return True
            

def beep():
    for i in range(3):
        winsound.Beep(1000,200)
        winsound.Beep(2000,200)
        winsound.Beep(3000,200)

def timestamp():
    return datetime.now().strftime("%m/%d/%Y %H:%M:%S")


def load_urls(filename):
    try:
        with open(filename) as f:
            return f.read().splitlines()
    except:
        print(f'{timestamp()} ERROR: Unable to open {FILENAME}')    
        return []
    

def init_chromedriver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_PATH}")
    options.add_argument(f"--profile-directory={PROFILE_NAME}")
    options.add_argument('--log-level=3') # Silent mode
    service = Service(CHROMEDRIVER_PATH)

    return webdriver.Chrome(service=service, options=options)


def load_session():
    session = requests.Session()
    # Modifying headers is required to avoid Requests being blocked for being a scraping bot.
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                            'referer': 'https://www.bestbuy.com/'})
    return session


def rand_sleep(delay_1, delay_2):
    # Averaging two random delay values skews results towards the middle. 
    delay_time = (random.randint(delay_1, delay_2) + random.randint(delay_1, delay_2))/2
    time.sleep(delay_time)
        

if __name__ == "__main__":
    print('-'*50)
    print('WELCOME TO BETTER BEST BUY BATCH BUYING BOT (B6)')
    print('-'*50)

    # Initialize Chromedriver
    print(f'{timestamp()} Initializing Chromedriver at {CHROMEDRIVER_PATH}...')
    driver = init_chromedriver()

    # Load Requests Session
    print(f'{timestamp()} Loading Requests session...')
    session = load_session()

    # Load Product URLs
    print(f'{timestamp()} Loading product URLs from {FILENAME}...')    
    url_list = load_urls(FILENAME)

    # Create Product List
    product_list = [Product(url, driver) for url in url_list]
    print(f'{timestamp()} Starting main loop for {len(product_list)} products...','\n')

    alert.email_alert(f'{timestamp()} B6 Bot Started!')
    alert.pushover(f'{timestamp()} B6 Bot Started!')

    while len(product_list) > 0:
        for product in product_list:
            #Check the product availablity and add to cart if allowed.
            #Skips the check if product has already been added to cart.
            if not product.in_cart and product.check_stock(session) and AUTO_ADD_TO_CART:
                product.add_to_cart(driver)

            # If we're not automatically checking out, we're done with the product.
            if product.in_cart and not AUTO_CHECKOUT:
                product_list.remove(product)
            
            # If we want to automatically attempt to check out...
            if product.in_cart and not product.checked_out and AUTO_CHECKOUT:
                product.checkout(driver)
            
            # Similarly, if we reach the checkout page and do not desire to place order automatically, we are done.
            if product.in_cart and product.checked_out and not AUTO_PLACE_ORDER:
                product_list.remove(product)
            
            #Attempt to place order...
            if product.in_cart and product.checked_out and AUTO_PLACE_ORDER:            
                if product.place_order(driver):
                    #Remove the product from list if order successfully placed.
                    product_list.remove(product)

            rand_sleep(SHORT_DELAY_1, SHORT_DELAY_2)

    input(f'{timestamp()} Product list empty. Bot terminated.')