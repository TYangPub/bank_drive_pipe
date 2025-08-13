import asyncio
import calendar
import csv
import cv2
import datetime
import gc
import json
import logging
import numpy as np
import os
import pyautogui
import time
from dataclasses import dataclass, field
from dotenv import load_dotenv
from functools import partial
from typing import Any, Callable, ClassVar, Optional

# from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

load_dotenv()
user = os.getenv("chase_user")
password = os.getenv("chase_pass")
browser_path = os.getenv("browser_path")
user_data_dir = os.getenv("user_data_dir")

@dataclass
class Timer:
    timers: ClassVar[dict[str, Any]] = {}
    name: Optional[str] = None
    text: str = "Elapsed time: {elapsed:.4f} seconds"
    logger: Optional[Callable[[str], None]] = print
    _start_time: Optional[float] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.name is not None:
            self.timers.setdefault(self.name, 0)
        
    def start(self) -> None:
        if self._start_time is not None:
            raise RuntimeError("Timer is already running")
        self._start_time = time.perf_counter()
    
    def stop(self) -> float:
        if self._start_time is None:
            raise RuntimeError("Timer is not running")
        
        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None

        if self.logger:
            self.logger(self.text.format(elapsed=elapsed_time))
        if self.name:
            self.timers[self.name] += elapsed_time

        # print(elapsed_time) 
        return elapsed_time

    def __enter__(self):
        self.start()
        return self
    def __exit__(self, *exc_info):
        self.stop()

class logging:
    def __init__(self, page):
        self.page = page

    async def track_clicks(self):
        await self.page.expose_function("logClick", lambda selector: print(f"Clicked: {selector}"))
        await self.page.evaluate("""
            document.addEventListener('click', event => {
                let target = event.target;
                let selector = '';
                try {
                    selector = target.tagName.toLowerCase();
                    if (target.id)
                        selector += '#' + target.id;
                    else if (target.className)
                        selector += '.' + target.className.split(' ').join('.');
                } catch {}
                window.logClick(selector);
            });
        """)

class state_track:
    def __init__(self):
        self.step = None
        self.account = None
        self.status = "Not started"
        self.error = None

    def update(self, account, step, status, error=None):
        self.account = account
        self.step = step
        self.status = status
        self.error = error

class login:
    def __init__(self, page):
        self.page = page
    
    base_dir = os.path.dirname(os.path.abspath(__file__))

    async def gotosite(self):
        await self.page.goto("https://www.chase.com/business")
        await self.page.wait_for_selector('text="Sign in"', state='visible', timeout=3000)
        await self.page.click('text="Sign in"')

    async def cred_fill(self, paths: list, cred):
        image_found = False 
        for path in paths:
            try:
                template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                w, h = template.shape[::-1]

                screenshot = pyautogui.screenshot()
                screenshot_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
                res = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
                threshold = 0.8
                loc = np.where(res >= threshold)
                if loc[0].size:
                    pt = (loc[1][0], loc[0][0])  # first detected region
                    center_x = pt[0] + w // 2
                    center_y = pt[1] + h // 2
                    pyautogui.click(center_x, center_y)
                    print(f"Used {path}")
                    image_found = True
                    break
                else:
                    pass
                    print(f"Image not found with {path}")
            except Exception as e:
                print(f"Error: {e}")

        if not image_found:
            print("Image not found")
            return

        pyautogui.write(cred, interval=0.08)

        return()

    async def submit_btn(self, paths: list):
        image_found = False
        for path in paths:
            try:    
                template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                w, h = template.shape[::-1]

                screenshot = pyautogui.screenshot()
                screenshot_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
                res = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
                threshold = 0.8
                loc = np.where(res >= threshold)
                if loc[0].size:
                    pt = (loc[1][0], loc[0][0])  # first detected region
                    center_x = pt[0] + w // 2
                    center_y = pt[1] + h // 2
                    pyautogui.click(center_x, center_y)
                    image_found = True
                else:
                    print("Image not found with ", path)
            except Exception as e:
                print(f"Error: {e}")

    async def login(self, bank):
        await self.gotosite()
        time.sleep(3)
        photos_dir = os.path.join(login.base_dir, "photos", str(bank))
        # await self.cred_fill([file for file in os.listdir(photos_dir)
        #                       if os.path.isfile(os.path.join(photos_dir, file)) and "Username" in file], user)
        # await self.cred_fill([file for file in os.listdir(photos_dir) if os.path.isfile(os.path.join(photos_dir, file)) and "Password" in file], password)
        # await self.submit_btn([file for file in os.listdir(photos_dir) if os.path.isfile(os.path.join(photos_dir, file)) and "submit" in file])

        await self.cred_fill([os.path.join(photos_dir, file) for file in os.listdir(photos_dir) if "Username" in file], user)
        await self.cred_fill([os.path.join(photos_dir, file) for file in os.listdir(photos_dir) if "Password" in file], password)
        await self.submit_btn([os.path.join(photos_dir, file) for file in os.listdir(photos_dir) if "submit" in file])
        # print([file for file in os.listdir(photos_dir) if "Username" in file])
        return

