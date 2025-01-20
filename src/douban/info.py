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


def exhaustive_ID():
    sql = f"SELECT `movie_ID` FROM `douban_index` ORDER BY `movie_ID`  DESC limit 1"
    flag, ID = DB().select(sql)
    ID = int(ID[0][0])
    driver, expire_time = webserver()
    name = None
    while True:
        try:
            if expire_time < now_time():
                driver.close()
                driver.quit()
                exhaustive_ID() 

            ID -= 1
            url = f"https://movie.douban.com/subject/{ID}/"
            # url = f'https://movie.douban.com/subject/1864790/'、
            try:
                driver.get(url)
            except (selenium.common.exceptions.TimeoutException, selenium.common.exceptions.WebDriverException):
                logger.write_log(f"浏览器开启超时", 'error')
                driver.close()
                driver.quit()
                exhaustive_ID()
            except Exception as e:
                logger.write_log(e, 'error')

            title = driver.title

            if title == '页面不存在' or title == '豆瓣电影' or title == '条目不存在':
                logger.write_log(f"非法ID - {ID}", 'warning')
                sql = f"INSERT INTO `douban_index` (`movie_ID`) VALUES ({ID});"
                DB().insert(sql)
                continue
            elif title == '豆瓣 - 登录跳转页':
                logger.write_log(f"----- 代理错误 -----", 'error')
                driver.close()
                driver.quit()
                exhaustive_ID()
            else:
                if '(豆瓣)' in title:
                    title = title.replace('(豆瓣)', '').lstrip().rstrip()

                try:
                    name = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="content"]/h1/span[1]'))).text
                except selenium.common.exceptions.TimeoutException:
                    time.sleep(30)
                    driver.close()
                    driver.quit()
                    exhaustive_ID()

            try:
                introduction = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.ID, 'link-report-intra'))).text.replace(' ©豆瓣', '')
                introduction = introduction.replace("'", r"\'")
            except selenium.common.exceptions.TimeoutException:
                introduction = None
            title = title.replace("'", r"\'")
            name = name.replace("'", r"\'")

            if 'Season' in name:
                season = name[name.find('Season') + 7:]
            else:
                season = None

            sql = (f"INSERT INTO `douban_index` (`movie_ID`, `title`, `introduction`, `status`, `name`, `season`) "
                   f"VALUES  ({ID}, '{title}', '{introduction}', '0', '{name}', '{season}');")
            DB().insert(sql)

            thread1 = threading.Thread(target=get_director(driver, ID))
            thread2 = threading.Thread(target=get_screenwriter(driver, ID))
            thread3 = threading.Thread(target=get_starring(driver, ID))
            thread4 = threading.Thread(target=get_info(driver, ID))
            thread5 = threading.Thread(target=get_star(driver, ID))
            thread1.start()
            # thread2.start()
            # thread3.start()
            thread4.start()
            thread5.start()

            logger.write_log(f"已获取电影 - {title} - ID - {ID}", 'info')

            sql = f'DELETE FROM `douban_index` WHERE `name` IS NULL '
            DB().delete(sql)

        except selenium.common.exceptions.TimeoutException:
            driver.close()
            driver.quit()
            exhaustive_ID()

        except KeyboardInterrupt:
            driver.close()
            driver.quit()


def get_star(driver, ID):
    try:
        total_star = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="interest_sectl"]/div[1]/div[2]/strong'))).text

        star1 = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="interest_sectl"]/div[1]/div[3]/div[5]/span[2]'))).text.replace('%', '')

        star2 = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="interest_sectl"]/div[1]/div[3]/div[4]/span[2]'))).text.replace('%', '')

        star3 = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="interest_sectl"]/div[1]/div[3]/div[3]/span[2]'))).text.replace('%', '')

        star4 = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="interest_sectl"]/div[1]/div[3]/div[2]/span[2]'))).text.replace('%', '')

        star5 = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="interest_sectl"]/div[1]/div[3]/div[1]/span[2]'))).text.replace('%', '')

        star_number = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="interest_sectl"]/div[1]/div[2]/div/div[2]/a/span'))).text

        sql = f"UPDATE `douban_index` SET `star` = '{total_star}' WHERE `movie_ID` = {ID}"
        DB().update(sql)
        sql = (f"INSERT INTO `douban_star` (`movie_ID`, `star_number`, `5`, `4`, `3`, `2`, `1`) VALUES "
               f"({ID}, {star_number}, '{star5}', '{star4}', '{star3}', '{star2}', '{star1}');")
        DB().insert(sql)
    except selenium.common.exceptions.TimeoutException:
        sql = (f"INSERT INTO `douban_star` (`movie_ID`, `star_number`) VALUES "
               f"({ID}, 0);")
        DB().insert(sql)


