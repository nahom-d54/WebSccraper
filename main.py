import requests
from fake_headers import Headers
from bs4 import BeautifulSoup as bs
from proxy import Proxy
import time
import urllib3
import concurrent.futures
import csv


import os
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


header = Headers().generate()
header['Referer'] = 'https://www.google.com/'
property_list_parsed = []
url = "https://www.habitaclia.com/alquiler-viviendas-particulares-barcelona.htm"

has_next = True
count = 0
error = 0

proxyobj = Proxy()
def get_response_with_retry(url, headers, max_retries=100, delay=2, referer= None):
    retries = 0
    while retries < max_retries:
        proxy = proxyobj.get_random_proxy()
        if referer:
            header['Referer'] = referer
        try:
            response = requests.get(url, headers=headers, verify=False, proxies=proxy)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            return response
        except requests.RequestException as e:
            #print(f"Request failed: . Retrying ({retries + 1}/{max_retries})...")
            retries += 1
            # proxyobj.remove_dead(proxy['http'])
    return None


while has_next:
    if count > 0:
        url = f"https://www.habitaclia.com/alquiler-viviendas-particulares-barcelona-{count}.htm"
    response = get_response_with_retry(url, header)
    if response:
        soup = bs(response.text, 'lxml')
        try:
            property_list = soup.find('main').find('section', class_="list-items-container").find('section', class_="list-items").find_all('article', class_="list-item-container")
            nav = soup.find('main').find(id='js-nav').find('ul').find_all('li')
            has_next = False
            for li in nav:
                if 'next' in li.get('class', []):
                    has_next = True
                    count += 1
                    break
        except:
            print(url)
            continue

        property_list_urls = [u['data-href'] for u in property_list]

        completed = 0
        total = len(property_list_urls)
        def print_progress(completed, total):
            progress = int((completed / total) * 100)
            bar = '#' * (progress // 2) + '-' * (50 - (progress // 2))
            print(f"\rChecking pages: [{bar}] {progress}% : success: {len(property_list_parsed)}: page {count}", end='')

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(get_response_with_retry, property_url, header, referer = url): property_url for property_url in property_list_urls}
                for future in concurrent.futures.as_completed(futures):
                    property_response = future.result()
                    if property_response:
                        item = {"title": "", "price": "", "street": "", "meters": "", "rooms": "", "toilets": ""}

                        isoup = bs(property_response.text, 'lxml')
                        try:
                            iraw = isoup.find('main').find('div', class_="content-detail-filter")
                            summery = iraw.find('section', class_='summary')
                            detail = iraw.find('section', class_='detail')
                            item['price'] = summery.find('div', class_='price').find('span').text.strip('\r\n ')
                            location = summery.find('article', class_='location').find('h4').find_all(string=True)
                            item['street'] = ''.join([l.strip('\r\n- ') for l in location])
                            meta = summery.find(id='js-feature-container').find('ul', class_='feature-container').find_all('li', class_='feature')

                            item['meters'] = meta[0].text.strip('\r\n ')
                            item['rooms'] = meta[1].text.strip('\r\n ')
                            item['toilets'] = meta[2].text.strip('\r\n ')
                            item['title'] = summery.find('h1').text.strip('\r\n ')

                            property_list_parsed.append(item)
                            #print(f"\rsuccess: {len(property_list_parsed)} error: { error }", end='')
                            completed += 1
                            print_progress(completed, total)
                        except Exception as e:
                            #print(e)
                            pass



csv_file = f'properties-{int(time.time())}.csv'
# Get the keys from the first dictionary to use as the header row
keys = property_list_parsed[0].keys()

# Write the data to a CSV file
with open(csv_file, 'w', newline='') as output_file:
    dict_writer = csv.DictWriter(output_file, fieldnames=keys)
    dict_writer.writeheader()
    dict_writer.writerows(property_list_parsed)

print(f"Data has been written to {csv_file}")