class csv_d:
    def __init__(self, page):
        self.page = page

    async def init_sel_acct(self, name, num):
        account_selectors = [
            f'a:has-text("{name}")',
            f'a:has-text("{num}")',
            f'span:has-text("{name}")',  
            f'span:has-text("{num}")', 
            f'a:has(span:has-text("{name}"))',
            f'a:has(span:has-text("{num}"))'
        ]

        for selector in account_selectors:
            try:
                await self.page.wait_for_selector(selector, state='visible', timeout=2000)
                # print(f"Found account using selector: {selector}")
                await self.page.click(selector)
                # print(f"Successfully clicked on account: {selector}")
                await self.page.wait_for_load_state('networkidle', timeout=3000)
                return True
                
            except Exception as e:
                print(f"Failed to find account with selector '{selector}': {e}")
                continue
        
        print(f"Could not find account: {selector}")
        return False

    async def init_click_download(self):
        download_selectors = [
            '[id*="download-activity"]',
            '#quick-action-download-activity-tooltip-info',
            '#quick-action-download-activity-tooltip-button',
            '[data-testid="quick-action-download-activity-tooltip-button"]',
            '[data-testid="quick-action-download-activity-tooltip-info"]',
            'button:has-text("Download")',
        ]
        for selector in download_selectors:
            try:
                await self.page.wait_for_selector(selector, state='visible', timeout=2000)
                # print(f"Found download button: {selector}")
                await self.page.click(selector)
                # print("Successfully clicked download button")
                await self.page.wait_for_load_state('networkidle', timeout=3000)
                return True
                
            except Exception as e:
                print(f"Failed to find download button with selector '{selector}': {e}")
                continue
        
        print("Could not find download button")
        return False

    async def check_overview(self):
        try:
            await self.page.wait_for_selector('a[href="#/dashboard/overview"] span:has-text("Overview")', timeout=2000)
            return True
        except TimeoutError:
            return False
        except Exception:
            print(f"Overview not found")
            return False

    async def verify_acct(self, name, num):
        try:
            await self.page.wait_for_selector('#select-account-selector', state='visible', timeout=5000)

            account_text = await self.page.locator('#select-account-selector span').text_content()

            if name in account_text:
                print(f"Correct account selected: {account_text}")
                return True
            else:
                print(f"Wrong account selected. Expected: {name}, Got: {account_text}")
                try:
                    await self.page.locator('#select-account-selector').click()
                    correct_acct = await self.page.wait_for_selector(f'mds-select-option[label="{name} (...{num})"]', timeout=3000)
                    await correct_acct.click()
                    await asyncio.sleep(0.3)
                    print(f"Selected account: {name} (...{num})")
                    return True
                except Exception as e:
                    print(f"Error selecting account: {e} with mds-select-option[label={name} (...{num})]")
                    return False
                
        except Exception as e:
            # print(f"Error verifying account selection: {e}")
            raise RuntimeError("Error") from e
        
        
    async def set_file_type(self):
        try:
            # Click the file type dropdown
            await self.page.wait_for_selector('#select-downloadFileTypeOption', state='visible', timeout=2500)
            await self.page.click('#select-downloadFileTypeOption')
            await self.page.wait_for_timeout(1000)
            
            # Dropdown options
            csv_selectors = [
                'span:has-text("Spreadsheet (Excel, CSV)")',
                'li:has-text("Spreadsheet (Excel, CSV)")',
                '[role="option"]:has-text("Spreadsheet (Excel, CSV)")',
            ]
            
            for selector in csv_selectors:
                try:
                    await self.page.click(selector)
                    # print("Successfully selected CSV file type")
                    return True
                except:
                    continue
            
            print("Could not select CSV file type")
            return False
            
        except Exception as e:
            # print(f"Error setting file type: {e}")
            raise RuntimeError("Error") from e
        
    async def set_date_range(self, month, year):
        # timer = Timer(name="choosing range")

        start_date = datetime.date(year, month, 1).strftime('%m/%d/%Y')
        end_date = datetime.date(year, month, calendar.monthrange(year, month)[1]).strftime('%m/%d/%Y')
        try:
            # Click the timeframe dropdown
            await self.page.wait_for_selector('#select-downloadActivityOptionId', state='visible', timeout=3000)
            await self.page.click('#select-downloadActivityOptionId')
            await self.page.wait_for_timeout(500)
            
            # Select "Choose a date range" option
            date_range_selectors = [
                'mds-select-option[label="Choose a date range"]',
                'span[class="option__accessible-text]:has-text("Choose a date range")',
                'span:has-text("Choose a date range")',
                '[role="option"]:has-text("Choose a date range")',
            ]
            
            for selector in date_range_selectors:
                try:
                    # timer.start()
                    await self.page.wait_for_selector(selector, state='visible', timeout=3000)
                    await self.page.click(selector)
                    # timer.stop()
                    # print(f"Selected with {selector}")
                    break
                except:
                    continue
            
            # Wait for date input fields to appear
            await self.page.wait_for_timeout(3000)
            
            # Fill start date
            start_date_selector = '#accountActivityFromDate-input-input'
            await self.page.wait_for_selector(start_date_selector, state='visible', timeout=3000)
            await self.page.fill(start_date_selector, start_date)
            # print(f"Set start date: {start_date}")
            
            # Fill end date
            end_date_selector = '#accountActivityToDate-input-input'
            await self.page.wait_for_selector(end_date_selector, state='visible', timeout=3000)
            await self.page.fill(end_date_selector, end_date)
            # print(f"Set end date: {end_date}")
            
            return True
        
        except Exception as e:
            # print(f"Error setting date range: {e}")
            raise RuntimeError("Error") from e

    async def execute_download(self, path, name, year, month):
        if month < 10:
            month = "0" + str(month)
        try:
            # Download button possiblities
            download_button_selectors = [
                'button[type="button", class="button button--primary button --fluid"]',
                'mds-button#download',
                'mds-button[text="Download"]',
                'mds-button[variant="primary"]',
                'mds-button:has-text("Download")'
            ]
            
            for selector in download_button_selectors:
                try:
                    await self.page.wait_for_selector(selector, state='visible', timeout=3000)
                    async with self.page.expect_download(timeout=3000) as download_info:
                        await self.page.click(selector)
                    # print("Successfully clicked Download button")
                    
                    # Wait for download to initiate
                    # page.wait_for_timeout(3000)
                    download = await download_info.value
                    await download.save_as(f"{path}{name}__{month}_{year}.csv")
                    return True
                    
                except:
                    continue
            
            print("Could not find Download button")
            raise RuntimeError("Could not find download button")
            
        except Exception as e:
            # print(f"Error executing download: {e}")
            raise RuntimeError("Error") from e
        
    async def click_download_other_activity(self):
        # Wait for the download other activity button
        other_activity_selectors = [
            'button:has(span:has-text("Download other activity"))',
            'span:has-text("Download other activity")',
            'button:has-text("Download other activity")',
        ]
        
        last_exception = None

        for selector in other_activity_selectors:
            try:
                await self.page.wait_for_selector(selector, state='visible', timeout=3000)
                await self.page.click(selector)
                print(f"Successfully clicked {selector}")
                
                # Wait for page to load
                await self.page.wait_for_load_state('networkidle', timeout=3000)
                
                
                # perform another check overview
                if await self.check_overview():
                    overview_success = await self.init_click_download()
                    if not overview_success:
                        raise RuntimeError("Failed to click out of overview")

                return True
            except Exception as e:
                last_exception = e
                continue
        if last_exception:
            raise RuntimeError("No button found") from last_exception
        else:
            raise RuntimeError("No button found")

    def init_download(self, name, num, month, year):
        try:
            self.init_sel_acct(name, num)
            self.init_click_download()
            self.verify_acct(name, num)
            self.set_file_type()
            self.set_date_range(month, year)
            self.execute_download("downloads/", name, month, year)
            self.click_download_other_activity()
        except Exception as e:
            print(f"Error: {e}")
        return
    
    async def norm_download(self, name, num, month, year):
        steps = [
            ("check_overview", self.check_overview),
            ("verify_acct", partial(self.verify_acct, name, num)),
            ("set_file_type", self.set_file_type),
            ("set_date_range", partial(self.set_date_range, month, year)),
            ("execute_download", partial(self.execute_download, "downloads/", name, month, year)),
            ("click_download_other_activity", self.click_download_other_activity),
        ]

        state = state_track()

        # try:
        #     if await self.check_overview():
        #         success = await self.init_click_download()
        #         if not success:
        #             raise RuntimeError("Failed to click out of overview")
        #     print("- verify")
        #     await self.verify_acct(name, num)
        #     print("- file type")
        #     await self.set_file_type()
        #     print("- date range")
        #     await self.set_date_range(month, year)
        #     print("- download")
        #     await self.execute_download("downloads/", name, month, year)
        #     print("- other")
        #     await self.click_download_other_activity()
        #     await asyncio.sleep(1.5)
        # except Exception as e:
        #     print(f"Error: {e}")

        for i, (step_name, func) in enumerate(steps):
            state.update(step=step_name, account=name, status="running")
            try:
                if step_name == "check_overview":
                    if await func():
                        success = await self.init_click_download()
                        if not success:
                            state.update(step=step_name, account=name, status="failed")
                            raise RuntimeError("Failed to click out of overview")
                else:
                    await func()
            except Exception as e:
                state.update(step=step_name, account=name, status="failed", error=str(e))
                print(state)
                break
            else:
                state.update(step=step_name, account=name, status="success")

