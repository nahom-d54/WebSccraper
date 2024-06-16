import random, requests
import requests
import random
import concurrent.futures
import time
import urllib3
import json
import os
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Proxy:
    format = {'http': '', 'https': ''}
    
    types = {2: 'https', 1: 'http', 4: 'socks5', 3: 'socks4'}

    proxy_file = 'working_proxies.json'
    max_age_hours = 1


    def __init__(self) -> None:
        if self.load_proxies():
            print("Loaded proxies from file.")
        else:
            today = datetime.today()
            plist = []
            for d in range(3):
                t = today - timedelta(days=d)
                f = t.strftime('%Y-%m-%d')
                url = f"https://checkerproxy.net/api/archive/{f}"

                plist += requests.get(url).json()

            # Filter out proxies with a timeout greater than 10 seconds and type 1 (http)
            self.proxy_list = list(filter(lambda item: item['type'] != 1, plist))
            
            # Check the proxies and keep only the working ones
            self.proxy_list = self.check_proxies_concurrently(self.proxy_list, max_workers=int(len(self.proxy_list) / 10))

            self.save_proxies()

    def get_random_proxy(self):
        choice = random.choice(self.proxy_list)
        toreturn = self.format
        toreturn['http'] = self.types[choice['type']] + "://" + choice['addr']
        toreturn['https'] = self.types[choice['type']] + "://" + choice['addr']
        return toreturn
    
    def remove_dead(self, addr):
        self.proxy_list = list(filter(lambda proxy: proxy.get('addr') != addr, self.proxy_list))

    def check_proxy(self, proxy):
        test_url = 'http://httpbin.org/ip'
        proxies = {
            'http': self.types[proxy['type']] + "://" + proxy['addr'],
            'https': self.types[proxy['type']] + "://" + proxy['addr'],
        }
        try:
            response = requests.get(test_url, proxies=proxies, timeout=10, verify=False)
            response.raise_for_status()
            proxy['timeout'] = response.elapsed.seconds
            #print(f"Proxy {proxy['addr']} is working. Response: {response.json()}")
            return proxy
        except requests.RequestException as e:
            print(f"Proxy {proxy['addr']} failed. Error: {e}")
            return None

    def check_proxies_concurrently(self, proxy_list, max_workers=20):
        working_proxies = []
        total = len(proxy_list)
        completed = 0
        def print_progress(completed, total):
            progress = int((completed / total) * 100)
            bar = '#' * (progress // 2) + '-' * (50 - (progress // 2))
            print(f"\rChecking proxies: [{bar}] {progress}% : success: {len(working_proxies)}", end='')
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.check_proxy, proxy): proxy for proxy in proxy_list}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    working_proxies.append(result)

                completed += 1
                print_progress(completed, total)
        return working_proxies
    def save_proxies(self):
        with open(self.proxy_file, 'w') as f:
            json.dump({'timestamp': datetime.now().isoformat(), 'proxies': self.proxy_list, 'count': len(self.proxy_list)}, f)

    def load_proxies(self):
        if not os.path.exists(self.proxy_file):
            return False

        with open(self.proxy_file, 'r') as f:
            data = json.load(f)
            timestamp = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - timestamp < timedelta(hours=self.max_age_hours):
                self.proxy_list = data['proxies']
                return True

        return False