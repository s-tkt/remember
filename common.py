# いいにゃ、絶対さわるでないにゃ。絶対ににゃ！
from config import Config
import msg
root = None
lang = Config()['lang']
MSG = msg.m[lang]
del lang
