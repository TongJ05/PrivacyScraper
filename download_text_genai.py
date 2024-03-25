import io
import os
import urllib
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
import re
import time
import chromedriver_binary
import pdfminer.layout
import pdfminer.high_level
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from chatgpt_utils import is_policy_page_cot, get_policy_page_anchor, get_link_with_anchor, get_pdf_text, is_404_cot
from config import config


def extract_ca_eu(links):
    """
    Given a bs4.element.ResultSet object containing links (obtained by calling find_all('a') to some BeautifulSoup
    object), returns a list of links leading to CA/EU privacy statements using heuristics.
    """
    ca_eu_links = []
    saved_hrefs = []
    for link in links:
        href = link.get('href')
        text = link.get_text()
        if href and text:
            if 'http' not in href:  # it's an internal link
                continue
            if ("california" in text.lower() or "CA" in text) and (
                    "notice" in text.lower() or "privacy" in text.lower()) or "CCPA" in text:
                if href not in saved_hrefs:
                    ca_eu_links.append(link)
                    saved_hrefs.append(href)
            if ("european union" in text.lower() or "EU" in text) and (
                    "notice" in text.lower() or "privacy" in text.lower()):
                if href not in saved_hrefs:
                    ca_eu_links.append(link)
                    saved_hrefs.append(href)

    return ca_eu_links


def reformat(text):
    # remove zero width spaces, replace multiple whitespaces with one
    result = text.replace('‍', '\n')
    result = result.replace(' ', ' ')
    result = re.sub(r'\n+', '\n', result)
    result = re.sub(r'[ \t]+', ' ', result)
    return result


def get_all_policy_text(driver, url):
    """
    Given a Selenium driver, current URL and a blocklist, retrieve and return all texts on that page. This method also
    retrieves contents in iframes. If this page has any links to additional information about CA/EU users, they will be
    collected as well.
    """
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    # remove header and footer if any
    header = soup.find('header')
    head = soup.find('head')
    footer = soup.find('footer')
    foot = soup.find('foot')

    if header:
        header.extract()
    if head:
        head.extract()
    if footer:
        footer.extract()
    if foot:
        foot.extract()

    text = reformat(soup.get_text())

    # check if it is a pdf
    if len(text) == 0:
        pdf_result = get_pdf_text(url)
        if pdf_result is not None:
            text = pdf_result

    # check iframe
    if len(text) < 1000:  # probably contains an iframe with additional contents
        iframe = soup.find('iframe')
        if iframe:
            try:
                iframe_url = iframe['src']
                driver.get(iframe_url)
                driver.implicitly_wait(5)
                iframe_source = driver.page_source
                soup_iframe = BeautifulSoup(iframe_source, 'html.parser')
                text += soup_iframe.get_text()
            except Exception:
                print("Error checking iframe for doc with URL:", url)

    # check CA/EU notice
    links = soup.find_all('a')
    ca_eu_text = ""
    ca_eu_links = extract_ca_eu(links)
    appendix_num = 0
    if len(ca_eu_links) > 0:
        for link in ca_eu_links:
            href = link.get('href')
            title = link.get_text()
            driver.get(href)
            driver.implicitly_wait(8)
            additional_src = driver.page_source
            additional_soup = BeautifulSoup(additional_src, 'html.parser')

            title_str = f'Appendix {appendix_num}: {title}\n'
            ca_eu_text += title_str
            ca_eu_text += additional_soup.get_text()
            appendix_num += 1
    text += ca_eu_text
    return text


def download_text_save(url, app_id, output_path_policy, output_path_nonpolicy, app_name=''):
    """
    Download all information related to privacy in a website. This method may navigate to other websites if the given
    website does not contain a full privacy policy and have links to additional information.

    Arguments:
        url: the URL to go to initially
        app_id: the ID or any name of the app, it will be used when saving the downloaded text
        output_path_policy: if url is a privacy policy, all retrieved texts will be stored here
        output_path_nonpolicy: if url is not a privacy policy, all retrieved texts will be stored here
        app_name (optional): the name of the app that the desired privacy policy is for. It will be used when the provided
        url does not lead to a privacy policy page.
    Return:
        A tuple: (policy_text, is_policy_page)
        policy_text: the downloaded and saved full text
        is_policy_page: True if GenAI believes the provided URL leads to a privacy policy page, False otherwise
    """
    policy_text, is_policy_page = download_text(url, app_name)
    doc_name = app_id + ".txt"
    if is_policy_page:
        output_path = output_path_policy
    else:
        output_path = output_path_nonpolicy
    output_path = os.path.join(output_path, doc_name)
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(policy_text)
    return policy_text, is_policy_page


