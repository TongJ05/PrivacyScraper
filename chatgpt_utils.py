import urllib
import io
import os
import openai
import time
from selenium import webdriver
from bs4 import BeautifulSoup
import re
import chromedriver_binary
import pdfminer.layout
import pdfminer.high_level
from config import config


def reformat(text):
    # remove zero width spaces, replace multiple whitespaces with one
    result = text.replace('‍', '\n')
    result = result.replace(' ', ' ')
    result = re.sub(r'\n+', '\n', result)
    result = re.sub(r'[ \t]+', ' ', result)
    return result


def ask_chatgpt(prompt='', messages=None, retries=config['chatgpt_api_retries']):
    """
    This method passes the given input to ChatGPT API. Input can either be a text prompt or a complete message with
    history conversation context. If both prompt and messages are provided, argument "prompt" will be ignored.

    Arguments:
        prompt: text to be passed to ChatGPT API
        messages: message object to be passed to ChatGPT API
        retries: number of retries if a call to API times out
    Return:
        text answer from ChatGPT or "ChatGPT API Error"
    """

    is_success = False
    while retries > 0:
        try:
            if messages is None:
                response = openai.ChatCompletion.create(
                    model=config['chatgpt_model'],
                    request_timeout=config['chatgpt_api_timeout'],
                    temperature=0,
                    messages=[
                        {"role": "system",
                         "content": config['initial_prompt']},
                        {"role": "user", "content": prompt},
                    ]
                )
            else:
                response = openai.ChatCompletion.create(
                    model=config['chatgpt_model'],
                    request_timeout=config['chatgpt_api_timeout'],
                    temperature=0,
                    messages=messages
                )
            retries = 0
            is_success = True
        except Exception as e:
            print(e)
            retries -= 1
            time.sleep(5)

    if is_success:
        return response.choices[0].message.content
    else:
        return 'ChatGPT API Error'


def get_link_with_anchor(links):
    """
    Given a bs4.element.ResultSet object containing links (obtained by calling find_all('a') to some BeautifulSoup
    object), returns two lists: a list of links, and a list of anchor texts associated with the corresponding link.
    """
    links_list = []
    anchor_texts_list = []
    for link in links:
        href = link.get('href')
        text = link.get_text()
        if href and text:
            links_list.append(href)
            anchor_texts_list.append(text.replace('\n', '').replace('\t', ''))
    return links_list, anchor_texts_list


def get_policy_page_anchor(page_source):
    """
    Given a page source from webdriver (driver.page_source), let GenAI to decide which link may lead to a privacy
    policy page

    Arguments:
        page_source: a page source from webdriver
    Return:
        the answer from GenAI about which anchor text can lead to a privacy policy.
        Common answers include: CORRECT ANCHOR TEXT (if there is such link),
                                text "NONE" (if there is no such link),
                                some text stating that there is no such anchor text (if there is no such link)
    """
    initial_prompt = config['analyze_anchor_text_prompt_beginning']
    task_description = config['analyze_anchor_text_prompt_ending']

    soup = BeautifulSoup(page_source, 'html.parser')
    links = soup.find_all('a')
    hrefs, anchor_texts = get_link_with_anchor(links)
    anchor_text_str = '\n'.join(anchor_texts)

    complete_prompt = initial_prompt + anchor_text_str + task_description
    # print(complete_prompt)
    return ask_chatgpt(prompt=complete_prompt)


