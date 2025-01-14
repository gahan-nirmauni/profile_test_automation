# coding=utf-8
import csv
import logging
import time
import base64
import requests
import unittest
import shutil

from selenium.common.exceptions import TimeoutException
from slugify import slugify
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
# imports for cropping snapshot
from PIL import Image
from io import BytesIO


from configure import *

__author__ = "Gahan Saraiya"


def _sleep(seconds=2, flag=True):
    if flag:
        time.sleep(seconds)


class BaseTest(unittest.TestCase):
    live_server_url = "http://urbanprofile.gujarat.gov.in/"
    browser_driver = BROWSER_DRIVER
    credentials = CREDENTIALS
    scroll_pause_time = 0.5
    logger = logging.getLogger('UnitTest')

    def setUp(self):
        if BROWSER == "chrome":
            options = webdriver.ChromeOptions()
            preferences = {
                "download.default_directory": DOWNLOAD_DIR,
                "download.prompt_for_download": False,
            }
            options.add_experimental_option("prefs", preferences)
            options.add_experimental_option("detach", True)
            options.add_argument("--disable-extensions")
            self.selenium = webdriver.Chrome(executable_path=self.browser_driver, options=options)
        else:
            profile = webdriver.FirefoxProfile()
            profile.set_preference('browser.download.folderList', 2)  # custom location
            profile.set_preference('browser.download.manager.showWhenStarting', False)
            profile.set_preference('browser.download.dir', DOWNLOAD_DIR)
            profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/csv')
            self.selenium = webdriver.Firefox(executable_path=self.browser_driver, firefox_profile=profile)
        self.selenium.set_window_size(BROWSER_WIDTH, BROWSER_HEIGHT)
        self.logger.info("Initialized test with BROWSER: {} custom screen resolution W: {} and H: {}".format(BROWSER, BROWSER_WIDTH, BROWSER_HEIGHT))

    def tearDown(self):
        pass
        # self.selenium.close()
        # super().tearDownClass()

    @staticmethod
    def crop_image(img_element, snapshot):
        location, size = img_element.location, img_element.size

        img = Image.open(BytesIO(snapshot))
        # im = Image.open(StringIO(base64.decodebytes(self.selenium.get_screenshot_as_base64())))
        left, top = location['x'], location['y']
        right = location['x'] + size['width']
        bottom = location['y'] + size['height']
        img = img.crop((left, top, right, bottom))
        return img

    def read_image(self, img):
        img.save("captcha.png")
        with open("captcha.png", 'rb') as f:
            captcha_content = f.read()
        img_post_data = "data:image/png;base64," + str(base64.b64encode(captcha_content))[2:-1]
        resp = requests.post(API_URL, data={"image": img_post_data})
        captcha = resp.json().get('text').strip()
        self.logger.info("TEXT-CAPTCHA>> {}".format(captcha))
        if captcha:
            _captcha = os.path.join(CAPTCHA_DIR, "{}.png".format(captcha))
            shutil.move("captcha.png", _captcha)
        return captcha

    def _test_login(self):
        self.selenium.get(self.live_server_url)
        username_input = self.selenium.find_element_by_name("txt_user")
        username_input.send_keys(self.credentials['username'])
        password_input = self.selenium.find_element_by_name("txt_pwd")
        password_input.send_keys(self.credentials['password'])
        captcha_input = self.selenium.find_element_by_id("txtturing")
        # workout for captcha
        png = self.selenium.get_screenshot_as_png()
        img = self.selenium.find_element_by_id("Image1")
        im = self.crop_image(img, png)
        captcha = self.read_image(im)
        captcha_input.send_keys(captcha)
        _sleep(1)
        self.selenium.find_element_by_id('btn_login').click()

    def scroll(self):
        # Get scroll height
        last_height = self.selenium.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to bottom
            self.selenium.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep(self.scroll_pause_time)
            # Calculate new scroll height and compare with last scroll height
            new_height = self.selenium.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def take_snapshot(self, session_prefix=None):
        now = datetime.now()
        now_date = now.strftime('%d_%b_%Y')
        session_prefix = now.strftime('%Y-%d-%m_%H') if not session_prefix else session_prefix
        _name = "screen-shot_{}.png".format(now.strftime('%Y-%d-%m_%H.%M.%S'))
        _path = os.path.join(SNAPSHOT_DIR, 'selenium', now_date, session_prefix)
        os.makedirs(_path, exist_ok=True)
        self.selenium.save_screenshot(os.path.join(_path, _name))
        self.logger.info("Snapshot for url : {} saved at: {}".format(self.selenium.current_url, _path))

    class Meta:
        abstract = True


