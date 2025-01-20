import time
import re

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


def get_long_comment():
    driver, expire_time = webserver()
    while True:
        name = None
        sql = f"SELECT movie_ID FROM douban_index WHERE `status` = '1'  ORDER BY movie_ID  LIMIT 1"
        flag, data = DB().select(sql)
        movie_ID = data[0][0]
        # movie_ID = 1863766
        time_out = 5
        sql = f"SELECT count(*) FROM douban_long_comment WHERE movie_ID = {movie_ID}"
        flag, data = DB().select(sql)

        if data:
            page = int(int(data[0][0]) / 20) * 20
        else:
            page = 0

        try:
            url = f"https://movie.douban.com/subject/{movie_ID}/reviews?sort=hotest&start={page}"
            driver.get(url)
            time.sleep(3)
            while True:
                try:
                    try:
                        title = driver.title
                        if title == '豆瓣 - 登录跳转页':
                            logger.write_log(f"----- 代理错误 -----", 'error')
                            driver.close()
                            driver.quit()
                            get_long_comment()

                    except (selenium.common.exceptions.TimeoutException, selenium.common.exceptions.WebDriverException):
                        logger.write_log(f"浏览器开启超时", 'error')
                        driver.close()
                        driver.quit()
                        get_long_comment()

                except Exception as e:
                    logger.write_log(e, 'error')

                try:
                    comment_count = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="content"]/h1'))).text
                    comment_count = comment_count[comment_count.rfind('(') + 1:][:-1]
                    sql = (f"UPDATE `Movie`.`douban_index` SET "
                           f"`long_comment_count` = {comment_count} WHERE `movie_ID` = {movie_ID}")
                    DB().update(sql)
                except selenium.common.exceptions.TimeoutException:
                    driver.close()
                    driver.quit()
                    get_long_comment()

                review_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'review-list')))

                review_divs = review_list.find_elements(By.TAG_NAME, 'div')

                data_cid_list = [div.get_attribute('data-cid') for div in review_divs if div.get_attribute('data-cid')]

                if len(data_cid_list) == 0:
                    sql = f"UPDATE `Movie`.`douban_index` SET `status` = '2' WHERE `movie_ID` = {movie_ID}"
                    DB().update(sql)
                    logger.write_log(F'电影ID - {movie_ID} 无评论', 'warning')
                    break

                logger.write_log(f"----------------------本页{len(data_cid_list)}条数据----------------------", 'info')
                try:
                    if_display = WebDriverWait(driver, time_out).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'btn-unfold')))
                    logger.write_log(if_display.text, 'warning')
                    if_display.click()
                    time.sleep(1)
                    start_display = None
                except (selenium.common.exceptions.TimeoutException,
                        selenium.common.exceptions.ElementNotInteractableException):
                    if_display = None

                for cid_code in data_cid_list:

                    if expire_time < now_time():
                        driver.close()
                        driver.quit()
                        get_long_comment()

                    try:
                        WebDriverWait(driver, time_out).until(
                            EC.presence_of_element_located((By.XPATH, f'//*[@id="toggle-{cid_code}-copy"]'))).click()
                    except (selenium.common.exceptions.TimeoutException,
                            selenium.common.exceptions.ElementNotInteractableException):
                        pass

                    logger.write_log(f'正在获取评论 评论ID - {cid_code}', 'info')

                    comment_title = get_comment_title(driver, time_out, cid_code)
                    user_name = get_user_name(driver, time_out, cid_code)
                    star = get_star(driver, time_out, cid_code)
                    release_time = get_release_time(driver, time_out, cid_code)
                    comment_text = get_comment_text(driver, time_out, cid_code)
                    up_num = get_up_num(driver, time_out, cid_code)
                    down_num = get_down_num(driver, time_out, cid_code)
                    reply_num = get_reply_num(driver, time_out, cid_code)

                    # print(comment_title)
                    # print(user_name)
                    # print(star)
                    # print(release_time)
                    # print(comment_text)
                    # print(up_num)
                    # print(down_num)
                    # print(reply_num)
                    # print(f'\n\n')

                    sql = (f"INSERT INTO `Movie`.`douban_long_comment`"
                           f" (`comment_ID`, `movie_ID`, `comment_title`, `user_name`, `star`, `release_time`, "
                           f"`comment_text`, `up_num`, `down_num`, `reply_num`) VALUES"
                           f" ({cid_code}, {movie_ID}, '{comment_title}', '{user_name}', '{star}', '{release_time}',"
                           f" '{comment_text}', {up_num}, {down_num}, {reply_num});")
                    DB().insert(sql)

                    time.sleep(0.2)
                try:
                    paginator = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'paginator')))
                    next_page_button = paginator.find_element(By.CLASS_NAME, 'next')
                    next_link = next_page_button.find_element(By.TAG_NAME, 'a').get_attribute('href')
                except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.TimeoutException):
                    next_link = None
                    next_page_button = None
                if next_link:
                    next_page_button.click()
                    time.sleep(2)

                else:
                    sql = f"UPDATE `Movie`.`douban_index` SET `status` = '2' WHERE `movie_ID` = {movie_ID}"
                    DB().update(sql)
                    break

        except Exception as e:
            logger.write_log(e, 'error')