def collect_page_text(driver, url=''):
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    # remove headers and footers (if any)
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

    # blocklist = [
    #     'style',
    #     'script',
    #     'option',
    #     'label'
    #     # text in these labels will not be collected
    # ]
    #
    # text_elements = [t for t in soup.find_all(string=True) if t.parent.name not in blocklist]
    # text = ''
    # for t in text_elements:
    #     element_text = t.get_text()
    #     # replaces every newline that is not preceded by a period or column by a space for a better format
    #     element_text = re.sub(r'(?<=[^.:])\n(?=.)', ' ', element_text)
    #     text += element_text
    text = reformat(soup.get_text())

    # check iframe
    text_iframe = ""
    if len(text) < 1000:  # probably contains an iframe with additional contents
        iframe = soup.find('iframe')
        if iframe:
            try:
                iframe_url = iframe['src']
                driver.get(iframe_url)
                driver.implicitly_wait(5)
                iframe_source = driver.page_source
                soup_iframe = BeautifulSoup(iframe_source, 'html.parser')
                text_iframe = soup_iframe.get_text()
            except Exception:
                print("Error checking iframe for doc with URL:", url)
    text += text_iframe

    # check pdf
    if len(text) == 0:
        text = get_pdf_text(url)

    if len(text) > 15000:
        text = text[:15000]

    return text


def is_policy_page_cot(driver, url=''):
    """
        Given a web driver, decides if the current page contains a privacy policy or a beginning of a privacy policy(in
        case of the privacy policy is too long). It will remove page header and footer to diminish the influence of
        irrelevant navigational links, which are very common contents of headers and footers.
        It does not only consider all the plain text of the webpage. If the webpage contains too few content, it checks
        if this webpage contains iframes and all contents in the iframes will also be considered when deciding.
        It also checks if the webpage is a pdf document. If so, all contents in that pdf will be considered as well.

        Arguments:
            driver: a Selenium webdriver
            url: current URL (for pdf checking)
        Return:
            the answer from GenAI describing if the webpage is a privacy policy.
            Common answers include: Yes, yes, No, no
    """
    initial_prompt = config['if_policy_page_prompt_beginning']
    task_description = config['if_policy_page_prompt_ending']

    # Collecting the text of the website
    text = collect_page_text(driver, url)

    # Use Chain of Thought technique to decide if the content is a privacy policy
    complete_prompt = initial_prompt + text + task_description  # first prompt, asking for evidence
    initial_response = ask_chatgpt(prompt=complete_prompt)
    cot_prompt = config['if_policy_page_prompt_extract_answer']  # prompt to extract answer

    messages = [
        {"role": "system",
         "content": config['initial_prompt']},
        {"role": "user", "content": complete_prompt},
        {"role": "system", "content": initial_response},
        {"role": "user", "content": cot_prompt}
    ]

    cot_response = ask_chatgpt(messages=messages).replace('.', '')
    # print(cot_response)
    return cot_response


def is_404_cot(driver, url=''):
    initial_prompt = config['if_404_prompt_beginning']
    task_description = config['if_404_prompt_ending']

    # Collecting the text of the website
    text = collect_page_text(driver, url)

    complete_prompt = initial_prompt + text + task_description  # first prompt, asking for evidence
    initial_response = ask_chatgpt(prompt=complete_prompt)
    cot_prompt = config['if_404_prompt_extract_answer']  # prompt to extract answer

    messages = [
        {"role": "system",
         "content": config['initial_prompt']},
        {"role": "user", "content": complete_prompt},
        {"role": "system", "content": initial_response},
        {"role": "user", "content": cot_prompt}
    ]

    cot_response = ask_chatgpt(messages=messages).replace('.', '')
    return cot_response

def get_pdf_text(url):
    """
    Given a URL to a pdf document, return all its text.

    Arguments:
        url: URL to the pdf document
    Return:
        All text in that pdf document
    """
    text = ''
    try:
        response = urllib.request.urlopen(url)
        content = response.read()
        # Then, extract the text from the PDF content
        with io.BytesIO(content) as data, io.StringIO() as outfp:
            laparams = pdfminer.layout.LAParams()
            pdfminer.high_level.extract_text_to_fp(data, outfp, laparams=laparams)
            text = outfp.getvalue()
        if os.path.exists(url[url.rfind('/') + 1:]):
            os.remove(url[url.rfind('/') + 1:])
    except:
        pass
    return text