def download_text(url, app_name=''):
    """
    The behavior of this method is almost identical to that of the previous download_text_save method. The only
    difference is that this method does not write the extracted privacy policy into a text file.
    Arguments:
        url: the URL to go to initially
        app_name (optional): the name of the app that the desired privacy policy is for. It will be used when the provided
        url does not lead to a privacy policy page.
    Return:
        A tuple: (policy_text, is_policy_page)
        policy_text: the downloaded and saved full text
        is_policy_page: True if GenAI believes the provided URL leads to a privacy policy page, False otherwise
    """
    options = Options()
    options.add_argument("--enable-javascript")
    options.add_argument("--lang=en")
    if config['headless_driver']:
        options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(8)
    provided_url = url

    try:
        driver.get(url)
        first_page_source = driver.page_source
        soup_first = BeautifulSoup(first_page_source, 'html.parser')
        first_text = soup_first.get_text()
    except Exception:
        # error in visiting the provided URL, do a search immediately
        is_policy_page = False

        if app_name == '' or app_name is None:
            policy_text = 'An error occurred when visiting the provided URL.'
        else:
            search_query = app_name + " privacy policy English"

            driver.get('https://www.google.com')
            search_box = driver.find_element(By.NAME, 'q')
            search_query = search_query
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.RETURN)
            time.sleep(2)
            result_url = driver.find_elements(By.CSS_SELECTOR, 'div#search .g a')[0].get_attribute('href')

            # get policy text from the top search result
            driver.get(str(result_url))
            policy_text = get_all_policy_text(driver, url)

        driver.close()
        return policy_text, is_policy_page

    # For non-error cases, check if current site is policy page
    is_policy_page = is_policy_page_cot(driver, url)
    if 'Yes' in is_policy_page or 'yes' in is_policy_page:
        is_policy_page = True
    else:
        is_policy_page = False

    if is_policy_page:
        # record all texts in this page
        policy_text = get_all_policy_text(driver, url)
    else:
        # check if current page is a 404 page. If so, do a google search to find the privacy policy page
        is_404_page = is_404_cot(driver, url)
        if 'Yes' in is_404_page or 'yes' in is_404_page:
            is_404_page = True
        else:
            is_404_page = False

        if is_404_page:
            # for 404 pages, do a google search
            if app_name == '':
                policy_text = first_text
            else:
                search_query = app_name + " privacy policy English"
                driver.get('https://www.google.com')
                search_box = driver.find_element(By.NAME, 'q')
                search_query = search_query
                search_box.send_keys(search_query)
                search_box.send_keys(Keys.RETURN)
                time.sleep(2)
                result_url = driver.find_elements(By.CSS_SELECTOR, 'div#search .g a')[0].get_attribute('href')

                # get policy text from the top search result
                driver.get(str(result_url))
                policy_text = get_all_policy_text(driver, url)

        else:
            # for other pages, let GenAI point a link to follow
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            links = soup.find_all('a')
            hrefs, anchor_texts = get_link_with_anchor(links)

            for i in range(len(anchor_texts)):
                anchor_texts[i] = anchor_texts[i].strip()

            try:
                anchor_to_follow = get_policy_page_anchor(page_source)
                href_to_follow = hrefs[anchor_texts.index(anchor_to_follow)]

                if 'http' in href_to_follow:
                    driver.get(href_to_follow)
                    policy_text = get_all_policy_text(driver, href_to_follow)
                else:
                    link = driver.find_element(By.XPATH, f"//a[@href='{href_to_follow}']")
                    link.click()
                    curr_url = driver.current_url
                    policy_text = get_all_policy_text(driver, curr_url)

            except Exception:
                # an expected error occurred when finding the correct link to follow (there is no valid link)
                policy_text = get_all_policy_text(driver, url)

    driver.close()
    return policy_text, is_policy_page