class null_handle:
    def __init__(self, page):
        self.page = page
    
    downloads = 
    n_found = set([acct['name'] for acct in bank_accts]) - set(downloads)

    # async def check_downloads(self, d_path, bank_accts):
    #     downloads = [name[:-12] for name in os.listdir(str(d_path))]
    #     n_found = set([acct['name'] for acct in bank_accts]) - set(downloads)
    #     try:
    #         for acct in n_found:
    #             acct_name = acct
    #             acct_num = bank_accts[bank_accts['name'] == acct_name]

    async def gen_blank(res_path, bank_accts)


async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            slow_mo=1000,
            viewport={"width": 1920, "height": 1040},
            accept_downloads=True
        )
        page = await context.new_page()

        # Initialize logger and start tracking clicks
        click_logger = logging(page)
        await click_logger.track_clicks()

        login_instance = login(page)
        await login_instance.login("chase_bus")

        csv_instance = csv_d(page)

        # Example of async command loop (simplified)
        cont = True
        try:
            with open('creds/bank_accts.json', 'r') as file:
                bank_accts = json.load(file)
        except Exception:
            with open('src/creds/bank_accts.json', 'r') as file:
                bank_accts = json.load(file)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        photos_dir = os.path.join(base_dir, "photos", str("chase_bus"))
        # print([file for file in os.listdir(photos_dir) if os.path.isfile(os.path.join(photos_dir)) and "Username" in file])

        while cont:
            debug_input = await asyncio.to_thread(input, "Enter a command: ")
            match debug_input:
                case "user":
                    await login_instance.cred_fill([os.path.join(photos_dir, file) for file in os.listdir(photos_dir) if "Username" in file], user)
                case "pass":
                    await login_instance.cred_fill([os.path.join(photos_dir, file) for file in os.listdir(photos_dir) if "Password" in file], password)
                case "loop":
                    results = []
                    for acct in bank_accts:
                        try:
                            await csv_instance.norm_download(acct['name'], acct['num'], 4, 2025)
                            print(f"Downloaded {acct['name']}({acct['num']}) for March 2025\n")
                            gc.collect()
                            results.append({'account': acct, 'status': "success"})
                        except Exception as e:
                            print(f"Error for account {acct['name']}({acct['num']}): {e}")
                            results.append({'account': acct, 'status': 'error', 'error': str(e)})
                            continue
                    for r in results:
                        print(r)
                case "exit":
                    await context.close()
                    cont = False

class testing:
    # def __init__(self, page):
    #     self.page = page
    base_dir = os.path.dirname(os.path.abspath(__file__))

    def access_files(self, bank):
        photo_dir = os.path.join(testing.base_dir, "photos", str(bank))
        print(photo_dir)
        all_users = os.listdir(photo_dir)
        print(all_users)
        return

async def debugging():
    # async with async_playwright() as p:
    #     context = await p.chromium.launch_persistent_context(
    #         user_data_dir,
    #         headless=False,
    #         slow_mo=1000,
    #         viewport={"width": 1920, "height": 1040},
    #         accept_downloads=True
    #     )
    #     page = await context.new_page()
    try:
        tester = testing()
        tester.access_files("chase_bus")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # asyncio.run(debugging())
    asyncio.run(main())