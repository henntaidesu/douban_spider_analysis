import sys
import threading
import time
from datetime import datetime
import selenium.webdriver.support.wait
import selenium.common.exceptions
from src.module.execution_db import DB
from src.module.log import Log, err2
from src.module.web_drive import webserver
from src.module.now_time import now_time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = Log()


def get_personnel():
    driver, expire_time = webserver()
    try:
        while True:
            sql = f"SELECT movie_ID FROM douban_index WHERE `status` = '0'  ORDER BY movie_ID LIMIT 1"
            flag, data = DB().select(sql)
            if data:
                ID = data[0][0]
                # ID = 26363254
                url = f"https://movie.douban.com/subject/{ID}/celebrities"
            else:
                driver.close()
                driver.quit()
                time.sleep(3600)
                get_personnel()

            try:
                if expire_time < now_time():
                    driver.close()
                    driver.quit()
                    get_personnel()
                try:
                    driver.get(url)

                    title = driver.title

                    if title == '豆瓣 - 登录跳转页':
                        logger.write_log(f"----- 代理错误 -----", 'error')
                        driver.close()
                        driver.quit()
                        get_personnel()

                except (selenium.common.exceptions.TimeoutException, selenium.common.exceptions.WebDriverException):
                    logger.write_log(f"浏览器开启超时", 'error')
                    driver.close()
                    driver.quit()
                    get_personnel()

            except ExceptionGroup as e:
                logger.write_log(e, 'error')

            try:
                article_type_list = WebDriverWait(driver, 2).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, 'list-wrapper')))
            except selenium.common.exceptions.TimeoutException:
                try:
                    article_type_list = WebDriverWait(driver, 2).until(
                        EC.presence_of_all_elements_located((By.XPATH, '//*[@id="content"]/h1')))
                    if article_type_list:
                        logger.write_log(f'{ID} - 无演员表', 'warning')

                        sql = f"UPDATE `Movie`.`douban_index` SET `status` = 'a' WHERE `movie_ID` = {ID}"
                        DB().update(sql)
                        continue
                except (selenium.common.exceptions.TimeoutException, IndexError):
                    logger.write_log(f'浏览器加载错误', 'error')
                    driver.close()
                    driver.quit()
                    get_personnel()

                except Exception as e:
                    logger.write_log(e, 'error')

            for article_list in article_type_list:
                personnel_class = article_list.find_element(By.TAG_NAME, 'h2').text
                personnel_name_list = article_list.find_elements(By.CLASS_NAME, 'name')
                personnel_works_list = article_list.find_elements(By.CLASS_NAME, 'works')
                personnel_position_list = article_list.find_elements(By.CLASS_NAME, 'role')

                p_name_list = []
                name_list = []
                name_ID_list = []

                for personnel_name in personnel_name_list:
                    name = personnel_name.text
                    name_ID = personnel_name.get_attribute('href')
                    if name_ID is None:
                        continue
                    else:
                        name_ID = name_ID[name_ID.rfind('/', 0, name_ID.rfind('/')):].replace('/', '')
                        name_list.append(name)
                        name_ID_list.append(name_ID)

                aaa_list = []
                for i in range(len(name_list)):
                    position_type = None
                    position_name = None
                    # works = personnel_works_list[i].text
                    try:
                        position = personnel_position_list[i].text
                        if "(" in position:
                            position_type = position[:position.find('(')].rstrip().lstrip()
                            position_name = position[position.find('('):]
                            if '饰' in position_name:
                                position_name = position_name[position_name.find('饰') + 1:][: -1].rstrip().lstrip()
                                if '(' in position_name:
                                    position_name = position_name.replace('(', '')

                            elif '配' in position_name:
                                position_name = position_name[position_name.find('配') + 1:].rstrip().lstrip()
                                if ')' in position_name:
                                    position_name = position_name.replace(')', '')

                        else:
                            position_type = position
                    except IndexError:
                        position_type = personnel_class

                    except Exception as e:
                        logger.write_log(e, 'error')

                    name = name_list[i]
                    name_ID = name_ID_list[i]
                    if name:
                        name = name.replace("'", r"\'")
                    if position_name:
                        position_name = position_name.replace("'", r"\'")
                    if personnel_class:
                        personnel_class = personnel_class.replace("'", r"\'")
                    sql = (f"INSERT INTO `Movie`.`douban_personnel` "
                           f"(`movie_ID`, `personnel_class`, `position_type`, `position_name`, `name`, `name_ID`) "
                           f"VALUES ({ID}, '{personnel_class}', '{position_type}', '{position_name}', '{name}', '{name_ID}');")
                    DB().insert(sql)
                    logger.write_log(f"已获取人员 - {personnel_class} - {position_type} - {position_name} - {name} - {name_ID}","info")

            sql = f"UPDATE `Movie`.`douban_index` SET `status` = '1' WHERE `movie_ID` = {ID}"
            DB().update(sql)


    except KeyboardInterrupt:
        if driver:
            driver.close()
            driver.quit()
            sys.exit()

    except ExceptionGroup as e:
        logger.write_log(e, 'error')