import requests
import functools
import shutil
import codecs
import sys
import os
from collections.abc import Mapping, MutableMapping
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

url = "https://google.com"
use_tor_network = False

if len(sys.argv) > 1:
    url = sys.argv[1]
output_folder = urlparse(url).netloc

session = requests.session()
if use_tor_network:
    session.request = functools.partial(session.request, timeout=30)
    session.proxies = {'http':  'socks5h://localhost:9050',
                        'https': 'socks5h://localhost:9050'}

workspace = os.path.dirname(os.path.realpath(__file__))

class Extractor:
    def __init__(self, url):
        self.url = url
        self.soup = BeautifulSoup(self.get_page_content(url), "html.parser")
        self.scraped_urls = self.scrap_all_urls()
    
    def run(self):
        self.save_files(self.scraped_urls)
        self.save_html()
    
    def get_page_content(self, url):
        try: 
            content = session.get(url)
            content.encoding = 'utf-8'
            return content.text
        except Exception as e:
            print(f"Failed to retrieve page content: {e}")
            return None

    def scrap_scripts(self):
        script_urls = []
        for script_tag in self.soup.find_all("script"):
            script_url = script_tag.attrs.get("src")
            if script_url:
                if not script_url.startswith('http'):
                    script_url = urljoin(self.url, script_url)
                new_url = self.url_to_local_path(script_url, keepQuery=True)
                if new_url:
                    script_tag['src'] = new_url
                    script_urls.append(script_url.split('?')[0])
        return list(dict.fromkeys(script_urls))

    def scrap_form_attr(self):
        urls = []
        for form_tag in self.soup.find_all("form"):
            form_url = form_tag.attrs.get("action")
            if form_url:
                if not form_url.startswith('http'):
                    form_url = urljoin(self.url, form_tag.attrs.get("action"))
                new_url = self.url_to_local_path(form_url, keepQuery=True)
                if new_url:
                    form_tag['action'] = new_url
                    urls.append(form_url.split('?')[0])
        return list(dict.fromkeys(urls))

    def scrap_a_attr(self):
        urls = []
        for link_tag in self.soup.find_all('a'):
            link_url = link_tag.attrs.get('href')
            if link_url:
                if not link_url.startswith('http'):
                    link_url = urljoin(self.url, link_tag.attrs.get('href'))
                new_url = self.url_to_local_path(link_url, keepQuery=True)
                if new_url:
                    link_tag['href'] = new_url
                    urls.append(link_url.split('?')[0])
        return list(dict.fromkeys(urls))

    def scrap_img_attr(self):
        urls = []
        for img_tag in self.soup.find_all('img'):
            img_url = img_tag.attrs.get('src')
            if img_url:
                if not img_url.startswith('http'):
                    img_url = urljoin(self.url, img_tag.attrs.get('src'))
                new_url = self.url_to_local_path(img_url, keepQuery=True)
                if new_url:
                    img_tag['src'] = new_url
                    urls.append(img_url.split('?')[0])
        return list(dict.fromkeys(urls))

    def scrap_link_attr(self):
        urls = []
        for link_tag in self.soup.find_all('link'):
            link_url = link_tag.attrs.get('href')
            if link_url:
                if not link_url.startswith('http'):
                    link_url = urljoin(self.url, link_tag.attrs.get('href'))
                new_url = self.url_to_local_path(link_url, keepQuery=True)
                if new_url:
                    link_tag['href'] = new_url
                    urls.append(link_url.split('?')[0])
        return list(dict.fromkeys(urls))

    def scrap_btn_attr(self):
        urls = []
        for buttons in self.soup.find_all('button'):
            button_url = buttons.attrs.get('onclick')
            if button_url:
                button_url = button_url.replace(' ','')
                button_url = button_url[button_url.find('location.href='):].replace('location.href=','')
                button_url = button_url.replace('\'', '')
                button_url = button_url.replace('\"', '')
                button_url = button_url.replace('`', '')
                if button_url and button_url.startswith('/'):
                    if not button_url.startswith('http'):
                        button_url = urljoin(self.url, buttons.get('onclick'))
                    new_url = self.url_to_local_path(button_url, keepQuery=True)
                    if new_url:
                        buttons['onclick'] = new_url
                        urls.append(button_url.split('?')[0])
        return list(dict.fromkeys(urls))

    def scrap_assets(self):
        assets_urls = []
        form_attr = self.scrap_form_attr()
        a_attr = self.scrap_a_attr()
        img_attr = self.scrap_img_attr()
        link_attr = self.scrap_link_attr()
        btn_attr = self.scrap_btn_attr()
        
        if form_attr: assets_urls.extend(form_attr)
        if a_attr: assets_urls.extend(a_attr)
        if img_attr: assets_urls.extend(img_attr)
        if link_attr: assets_urls.extend(link_attr)
        if btn_attr: assets_urls.extend(btn_attr)

        return list(dict.fromkeys(assets_urls))

    def scrap_all_urls(self):
        urls = []
        urls.extend(self.scrap_scripts())
        urls.extend(self.scrap_assets())
        return list(dict.fromkeys(urls))
    
    def url_to_local_path(self, url, keepQuery=False):
        try:
            new_url = urlparse(url).path
            query = urlparse(url).query
            if keepQuery and query:
                new_url += '?' + query
            if (new_url[0] == '/') or (new_url[0] == '\\'):
                new_url = new_url[1:]
        except Exception as e:
            print(f"Error parsing URL to path: {e}")
            return None
        return new_url

    def download_file(self, url, output_path):
        if not url or not urlparse(url).scheme:
            print(f"Skipping invalid URL: {url}")
            return False

        url = url.split('?')[0]
        file_name = url.split('/')[-1]

        if len(file_name) == 0:
            return False

        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not file_name:
            print(f"Skipping directory path: {output_path}")
            return False

        try:
            response = session.get(url)
            with open(output_path, "wb") as file:
                file.write(response.content)
                print(f"Downloaded {file_name} to {os.path.relpath(output_path)}")
        except Exception as e:
            print(f"Failed to download {url}. Error: {e}")
            return False

        return True

    def save_files(self, urls):
        shutil.rmtree(os.path.join(workspace, output_folder), ignore_errors=True)
        for url in urls:
            output_path = self.url_to_local_path(url, keepQuery=False)
            if output_path:
                output_path = os.path.join(workspace, output_folder, output_path)
                self.download_file(url, output_path)
        return True
    
    def save_html(self):
        output_path = os.path.join(workspace, output_folder, 'index.html')
        prettyHTML = self.soup.prettify()
        try:
            with codecs.open(output_path, 'w', 'utf-8') as file:
                file.write(prettyHTML)
                print(f"Saved index.html to {os.path.relpath(output_path)}")
        except Exception as e:
            print(f"Failed to save HTML file. Error: {e}")
        return True

extractor = Extractor(url)

print(f"Extracting files from {url}\n")
extractor.run()
print(f"\nTotal extracted files: {len(extractor.scraped_urls)}")