def get_director(driver, ID):
    try:
        director = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, f'//*[@id="info"]/span[1]/span[2]/a')))
        director_text = director.text.replace("'", r"\'")

        director_href = director.get_attribute('href')
        director_ID = director_href[director_href.rfind('/', 0, director_href.rfind('/')):].replace('/', '')
        if len(director_ID) > 8:
            director_ID = None
        sql = f"UPDATE `douban_index` SET  `director` = '{director_text}', `director_ID` = '{director_ID}' WHERE `movie_ID` = {ID}"
        DB().update(sql)
    except selenium.common.exceptions.TimeoutException:
        return


def get_screenwriter(driver, ID):
    # 编剧
    i = 0
    screenwriter_list = []
    while True:
        i += 1
        # 导演
        try:
            screenwriter = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="info"]/span[2]/span[2]/a[{i}]')))
            screenwriter_text = screenwriter.get_attribute('text')
            screenwriter_href = screenwriter.get_attribute('href')
            screenwriter_ID = screenwriter_href[screenwriter_href.rfind('/', 0, screenwriter_href.rfind('/')):].replace(
                '/', '')
            screenwriter_list.append([screenwriter_text, screenwriter_ID])
        except selenium.webdriver.support.wait.TimeoutException:
            screenwriter = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="info"]/span[2]/span[2]/a')))
            screenwriter_text = screenwriter.text
            screenwriter_href = screenwriter.get_attribute('href')
            screenwriter_ID = screenwriter_href[screenwriter_href.rfind('/', 0, screenwriter_href.rfind('/')):].replace(
                '/', '')
            screenwriter_list.append([screenwriter_text, screenwriter_ID])
            break
        except (selenium.common.exceptions.InvalidSelectorException, selenium.common.exceptions.TimeoutException):
            break

    screenwriter_list = list({tuple(item): item for item in screenwriter_list}.values())
    print(screenwriter_list)
    return


def get_starring(driver, ID):
    i = 0
    starring_list = []

    while True:
        i += 1
        # 导演
        try:
            starring = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="info"]/span[3]/span[2]/a[{i}')))
            starring_text = starring.get_attribute('text')
            starring_href = starring.get_attribute('href')
            starring_ID = starring_href[starring_href.rfind('/', 0, starring_href.rfind('/')):].replace('/', '')
            starring_list.append([starring_text, starring_ID])
        except selenium.webdriver.support.wait.TimeoutException:
            starring = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="info"]/span[3]/span[2]/a')))
            starring_text = starring.text
            starring_href = starring.get_attribute('href')
            starring_ID = starring_href[starring_href.rfind('/', 0, starring_href.rfind('/')):].replace('/', '')
            starring_list.append([starring_text, starring_ID])
            break
        except (selenium.common.exceptions.InvalidSelectorException, selenium.common.exceptions.TimeoutException):
            break

    if not starring_list:
        i = 0
        while True:
            i += 1
            # 导演
            try:
                starring = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, f'//*[@id="info"]/span[3]/span[2]/span[{i}]/a')))
                starring_text = starring.get_attribute('text')
                starring_href = starring.get_attribute('href')
                starring_ID = starring_href[starring_href.rfind('/', 0, starring_href.rfind('/')):].replace('/', '')
                starring_list.append([starring_text, starring_ID])
            except selenium.webdriver.support.wait.TimeoutException:
                starring = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, f'//*[@id="info"]/span[3]/span[2]/a')))
                starring_text = starring.text
                starring_href = starring.get_attribute('href')
                starring_ID = starring_href[starring_href.rfind('/', 0, starring_href.rfind('/')):].replace('/', '')
                starring_list.append([starring_text, starring_ID])
                break
            except (selenium.common.exceptions.InvalidSelectorException, selenium.common.exceptions.TimeoutException):
                break

    starring_list = list({tuple(item): item for item in starring_list}.values())
    print(starring_list)
    return


