# Privacy-Crawler

**NSF Privacy Question Answering Project - Principal Investigator Norman Sadeh, CMU**  
*12/02/2023, Tong Jiao*

## Overview
Given a URL or a CSV file containing URLs to privacy policy pages, this crawler can retrieve and save full privacy policy texts from the given URLs.

## Objective of Designing This Crawler
Though app developers are required to provide a URL to their privacy policy on the app store, the website's content from the given URL is not always the full privacy policy text. It may indirectly lead to the privacy policy or have links to other additional information. This software aims to get all information related to privacy from this given URL.  

Detailed design and analysis of this crawler, its performance on popular and random apps in the iOS app store, resources and data used, and its limitations: Check https://docs.google.com/presentation/d/10oUdr1Rszi4xrfLsKUewKoWFaeEmQ7Kc067tvIjfc7o/edit?usp=sharing for more detail.

## Code Organization
- **chatgpt_utils.py:** Utilities related to ChatGPT API calls
- **config.py:** Configurations used throughout the crawler
- **download_text_genai.py:** Functions for downloading text from URLs using generative AI tools
- **get_websites.py:** Retrieves a list of websites to download from the provided CSV file
- **main.py:** Executes the entire extracting process, if you want to do not want to use the `download_text` or `download_text_save` method elsewhere.

## Example Input, Output Files, and Usage
- **Example input file:** `popular_apps.csv` (contains 100 URLs to privacy policies of popular apps on the iOS app store, accessed at 10/14/2023)
- **Output folders:**
  - `saved_policies`: Contains texts from privacy policies
  - `saved_non_policies`: Contains texts from non-privacy policies
- **Used as an API imported by another module:**
```python
from download_text_genai import download_text
from config import config

example_url = "http://pbskids.org/privacy"
example_app_name = ''
policy_text, is_policy_page = download_text(example_url)
```
     

## Usage Instructions for using `main.py`
1. **Prepare Input:**
   - Get a list of websites to crawl and save the app names and URLs in a CSV file.
2. **Specify Configurations in `config.py`:**  
  Explanation of each parameter:
      - `openai_api_key`: The API key for using OpenAI services
      - `link_csv_path`: The CSV file containing links to privacy policies
      - `policy_col_name`: The column name of the column specifying the URL to the privacy policy page of each app
      - `app_id_col_name`: The column name of the column specifying the name of each app
      - `chatgpt_model`: The chatgpt model used in GenAI steps
      - `output_path_policy`: The path of a folder to save texts from privacy policies (determined by the crawler through GenAI)
      - `output_path_nonpolicy`: The path of a folder to save texts from non-privacy policies (determined by the crawler through GenAI)
      - `headless_driver`: If the Selenium driver is using headless mode. _**For non-GUI servers, this should be set to True!**_
      - `chatgpt_api_timeout`: Seconds to wait before retrying for ChatGPT API
      - `chatgpt_api_retries`: Maximum Number of tries for a single ChatGPT API call
      - `initial_prompt`: The initial prompt given to ChatGPT
      - `analyze_anchor_text_prompt_beginning`: Beginning of the prompt when asking ChatGPT to find a link to the correct privacy policy page. It gives context.
      - `analyze_anchor_text_prompt_ending`: Ending of the prompt when asking ChatGPT to find a link to the correct privacy policy page. It describes the task.
      - `if_policy_page_prompt_beginning`: Beginning of the prompt when asking ChatGPT to determine if the content in a webpage is a privacy policy. It gives context.
      - `if_policy_page_prompt_ending`: Ending of the prompt when asking ChatGPT to determine if the content in a webpage is a privacy policy. It describes the task.
      - `if_policy_page_prompt_extract_answer`: The prompt used to ask GenAI to give a one-word answer. When asking ChatGPT to determine if the content in a webpage is a privacy policy, Chain of Thought is used and this prompt extracts answers from GenAI's initial response.
  
3. **Run the Crawler (Execute `main.py`)**
   - After running main.py, privacy policies (determined by GenAI) will be saved in "output_path_policy" and non-policies will be saved in "output_path_nonpolicy".