def get_comment_title(driver, time_out, cid_code):
    comment_title = (WebDriverWait(driver, time_out).until(
        EC.presence_of_element_located((By.XPATH, f'//*[@id="{cid_code}"]/div[1]/h2/a'))).text.replace("'", r"\'"))
    return comment_title


def get_user_name(driver, time_out, cid_code):
    user_name = (WebDriverWait(driver, time_out).until(
        EC.presence_of_element_located((By.XPATH, f'//*[@id="{cid_code}"]/header/a[2]'))).text.replace("'", r"\'"))
    return user_name


def get_star(driver, time_out, cid_code):
    star = WebDriverWait(driver, time_out).until(
        EC.presence_of_element_located((By.XPATH, f'//*[@id="{cid_code}"]/header/span[1]')))
    star = star.get_attribute('title')
    return star


def get_release_time(driver, time_out, cid_code):
    try:
        release_time = WebDriverWait(driver, time_out).until(
            EC.presence_of_element_located((By.XPATH, f'//*[@id="{cid_code}"]/header/span[2]'))).text
    except selenium.common.exceptions.TimeoutException:
        release_time = WebDriverWait(driver, time_out).until(
            EC.presence_of_element_located((By.XPATH, f'//*[@id="{cid_code}"]/header/span'))).text

    return release_time


def get_comment_text(driver, time_out, cid_code):
    try:
        comment_text = WebDriverWait(driver, time_out).until(EC.presence_of_element_located
                                                             ((By.ID, f'link-report-{cid_code}'))).text.replace("'", r"\'")
        return comment_text.lstrip().rstrip()
    except (selenium.common.exceptions.TimeoutException,
            selenium.common.exceptions.ElementNotInteractableException) and Exception as e:
        logger.write_log(e, 'error')
        time.sleep(3)
        get_comment_text(driver, time_out, cid_code)


def get_up_num(driver, time_out, cid_code):
    try:
        up_num = WebDriverWait(driver, time_out).until(
            EC.presence_of_element_located(
                (By.XPATH, f'//*[@id="review-{cid_code}-content"]/div[3]/button[1]'))).text
        up_num = re.findall(r'\d+', up_num)[0]
        return up_num
    except (selenium.common.exceptions.TimeoutException,
            selenium.common.exceptions.ElementNotInteractableException) and Exception as e:
        logger.write_log(e, 'error')
    except IndexError:
        return 0


def get_down_num(driver, time_out, cid_code):
    try:
        down_num = WebDriverWait(driver, time_out).until(
            EC.presence_of_element_located(
                (By.XPATH, f'//*[@id="review-{cid_code}-content"]/div[3]/button[2]'))).text
        down_num = re.findall(r'\d+', down_num)[0]
        return down_num
    except (selenium.common.exceptions.TimeoutException,
            selenium.common.exceptions.ElementNotInteractableException) and Exception as e:
        logger.write_log(e, 'error')
    except IndexError:
        return 0


def get_reply_num(driver, time_out, cid_code):
    try:
        reply_num = WebDriverWait(driver, time_out).until(
            EC.presence_of_element_located((By.XPATH, f'//*[@id="{cid_code}"]/div/div[3]/a[3]'))).text
        reply_num = re.findall(r'\d+', reply_num)[0]
        return reply_num
    except (selenium.common.exceptions.TimeoutException,
            selenium.common.exceptions.ElementNotInteractableException) and Exception as e:
        logger.write_log(e, 'error')
    except IndexError:
        return 0