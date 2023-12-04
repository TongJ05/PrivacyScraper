import pandas as pd

def get_website_list(csv_file_path, policy_col_name, appid_col_name):
    """
    Read the input csv file and convert it to a list for main function
    Returned list is [(url_1, appid_1), (url_2, appid_2), ...]
    """
    df = pd.read_csv(csv_file_path)
    result_list = []

    for _, row in df.iterrows():
        url = row[policy_col_name]
        app_id = row[appid_col_name]
        result_list.append((url, app_id))

    return result_list
