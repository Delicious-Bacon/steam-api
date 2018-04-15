import logging
import pathlib
import time

from app_details_utils import load_app_details
from steam_catalog_utils import load_steam_catalog


def get_previously_seen_app_ids_of_games():
    return 'successful_appIDs.txt'


def get_previously_seen_app_ids_of_non_games():
    return 'faulty_appIDs.txt'


def load_text_file(file_name):
    try:
        with open(file_name, "r") as f:
            file_content = [line.strip() for line in f]
    except FileNotFoundError:
        file_content = []
        pathlib.Path(file_name).touch()
    return file_content


def load_previously_seen_app_ids():
    previously_seen_app_ids = set()

    success_filename = get_previously_seen_app_ids_of_games()
    error_filename = get_previously_seen_app_ids_of_non_games()

    for appid_log_file_name in [success_filename, error_filename]:
        parsed_app_ids = load_text_file(appid_log_file_name)
        previously_seen_app_ids = previously_seen_app_ids.union(parsed_app_ids)

    return previously_seen_app_ids


def scrape_steam_data():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('requests').setLevel(logging.DEBUG)
    log = logging.getLogger(__name__)

    query_rate_limit = 200  # Number of queries which can be successfully issued during a 4-minute time window
    wait_time = (4 * 60) + 10  # 4 minutes plus a cushion
    successful_status_code = 200  # Status code for a successful HTTP response

    query_count = 0

    (steam_catalog, is_success, query_status_code) = load_steam_catalog()

    assert is_success
    if query_status_code is not None:
        query_count += 1

    all_app_ids = list(steam_catalog.keys())

    previously_seen_app_ids = load_previously_seen_app_ids()

    unseen_app_ids = set(all_app_ids).difference(previously_seen_app_ids)

    success_filename = get_previously_seen_app_ids_of_games()
    error_filename = get_previously_seen_app_ids_of_non_games()

    for appID in unseen_app_ids:

        if query_count >= query_rate_limit:
            log.info("query count is %d ; limit %d reached. Wait for %d sec", query_count, query_rate_limit, wait_time)
            time.sleep(wait_time)
            query_count = 0

        (app_details, is_success, query_status_code) = load_app_details(appID)
        if query_status_code is not None:
            query_count += 1

        while (query_status_code is not None) and (query_status_code != successful_status_code):
            log.info("query count is %d ; HTTP response %d. Wait for %d sec", query_count, query_status_code, wait_time)
            time.sleep(wait_time)
            query_count = 0

            (app_details, is_success, query_status_code) = load_app_details(appID)
            if query_status_code is not None:
                query_count += 1

        appid_log_file_name = success_filename
        if (query_status_code is not None) and not is_success:
            assert (query_status_code == successful_status_code)
            appid_log_file_name = error_filename

        with open(appid_log_file_name, "a") as f:
            f.write(appID + '\n')


if __name__ == '__main__':
    scrape_steam_data()
