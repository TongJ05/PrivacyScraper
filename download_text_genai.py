import io
import os
import urllib
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
import re
import chromedriver_binary
import pdfminer.layout
import pdfminer.high_level
from selenium.webdriver.common.by import By
from chatgpt_utils import is_policy_page_cot, get_policy_page_anchor, get_link_with_anchor, get_pdf_text
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


def get_all_policy_text(driver, url, blocklist):
    """
    Given a Selenium driver, current URL and a blocklist, retrieve and return all texts on that page. This method also
    retrieves contents in iframes. If this page has any links to additional information about CA/EU users, they will be
    collected as well.
    """
    text = ''
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

    text_elements = [t for t in soup.find_all(string=True) if t.parent.name not in blocklist]
    for t in text_elements:
        # replaces every newline that is not preceded by a period or column by a space for a better format
        element_text = t.get_text()
        element_text = re.sub(r'(?<=[^.:])\n(?=.)', ' ', element_text)
        text += element_text

    # check if it is a pdf
    if len(text) == 0:
        text = get_pdf_text(url)

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
                print("Error checking iframe for doc ", id)

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


def download_text(url, app_id, output_path_policy, output_path_nonpolicy):
    """
    Download all information related to privacy in a website. This method may navigate to other websites if the given
    website does not contain a full privacy policy and have links to additional information.

    Arguments:
        url: the URL to go to initially
        app_id: the ID or any name of the app
        output_path_policy: if url is a privacy policy, all retrieved texts will be stored here
        output_path_nonpolicy: if url is not a privacy policy, all retrieved texts will be stored here
    Return:
        True if GenAI believes the provided URL leads to a privacy policy page, False otherwise
    """
    options = Options()
    options.add_argument("--enable-javascript")
    options.add_argument("--lang=en")
    if config['headless_driver']:
        options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    blocklist = [
        'style',
        'script',
        'option',
        'label'
        # text in these labels will not be collected
    ]

    driver.get(url)
    driver.implicitly_wait(8)

    # check if current site is policy page
    is_policy_page = is_policy_page_cot(driver, url)
    if 'Yes' in is_policy_page or 'yes' in is_policy_page:
        is_policy_page = True
    else:
        is_policy_page = False

    if is_policy_page:
        # record all texts in this page
        policy_text = get_all_policy_text(driver, url, blocklist)
    else:
        # let GenAI point a link to follow
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        links = soup.find_all('a')
        hrefs, anchor_texts = get_link_with_anchor(links)

        # remove all whitespaces in anchor texts because GenAI tools' responses will not include whitespaces.
        for i in range(len(anchor_texts)):
            anchor_texts[i] = anchor_texts[i].strip()

        try:
            anchor_to_follow = get_policy_page_anchor(page_source)
            href_to_follow = hrefs[anchor_texts.index(anchor_to_follow)]

            if 'http' in href_to_follow:
                driver.get(href_to_follow)
                policy_text = get_all_policy_text(driver, href_to_follow, blocklist)
            else:
                link = driver.find_element(By.XPATH, f"//a[@href='{href_to_follow}']")
                link.click()
                curr_url = driver.current_url
                policy_text = get_all_policy_text(driver, curr_url, blocklist)

        except Exception:
            # an expected error occurred when finding the correct link to follow (there is no valid link)
            policy_text = get_all_policy_text(driver, url, blocklist)

    # write to file
    doc_name = app_id + ".txt"
    if is_policy_page:
        output_path = output_path_policy
    else:
        output_path = output_path_nonpolicy
    output_path = os.path.join(output_path, doc_name)
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(policy_text)

    driver.close()
    return is_policy_page
