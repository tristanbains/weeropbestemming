# Custom code:
from python_code.download import *
# import threading
# from python_code.preprocess import *

# df_destinations = xlsx_sheet_to_df(filename=r'./data/vakantieweer_destinations.xlsx',sheetname='Destinations')
df_destinations = xlsx_add_latlon(filename=r'./data/destinations.xlsx',sheetname='Destinations')
dict_destinations = create_dict_destinations(df_destinations)

# Update raw data:
# start = datetime(2018,1,1)
# end = datetime.today()
folder_data_processed = './data/processed'
last_n_years = 7

# for country in dict_destinations:
    
#     # Create CSV's per country-place-month:
#     for place in dict_destinations[country]:
#         print(f'{country}, {place}')
        # df_cp_d = download_add_daily(country,place,dict_destinations,last_n_years=last_n_years)
        # if df_cp_d is not None:
        #     dfs_daily = preprocess_daily(df_cp_d)
        #     dictdfs_write_csv(dfs_daily,country,place,folder_data_processed)
#         df_cp_h = download_add_hourly(country,place,dict_destinations,last_n_years=last_n_years)
#         if df_cp_h is not None:
#             dfs_hourly = preprocess_hourly(df_cp_h)
#             dictdfs_write_csv(dfs_hourly,country,place,folder_data_processed)
    
#     # Create CSV's per country-place-month:
#     dict_dfs_country = combine_csvs_country(country=country,folder_data_processed=folder_data_processed)
#     dictdfs_write_csv(dict_dfs_country,country,place=None,folder_data_processed=folder_data_processed)
    

import threading
import time

def process_daily_data_with_timeout(country, place, dict_destinations, last_n_years, timeout=30):
    result = None
    stop_thread = threading.Event()
    def worker():
        nonlocal result
        try:
            df_cp_d = download_add_daily(country, place, dict_destinations, last_n_years=last_n_years)
            if df_cp_d is not None:
                dfs_daily = preprocess_daily(df_cp_d)
                dictdfs_write_csv(dfs_daily, country, place, folder_data_processed)
            result = True  # Indicate success
        except Exception as e:
            print(f"Error in thread for {country}, {place}: {e}")
            result = False
        finally:
            stop_thread.set()
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print(f"Timeout: Processing daily data for {country}, {place} did not finish within {timeout} seconds.")
        stop_thread.set()  # Signal the thread to stop
        thread.join()  # Wait for the thread to finish (gracefully)
    return result


def process_hourly_data_with_timeout(country, place, dict_destinations, last_n_years, timeout=30):
    result = None
    stop_thread = threading.Event()
    def worker():
        nonlocal result
        try:
            df_cp_h = download_add_hourly(country, place, dict_destinations, last_n_years=last_n_years)
            if df_cp_h is not None:
                dfs_hourly = preprocess_hourly(df_cp_h)
                dictdfs_write_csv(dfs_hourly, country, place, folder_data_processed)
            result = True  # Indicate success
        except Exception as e:
            print(f"Error in thread for {country}, {place}: {e}")
            result = False
        finally:
            stop_thread.set()
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print(f"Timeout: Processing hourly data for {country}, {place} did not finish within {timeout} seconds.")
        stop_thread.set()  # Signal the thread to stop
        thread.join()  # Wait for the thread to finish (gracefully)
    return result




for country in dict_destinations:

    threads=[]
    # Create CSV's per country-place-month:
    for place in dict_destinations[country]:
        print(f'{country}, {place}')
        
        daily_thread = threading.Thread(target=process_daily_data_with_timeout, 
                                        args=(country, place, dict_destinations, last_n_years))
        daily_thread.start()
        threads.append(daily_thread)

        hourly_thread = threading.Thread(target=process_hourly_data_with_timeout, 
                                         args=(country, place, dict_destinations, last_n_years))
        hourly_thread.start()
        threads.append(hourly_thread)
        
        # # Process daily data in a separate thread with timeout
        # if process_daily_data_with_timeout(country, place, dict_destinations, last_n_years):
        #     print(f"Daily data processing for {country}, {place} completed successfully.")
        # else:
        #     print(f"Daily data processing for {country}, {place} failed or timed out.")
        # df_cp_d = download_add_daily(country,place,dict_destinations,last_n_years=last_n_years)
        # if df_cp_d is not None:
        #     dfs_daily = preprocess_daily(df_cp_d)
        #     dictdfs_write_csv(dfs_daily,country,place,folder_data_processed)
        # if process_hourly_data_with_timeout(country, place, dict_destinations, last_n_years):
        #     print(f"Hourly data processing for {country}, {place} completed successfully.")
        # else:
        #     print(f"Hourly data processing for {country}, {place} failed or timed out.")

        # df_cp_h = download_add_hourly(country,place,dict_destinations,last_n_years=last_n_years)
        # if df_cp_h is not None:
        #     dfs_hourly = preprocess_hourly(df_cp_h)
        #     dictdfs_write_csv(dfs_hourly,country,place,folder_data_processed)
    
    for thread in threads:
        thread.join()
    # Create CSV's per country-place-month:
    dict_dfs_country = combine_csvs_country(country=country,folder_data_processed=folder_data_processed)
    dictdfs_write_csv(dict_dfs_country,country,place=None,folder_data_processed=folder_data_processed)