def get_info(driver, ID):
    movie_info = WebDriverWait(driver, 2).until(
        EC.presence_of_element_located((By.ID, 'info')))
    movie_info_text = movie_info.text.replace('\\n', '')

    if '类型' in movie_info_text:
        movie_type = movie_info_text[movie_info_text.find('类型: ') + 4:]
        movie_type = movie_type[:movie_type.find('\n')].replace('  ', ' ').replace(' ', '')
        movie_type_list = movie_type.split('/')
        for i in movie_type_list:
            sql = f"INSERT INTO `douban_type` (`movie_ID`, `movie_type`) VALUES ({ID}, '{i}');"
            DB().insert(sql)

    if '制片国家/地区' in movie_info_text:
        movie_county = movie_info_text[movie_info_text.find('制片国家/地区: ') + 9:]
        movie_county = movie_county[:movie_county.find('\n')].replace('  ', ' ').replace(' ', '')
        movie_county_list = movie_county.split('/')
        for i in movie_county_list:
            sql = f"INSERT INTO `douban_county` (`movie_ID`, `county`) VALUES ({ID}, '{i}');"
            DB().insert(sql)

    if '语言' in movie_info_text:
        movie_language = movie_info_text[movie_info_text.find('语言: ') + 4:]
        movie_language = movie_language[:movie_language.find('\n')].replace('  ', ' ').replace(' ', '')
        movie_language_list = movie_language.split('/')
        for i in movie_language_list:
            sql = f"INSERT INTO `douban_language` (`movie_ID`, `language`) VALUES ({ID}, '{i}');"
            DB().insert(sql)

    if '上映日期: ' in movie_info_text:
        movie_release = movie_info_text[movie_info_text.find('上映日期: ') + 6:]
        movie_release = movie_release[:movie_release.find('\n')].replace('  ', ' ').replace(' ', '')
        movie_release_list = movie_release.split('/')
        for i in movie_release_list:
            if '(' in i:
                release = i[:i.find('(')]
                county = i[i.find('(') + 1:].replace(')', '')
            else:
                release = i
                county = None
            sql = f"INSERT INTO `douban_release` (`movie_ID`, `release`, `county`) VALUES ({ID}, '{release}', '{county}');"
            DB().insert(sql)

    else:
        movie_release_list = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, f'//*[@id="content"]/h1/span[2]'))).text

        movie_release_list = movie_release_list[1:][:-1]
        sql = f"INSERT INTO `douban_release` (`movie_ID`, `release`) VALUES ({ID}, '{movie_release_list}');"
        DB().insert(sql)

    if '片长:' in movie_info_text:
        movie_Length_date = movie_info_text[movie_info_text.find('片长: ') + 4:]
        movie_Length_date = movie_Length_date[:movie_Length_date.find('\n')]
        if '分钟' in movie_Length_date:
            movie_Length_date = movie_Length_date.replace('  ', ' ').replace(' ', '').replace(
                '分钟', '')
        elif 'min' in movie_Length_date:
            movie_Length_date = movie_Length_date.replace('min', '').rstrip().lstrip()
        elif '分' in movie_Length_date:
            movie_Length_date = movie_Length_date.replace('分', ',').rstrip().lstrip()
            if '秒' in movie_Length_date:
                movie_Length_date = movie_Length_date.replace('秒', '')
        movie_Length_date = movie_Length_date.replace("'", r"\'")
        sql = f"UPDATE `douban_index` SET `length` = '{movie_Length_date}' WHERE `movie_ID` = {ID}"
        DB().update(sql)

    if '又名: ' in movie_info_text:
        movie_another_name = movie_info_text[movie_info_text.find('又名: ') + 4:]
        movie_another_name = movie_another_name[:movie_another_name.find('\n')].replace('  ', ' ')
        movie_another_name_list = movie_another_name.split('/')
        for i in movie_another_name_list:
            i = i.lstrip().rstrip().replace("'", r"\'")

            sql = f"INSERT INTO `douban_another_name` (`movie_ID`, `another_name`) VALUES ({ID}, '{i}');"
            DB().insert(sql)

    if 'IMDb: ' in movie_info_text:
        movie_IMDb = movie_info_text[movie_info_text.find('IMDb: ') + 6:]
        movie_IMDb = movie_IMDb[:movie_IMDb.find('\n')].replace('  ', ' ')
        sql = f"UPDATE `douban_index` SET `IMDb` = '{movie_IMDb}' WHERE `movie_ID` = {ID}"
        DB().update(sql)

    if '集数' in movie_info_text:
        movie_episode = movie_info_text[movie_info_text.find('集数:') + 3:]
        movie_episode = movie_episode[:movie_episode.find('\n')].replace('  ', ' ').rstrip().lstrip()
        sql = f"UPDATE `douban_index` SET `episode` = '{movie_episode}' WHERE `movie_ID` = {ID}"
        DB().update(sql)
    movie_info_text = movie_info_text.replace("'", r"\'")
    sql = f"UPDATE `douban_index` SET `info` = '{movie_info_text}' WHERE `movie_ID` = {ID}"
    DB().update(sql)
    print(movie_info_text)
    return
