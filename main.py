from pathlib import Path

import requests
from lxml import etree


headers = {
    'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
}
meta_url = "https://pypi.org/"
search_url = "https://pypi.org/search/?q"


def init_save_path(save_path="."):
    """ 初始化下载环境 """
    source_path = Path(save_path)
    save_path = source_path / 'whls'
    if not save_path.exists():
        save_path.mkdir()
    return save_path


def load_whl_info(packages_path: str):
    with open(packages_path, "r") as fr:
        whl_info = fr.read()
    return whl_info


def init_download_packages(whl_info: str):
    """ 处理输入 """
    need_packages = []
    package_info = [i.strip() for i in whl_info.split("\n") if i.strip()]
    whl_name = ""
    version = ""
    for i in package_info:
        whl_name = i
        if "==" in i:
            whl_name, version = i.split("==")
        need_packages.append((whl_name, version))
    return need_packages


def pypi_spider(save_path, need_packages: list, error_package: list = []):
    """ pypi镜像包爬虫
    need_packages: 需要下载的包
    error_package: 下载中出错的包
    """
    for idx, package_info in enumerate(need_packages, 1):
        search_content = package_info[0]
        version = package_info[1]
        print('需要下载的包信息', package_info)
        response = requests.get(
            f'{search_url}={search_content}', headers=headers)
        html_str = response.content.decode('utf-8')
        html = etree.HTML(html_str)

        search_results = html.xpath(
            '//*[@id="content"]/div/div/div[2]/form/div[3]/ul/*')
        result_url = ''
        for result in search_results:
            result_href = result.xpath('./a/@href')[0]
            result_name = result.xpath('./a/h3/span[1]')[0].text
            result_version = result.xpath('./a/h3/span[2]')[0].text
            if result_name == search_content:
                result_url = f'{meta_url}{result_href}#files'
                break
            elif result_name == search_content.capitalize() and len(result_name) == len(search_content):
                result_url = f'{meta_url}{result_href}#files'
                break
            elif '-' in search_content and search_content.replace('-', '_') == result_name and len(result_name) == len(search_content):
                result_url = f'{meta_url}{result_href}#files'
                break
        if version:
            result_url = f'{meta_url}{result_href}{version}/#files'
            print(f'开始准备下载 {result_name} {version}')
        else:
            print(f'开始准备下载 {result_name} {result_version}')
        if not result_url:
            error_package.append(search_content)
            continue
        # get download url
        response = requests.get(result_url, headers=headers)
        result_html_str = response.content.decode('utf-8')
        result_html = etree.HTML(result_html_str)
        result_download_nodes = result_html.xpath(
            '//*[@id="files"]/table/tbody/tr')

        win32_info = None  # 相同版本的win32包
        for result_download in result_download_nodes:
            file_type = result_download.xpath(
                './td[1]/text()')[1].replace(" ", '').replace('\n', '')
            download_version = result_download.xpath(
                './td[2]/text()')[1].replace(" ", '').replace('\n', '')
            download_href = result_download.xpath('./th/a/@href')[0]
            whl_name = result_download.xpath(
                './th/a/text()')[0].replace(" ", '').replace('\n', '')
            whl_size = result_download.xpath(
                './th/text()')[2].replace(" ", '').replace('\n', '')

            # 下载版本判断
            if download_version == 'cp37' and 'win32' in whl_name:
                win32_info = (whl_name, download_href)
            if download_version == 'py2.py3' and 'py2.py3-none-any' in whl_name:  # 准确下载python3的版本
                break
            elif download_version == 'cp37' and 'win_amd64' in whl_name:  # 准确下载python3.7 win64的版本
                # 查看是否有win32的包，并且下载
                if win32_info:
                    print(f'{search_content}的win32版本下载链接', win32_info)
                    file_name = save_path / win32_info[0]
                    file_content = requests.get(win32_info[1], headers=headers)
                    with open(file_name.absolute(), 'wb') as f:
                        f.write(file_content.content)
                break
            elif 'py3' in download_version or download_version == 'None':  # 下载通用版本
                break
        # 下载
        file_name = save_path / whl_name
        file_content = requests.get(download_href, headers=headers)
        with open(file_name.absolute(), 'wb') as f:
            f.write(file_content.content)

        print(f'{search_content}{whl_size} 版本{download_version} 类型{file_type} -- 下载成功')
        if len(need_packages) == idx:
            print('此次任务结束')
    if error_package:
        print('此次任务下载失败的包如下:')
        for idx, error_ in enumerate(error_package, 1):
            print(f'{idx}: {error_}')
    return error_package


def show_help():
    print("choose which source you need to download")
    url_info = """
    +++++++++COMMANDS++++++++++
    1:\t\tpypi.org
    2:\t\tdouban
    3:\t\taliyun
    +++++++++++++++++++++++++++
    """
    print(url_info)


def main_loop():
    packages_path = input(">>> input packages path: ").strip()
    if not packages_path:
        print("not found")
        return
    whl_info = load_whl_info(packages_path)
    need_packages = init_download_packages(whl_info)
    input_path = input(">>> input save path: ").strip()
    input_path = "." if not input_path else input_path
    save_path = init_save_path(input_path)
    show_help()
    choose = input(">>> ")
    if choose == "1":
        pypi_spider(save_path, need_packages)


if __name__ == "__main__":
    main_loop()
