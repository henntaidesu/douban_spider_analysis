from src.module.read_conf import ReadConf
from src.douban.personnel import get_personnel
from src.douban.info import exhaustive_ID
# from src.douban.long_comment import get_long_comment
# from machine_emotion.clean_text import chinese_tokenize


class Index:

    def __init__(self):
        self.conf = ReadConf()

    @staticmethod
    def index():
        # chinese_tokenize()
        exhaustive_ID()
        # get_personnel()
        # get_long_comment()
