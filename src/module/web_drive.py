from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from src.module.log import err2
from src.module.read_conf import ReadConf
from src.module.proxy_pool import get_new_proxy


def webserver():
    ID = None
    proxy_flag = False
    proxy_ID = None
    try:
        desired_capabilities = DesiredCapabilities.CHROME
        desired_capabilities["pageLoadStrategy"] = "none"
        options = webdriver.ChromeOptions()
        # 设置浏览器不加载图片，提高速度
        options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        options.add_argument("--disable-gpu")
        options.add_argument('--log-level=3')  # 设置日志级别减少输出信息
        options.add_argument('--silent')  # 禁止 DevTools 输出
        options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 禁用 DevTools 监听输出

        # options.add_argument('--headless')  # 不唤起实体浏览器

        proxy_flag = ReadConf().proxy_pool()
        if proxy_flag:
            proxy = Proxy()
            proxy_url, expire_time = get_new_proxy()
            proxy.proxy_type = ProxyType.MANUAL
            proxy.http_proxy = proxy_url
            proxy.ssl_proxy = proxy_url
            options.add_argument(f"--proxy-server={proxy_url}")
        else:
            expire_time = '2099-01-01 00:00:00'
        driver = webdriver.Chrome(service=ChromeService(r"chromedriver.exe"), options=options)
        driver.set_page_load_timeout(60)
        return driver, expire_time
    except Exception as e:
        err2(e)
