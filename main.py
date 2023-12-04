import time
from config import config
from get_websites import get_website_list
from download_text_genai import download_text
import openai

policy_col_name = config['policy_col_name']
appid_col_name = config['app_id_col_name']
csv_path = config['link_csv_path']
openai.api_key = config['openai_api_key']

start_time = time.time()
results = []
app_list = get_website_list(csv_file_path=csv_path, policy_col_name=policy_col_name, appid_col_name=appid_col_name)
print(f'Using the following opanai api key: {config["openai_api_key"]}')

for app in app_list:
    policy_url = app[0]
    app_id = app[1]
    output_path_policy = config['output_path_policy']
    output_path_nonpolicy = config['output_path_nonpolicy']

    try:
        result = download_text(policy_url, app_id, output_path_policy, output_path_nonpolicy)
        if result:
            print(f'Processing app:{app_id}, its url {policy_url} is a policy page')
        else:
            print(f'Processing app:{app_id}, its url {policy_url} may NOT be a policy page')
        results.append(result)
    except Exception as e:
        print("Error occurred when processing document", app_id)
        print("The error is: ", e)

end_time = time.time()
elapsed_time = end_time - start_time
print(f'Total time:{elapsed_time} seconds')
print(results)
