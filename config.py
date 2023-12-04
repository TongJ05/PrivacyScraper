config = {
    'openai_api_key': '',
    'link_csv_path': 'popular_apps.csv',
    'policy_col_name': 'privacy_policy_url',
    'app_id_col_name': 'app_id',
    'chatgpt_model': 'gpt-3.5-turbo-1106',
    'output_path_policy': 'new_crawler_result',
    'output_path_nonpolicy': 'new_crawler_result',
    'headless_driver': False,
    'chatgpt_api_timeout': 30,
    'chatgpt_api_retries': 5,
    'initial_prompt': 'You are a software user and am interested in the privacy policy of a software you are using.',
    'analyze_anchor_text_prompt_beginning': 'The following contents are anchor texts associated with links on a website:\n',
    'analyze_anchor_text_prompt_ending': '\nAccording to the previous provided information, I want to navigate to a '
                                         'website containing a company’s privacy policy, and now I am in a website '
                                         'that may have a link to my destination. Please decide clicking which link '
                                         'can take me to the company’s privacy policy page. If there is no possible '
                                         'link, please output NONE. If there is a possible link, output the anchor '
                                         'text only. If there are multiple possible links pointing to policies in '
                                         'different languages, output the anchor text to the English policy only. Do '
                                         'not use complete sentence when responding.',
    'if_policy_page_prompt_beginning': 'The following webpage is the content in a webpage:\n',
    'if_policy_page_prompt_ending': '\nPlease determine if the content of the webpage contains the beginning of a '
                                    'privacy policy (Terms of uses are not privacy policies). If the webpage offers '
                                    'links to the privacy policy, return \"No\" directly. This is the top priority. '
                                    'After considering this, if it is a random webpage or the homepage of the '
                                    'softawre, return \"No\". If it is a beginning of a privacy policy, '
                                    'return \"Yes\". List up to 3 supporting evidence and briefly explain. Limit the '
                                    'explanation of each evidence in 1 sentence. You must stand for either yes or no.',
    'if_policy_page_prompt_extract_answer': 'In a word (Yes/No), the answer is'

}