class UrbanProfileTest(BaseTest):
    def _test_town_directory(self):
        element = self.selenium.find_element_by_xpath("//*[contains(text(), 'TOWN DIRECTORY')]")
        element.click()
        _sleep(3)
        table = self.selenium.find_element_by_id("Table2")

    def test_ordered(self):
        self.selenium.set_window_size('1366', '768')
        # self.selenium.fullscreen_window()
        # self.take_snapshot()
        _sleep(1)
        self._test_login()
        _sleep(1)
        # self._test_town_directory()
        _sleep(1)


class VillageProfileTest(BaseTest):
    live_server_url = "http://villageprofile.gujarat.gov.in/"
    logger = logging.getLogger('sms_automation_test.VillageProfileTest')
    detail_report_file = os.path.join(DOWNLOAD_DIR, "detailreport.xls")
    csv_content_holder = []
    table_content_holder = []
    school_types = ['Primary School', 'Secondary School', 'Higher Secondary School']
    districts = ['Ahmadabad', 'Amreli', 'Anand', 'Arvalli', 'Banas Kantha', 'Bharuch', 'Bhavnagar', 'Botad', 'Chhota udepur', 'Devbhumi Dwarka', 'Dohad', 'Gandhinagar', 'Gir Somnath', 'Jamnagar', 'Junagadh', 'Kachchh', 'Kheda', 'Mahesana', 'Mahisagar', 'Morbi', 'Narmada', 'Navsari', 'Panch Mahals', 'Patan', 'Porbandar ', 'Rajkot', 'Sabar Kantha', 'Surat', 'Surendranagar', 'Tapi', 'The Dangs', 'Vadodara', 'Valsad']
    timestamp = VILLAGE_PROFILE_DATE if VILLAGE_PROFILE_DATE else None

    @property
    def school_type(self):
        return self.school_types

    def _test_login(self):
        self.selenium.get(self.live_server_url)
        username_input = self.selenium.find_element_by_id("LoginUser_UserName")
        username_input.send_keys(self.credentials['username'])
        password_input = self.selenium.find_element_by_id("LoginUser_Password")
        password_input.send_keys(self.credentials['password'])
        captcha_input = self.selenium.find_element_by_id("txtcaptcha")
        # workout for captcha
        png = self.selenium.get_screenshot_as_png()
        img = self.selenium.find_element_by_id("Image1")
        im = self.crop_image(img, png)
        captcha = self.read_image(im)
        captcha_input.send_keys(captcha)
        _sleep(1)
        self.selenium.find_element_by_id('LoginButton').click()
        self.logger.info("Clicked on login")

    def explore_school_detail_report(self):
        url_to_explore = self.live_server_url + "SchoolDetailReport.aspx"  # "http://villageprofile.gujarat.gov.in/DetailReport.aspx"
        self.logger.info("Exploring Detail Report from: {}".format(url_to_explore))
        self.selenium.get(url_to_explore)
        _sleep(2)
        district_selector = self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_District")  # select district pop up
        districts = [x.text for x in district_selector.find_elements_by_tag_name("option") if not x.text[0] == "-"]
        districts = self.districts
        self.logger.info("Exploring {} districts:\n{}".format(len(districts), districts))
        for district in districts:
            # _sleep(1)
            self.explore_school_district(district)
            self.table_content_holder = []
        self.logger.info("Exploration completed")

    def explore_school_district(self, district):
        self.logger.info("Working for District: {} ({})".format(district, "-"))
        self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_District").send_keys(district)
        # select talukas
        taluka_selector = self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_Taluka")
        talukas = [x.text for x in taluka_selector.find_elements_by_tag_name("option") if not x.text[0] == "-"]
        for taluka in talukas:
            self.explore_school_district_taluka(district, taluka)
            # self.write_content(slugify('{}_{}'.format(district, self.school_type[0])), self.school_type[0], content=self.table_content_holder)
            self.logger.debug("Value of content holder: >> {} (length: {}) <<".format(self.csv_content_holder, len(self.csv_content_holder)))

    def explore_school_district_taluka(self, district, taluka):
        self.logger.debug("Working for taluka: {}".format(taluka))
        self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_Taluka").send_keys(taluka)
        # school_type_selector = self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_population")  # select sector
        # school_types = [x.text for x in school_type_selector.find_elements_by_tag_name("option") if not (x.text[0] == "-" or 'select' in x.text.lower())]
        school_types = self.school_type
        for school_type in school_types:
            self.logger.debug("working for school_type: {}".format(school_type))
            self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_population").send_keys(school_type)
            # select timelines
            timeline_selector = self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_year")  # select year
            timelines = [x.text for x in timeline_selector.find_elements_by_tag_name("option") if not (x.text[0] == "-" or 'select' in x.text.lower())]
            timelines = [self.timestamp] if self.timestamp else timelines[0]
            for timeline in timelines:
                self.grab_school_data(district, taluka, timeline)
                self.logger.info("[LOOP-END] Completed Combination loop for District: {}\t|\tTaluka: {}\t|\tschool_type: {}\t|\ttimeline: {}".format(
                        district, taluka, self.school_type, timeline))
            self.write_content(slugify('{}_{}'.format(district, school_type)), school_type, content=self.table_content_holder)

    def grab_school_data(self, district, taluka, timeline):
        self.logger.debug("working for timeline: {}".format(timeline))
        self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_year").send_keys(timeline)
        view_report_btn = self.selenium.find_element_by_id("ContentPlaceHolder1_Button1")
        try:
            view_report_btn.click()
        except TimeoutException as e:
            self.logger.error("Caught TimeoutException: {}\nReExploring.....".format(e))
            _sleep(5)
            url_to_explore = self.live_server_url + "SchoolDetailReport.aspx"  # "http://villageprofile.gujarat.gov.in/DetailReport.aspx"
            self.logger.info("Exploring Detail Report: {}".format(url_to_explore))
            try:
                self.selenium.get(url_to_explore)
                if self.selenium.find_element_by_id("btnlogout"):
                    self._test_login()
                    self.selenium.get(url_to_explore)
            except TimeoutException as e:
                self.logger.error("Caught TimeoutException: {}\nReExploring.....again...".format(e))
                _sleep(15)
                self.selenium.get(url_to_explore)
                if self.selenium.find_element_by_id("btnlogout"):
                    self._test_login()
                    self.selenium.get(url_to_explore)
            self.explore_school_district(district)
        if "ContentPlaceHolder1_GridView1" in self.selenium.page_source:
            table_content = self.parse_table(self.selenium.page_source, "ContentPlaceHolder1_GridView1", district, timeline)
            table_header, table_data = table_content[0], table_content[1:]
            self.logger.debug("Generated table data Headers: {}".format(table_header))
            self.table_content_holder = self.table_content_holder + table_data if self.table_content_holder else self.table_content_holder + table_content
        else:
            self.logger.info("No data for choice: District: {}\t|\tTaluka: {}\t|\tschool_type: {}\t|\ttimeline: {}".format(
                    district, taluka, self.school_type, timeline))

    def parse_table(self, page_source, table_id, district, year):
        self.logger.debug("Parsing page source for table id: {}".format(table_id))
        soup = BeautifulSoup(page_source, "html.parser")
        table = soup.find("table", {"id": table_id})
        table_content = [
            [district] + [j.text.strip().replace("\n", "-").replace(",", ";") for j in i.find_all('td')] + [year]
            if i.find_all('td')
            else ["DistrictName"] + [j.text.strip() for j in i.find_all('th')] + ["Timeline"]
            for i in table.find_all('tr')
        ]
        self.logger.debug("Content of length (with header): {}".format(len(table_content)))
        return table_content

    def write_content(self, prefix_name, school_type, content):
        self.logger.debug("Writing content (length: {}) for {}".format(len(content), prefix_name))
        file_path = os.path.join(CSV_DIR, school_type)
        os.makedirs(file_path, exist_ok=True)
        file_location = os.path.join(file_path, "{}_school_detail_report.csv".format(prefix_name))
        with open(file_location, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for row in content:
                writer.writerow(row)

    def explore_detail_report(self):
        """
        districts = ['Ahmadabad', 'Amreli', 'Anand  ', 'Arvalli', 'Banas Kantha', 'Bharuch', 'Bhavnagar', 'Botad', 'Chhota udepur', 'Devbhumi Dwarka', 'Dohad  ', 'Gandhinagar', 'Gir Somnath', 'Jamnagar', 'Junagadh', 'Kachchh', 'Kheda', 'Mahesana', 'Mahisagar', 'Morbi', 'Narmada', 'Navsari  ', 'Panch Mahals', 'Patan  ', 'Porbandar ', 'Rajkot', 'Sabar Kantha', 'Surat', 'Surendranagar', 'Tapi', 'The Dangs', 'Vadodara', 'Valsad']
        sectors = ['Population', 'Health_Facility', 'Health_Doctors', 'Health_Other', 'Drinking Water', 'Sanitation', 'Electrification', 'Nutrition', 'Rural Road', 'Tourism', 'Transportation & Communication', 'Animal Husbandry', 'Other Amenities', 'Literacy', 'Employment and Social Security', 'Others', 'Worker', 'BPL Family', 'Livestock', 'Land Use Pattern', 'Primary Education', 'Secondary Education', 'Higher Secondary Education']
        """
        url_to_explore = self.live_server_url + "DetailReport.aspx"  # "http://villageprofile.gujarat.gov.in/DetailReport.aspx"
        self.logger.info("Exploring Detail Report: {}".format(url_to_explore))
        self.selenium.get(url_to_explore)
        district_selector = self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_District")  # select district pop up
        districts = [(x.text, x.get_attribute('value')) for x in district_selector.find_elements_by_tag_name("option") if not x.text[0] == "-"]
        sector_selector = self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_population")  # select sector
        sectors = [x.text for x in sector_selector.find_elements_by_tag_name("option") if not (x.text[0] == "-" or 'select' in x.text.lower())]
        timeline_selector = self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_year")  # select date
        timelines = [x.text for x in timeline_selector.find_elements_by_tag_name("option") if not (x.text[0] == "-" or 'select' in x.text.lower())]
        #  ['31-03-2018', '30-06-2017', '31-03-2017', '01-04-2016', '01-04-2015', '01-04-2014', '01-04-2013']
        for district, district_code in districts:
            self.logger.info("Working for District: {} ({})".format(district, district_code))
            for sector in sectors:
                self.logger.debug("working for sector: {}".format(sector))
                for timeline in timelines:
                    self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_District").send_keys(district)
                    self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_population").send_keys(sector)
                    self.selenium.find_element_by_id("ContentPlaceHolder1_ddl_year").send_keys(timeline)
                    get_excel_button = self.selenium.find_element_by_id("ContentPlaceHolder1_Button3")
                    get_excel_button.click()
                    _sleep(3)  # sleep for a while to avoid file not found error
                    self.read_file(district, sector, timeline)
                    self.remove_file(district, sector, timeline)
                self.rename_file("{}_{}".format(district, sector), content=self.csv_content_holder)
                self.logger.debug("Value of content holder: >> {} (length: {}) <<".format(self.csv_content_holder, len(self.csv_content_holder)))
                self.csv_content_holder = []
                break
            break

    def read_file(self, *args):
        # new_name = "_".join(args)
        new_name = "_".join(args[:2])
        try:
            with open(self.detail_report_file, "r") as f:
                content = f.read()
        except FileNotFoundError as e:
            self.logger.error("File Note Found!! Exception: {}".format(e))
            _sleep(5)
            return self.read_file()
        soup = BeautifulSoup(content, "html.parser")
        table = soup.find('table', {'id': 'ContentPlaceHolder1_GridView1'})
        table_content = [
            [j.text.encode('utf8').strip() for j in i.find_all('td')] if i.find_all('td') else [j.text.strip() for j in i.find_all('th')]
            for i in table.find_all('tr')
        ]
        # Table Headers would be:
        # ['Sr.No', 'District Name', 'Taluka Name', 'Village Name', 'No. Of Household', 'Total Population', 'Male', 'Female',
        # 'Total SC Population', 'SC Male', 'SC Female', 'Total ST Population', 'ST Male', 'ST Female']
        table_header, table_data = table_content[0], table_content[1:]
        self.logger.info("Generated table data Headers: {}".format(table_header))
        self.csv_content_holder = self.csv_content_holder + table_data if self.csv_content_holder else self.csv_content_holder + table_content
        # self.rename_file(new_name, content=table_content)

    def rename_file(self, new_name, content=None):
        if content:
            folder_name = os.path.join(DOWNLOAD_DIR, "csv")
            os.makedirs(folder_name, exist_ok=True)
            file_location = os.path.join(folder_name, "{}_detail_report.csv".format(new_name))
            with open(file_location, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                for row in content:
                    writer.writerow(row)
        else:
            folder_name = os.path.join(DOWNLOAD_DIR, "html", new_name)
            os.makedirs(folder_name, exist_ok=True)
            file_location = os.path.join(folder_name, "{}.html".format(new_name))
            shutil.move(self.detail_report_file, file_location)

    def remove_file(self, *args):
        folder_name = os.path.join(DOWNLOAD_DIR, "html", "_".join(args[:2]))
        os.makedirs(folder_name, exist_ok=True)
        new_name = "_".join(args)
        file_location = os.path.join(folder_name, "{}_detail_report.html".format(new_name))
        shutil.move(self.detail_report_file, file_location)
        # os.remove(self.detail_report_file)

    def test_ordered(self):
        _sleep(1)
        self._test_login()
        _sleep(2)
        self.explore_school_detail_report()


if __name__ == "__main__":
    # unittest.main()
    # self = VillageProfileTest()
    # self.setUp()
    # self._test_login()
    # _sleep(2)
    # self.explore_school_detail_report()
    pass
