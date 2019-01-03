import os
import time
import logging
import getpass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import csv

"""
- eBlasts tested that it works on: 
    - 1 page of stats (24 sent): https://drip.realgeeks.com/#/e03e3d1b-7d7d-4a1e-8c80-467dd4b37bf7/eblasts/17057/emails?direction=&page=1&per_page=&search=&sort=&_k=zoo1cr
    - 2 pages of stats (31 sent): https://drip.realgeeks.com/#/e03e3d1b-7d7d-4a1e-8c80-467dd4b37bf7/eblasts/14818/emails?direction=&page=1&per_page=&search=&sort=&_k=jf6lng
    - 9 pages of stats (225 sent): https://drip.realgeeks.com/#/e03e3d1b-7d7d-4a1e-8c80-467dd4b37bf7/eblasts/14713/emails?direction=&page=1&per_page=&search=&sort=&_k=olb1te
"""


xpaths = {'submit_button': '//*[@id="login-form"]/button',
          'status': '//*[@id="app"]/div/div[3]/div/div[1]',
          'next_button_class': '//span[@aria-label="Next"]/../..',
          'next_button':   '//span[@aria-label="Next"]'
          }


class Eblast:
    def __init__(self):
        self.start = time.time()
        logger.info('Setting up webdriver')
        # chrome options to disable extensions and give it an user agent
        chrome_options = Options()
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36')
        # chrome_options.add_argument('--headless')  # can't be headless

        # this is to get the chromedriver and assign it to driver
        project_root = os.path.abspath(os.path.dirname(__file__))
        driver_bin = os.path.join(project_root, 'chromedriver')
        self.driver = webdriver.Chrome(executable_path=driver_bin, chrome_options=chrome_options)
        logger.info('Finished setting up webdriver')

    def eblast(self):
        # prompt user for the eBlast they want to get the stats from
        eblast_url = input('Enter the URL of the eBlast you want the stats from: ')

        print('Enter your login credentials...')
        # prompt user for email
        user_email = input('Email: ')
        # prompt the user for a password and attempt to prevent echoing
        user_password = getpass.getpass('Password: ')

        # login page
        login_url = 'https://drip.realgeeks.com/'

        # go to drip so we can sign in
        self.driver.get(login_url)

        # finding the email and password fields by id and assigning them to variables
        email_field = self.driver.find_element_by_id('si-email')
        password_field = self.driver.find_element_by_id('si-password')

        # entering information in the email and password fields
        email_field.send_keys(user_email)
        password_field.send_keys(user_password)

        # finding the submit button by xpath and clicking it to log in
        self.driver.find_element_by_xpath(xpaths['submit_button']).click()

        time.sleep(1.5)
        # going to eblast_url once logged in
        self.driver.get(eblast_url)
        time.sleep(1.5)

        stats_list = []
        details_list = []
        while True:
            # moved into while loop so soup gets updated so stats can be pulled from correct page
            page_html = self.driver.page_source
            soup = BeautifulSoup(page_html, 'html.parser')

            index = 1
            # for each row in stats table
            for row in soup.select('tbody tr'):
                # get the text of each column except for the last column
                sent_date, to, delivered, opens, clicks, unsubscriptions, spam_reports, bounces, failures = [x.text for x in row.find_all('td')[:-1]]
                # add the text from the columns to stats_list
                stats_list.append([sent_date, to, delivered, opens, clicks, unsubscriptions, spam_reports, bounces, failures])

                # if there is a 0 in the delivered column
                if delivered == '0':
                    # finding details button and clicking it
                    self.driver.find_element_by_xpath(f'//*[@id="app"]/div/div[3]/div/div[3]/table/tbody/tr[{index}]/td[10]').click()

                    # this is the lowest time sleep needed to get the right details a message didn't send
                    time.sleep(0.22)

                    # finding alert that says why it has not been delivered
                    try:
                        # wait up to 5 seconds to find status
                        other_status = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, xpaths['status'])))
                        # add status why it wasn't delivered to details_list
                        details_list.append(other_status.text)
                        # go make to eblast_url to move on to next row
                        self.driver.get(eblast_url)
                        index += 1
                    except NoSuchElementException:
                        logger.exception('No status')
                        index += 1
                # else if there is a 0 in the delivered column
                elif delivered == '1':
                    # adding the status of Delivered instead of clicking details and getting the status in order to save time
                    delivered_status = 'Delivered'
                    details_list.append(delivered_status)
                    index += 1
                # shouldn't get here ever
                else:
                    logger.warning('This is the delivery else. The column does not have a 0 or 1.')
                    index += 1

            try:
                # tries to find the class of the next button
                next_button = self.driver.find_element_by_xpath(xpaths['next_button_class'])
                # if the class of the next button disabled then break out of While True loop so it doesn't keep printing last page
                if next_button.get_attribute('class') == 'disabled':
                    break
                else:
                    try:
                        # click next button then sleep so page could load but could probably shorten the time a good amount
                        self.driver.find_element_by_xpath(xpaths['next_button']).click()
                        time.sleep(2.5)
                        # update eblast_url so it doesn't keep using the URL it just used
                        eblast_url = self.driver.current_url
                        continue
                    except NoSuchElementException:
                        logger.exception('Unable to click next button.')
                        print('Unable to click next button.')
                        break
            except NoSuchElementException:
                logger.exception('Unable to find next button class to see if it is disabled.')
                print('Unable to find next button class to see if it is disabled.')
                break

        # adding details of the eBlast to the appropriate row of stats
        row = 0
        for stat in stats_list:
            for dets in details_list:
                stat.insert(10, details_list[row])
                row += 1
                break

        # try to get desktop path to save CSV file
        try:
            # For Unix or Linux
            desktop = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop/eblast_stats.csv')
        except Exception as e:
            # For Windows
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop/eblast_stats.csv')
            logger.exception('Unable to find desktop. |', e)

        # list of the names I want for the header
        header_names = ['Sent Date', 'To', 'Delivered', 'Opens', 'Clicks', 'Unsubscriptions', 'Spam Reports', 'Bounces', 'Failures', 'Details']
        with open(desktop, 'w', encoding='utf-8') as f:
            logger.info('Writing to CSV file.')
            writer = csv.writer(f)

            # write a header row
            writer.writerow({x: x for x in header_names})
            # write actual stats to CSV
            for stat in stats_list:
                writer.writerow(stat)

            logger.info('Finished writing to CSV file.')

    def teardown(self):
        logger.info('Tearing down webdriver')
        # Closes all browser window, safely ends the session, and quits driver
        self.driver.quit()
        logger.info('Finished tearing down webdriver')
        finish = time.time() - self.start
        logger.info(f'Program took {finish} seconds to run.')
        print('Done.')


if __name__ == "__main__":
    # to log exceptions in case information is needed
    logging.basicConfig(filename='logging.txt',
                        format='Time: %(asctime)s - File Name: %(filename)s - Level: %(levelname)s - Message: %(message)s - Function: %(funcName)s - Line: %(lineno)d')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    eb = Eblast()
    eb.eblast()
    eb.teardown()


