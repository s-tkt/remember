import os
import sys
import datetime
import hashlib
import zlib
import base64
import json
import pickle
from cryptography.fernet import Fernet
from dialog import showinfo, showerror, showwarning, askpassword
import common

class NoSuchItem(Exception):
    pass

class ExistingItem(Exception):
    pass

class Registry:
    PATH = 'record.json'
    version = 1
    n_add = 0
    n_remove = 0
    n_update = 0
    last_saved = None
    content = {'password':None, 'itemlist':{}}
    password = None # 生のパスワード
    fernet = None

    @staticmethod
    def get_fernet_key(passwd: str) -> bytes:
        sha = hashlib.sha256(passwd.encode())
        digest = sha.digest()[:32]
        return base64.urlsafe_b64encode(digest).decode()

    @staticmethod
    def get_double_hashed(passwd: str) -> str:
        hashed = Registry.get_fernet_key(passwd)
        sha = hashlib.sha256(hashed.encode())
        digest = sha.digest()
        sha = hashlib.sha256(digest)
        return sha.hexdigest()

    @staticmethod
    def make_fernet(passwd: str):
        Registry.fernet = Fernet(Registry.get_fernet_key(passwd))
        return Registry.fernet

    @staticmethod
    def encrypt(data: str) -> str:
        return Registry.fernet.encrypt(data.encode()).decode()

    @staticmethod
    def decrypt(data: str) -> str:
        return Registry.fernet.decrypt(data.encode()).decode()

    @staticmethod
    def getpassword():
        while(True):
            passwd1 = askpassword('準備にゃ', '秘密の合言葉を決めるにゃ。忘れたら何も思い出せなくなるにゃ。しっかり覚えるにゃ！')
            if passwd1 == None:
                return None
            passwd2 = askpassword('準備にゃ', '念のためもう一度合言葉を教えるにゃ。')
            if passwd2 == None:
                return None
            if passwd1 != passwd2:
                showerror('あわてるでないにゃ', 'パスワードが不一致にゃよ。')
            else:
                break
        return passwd1

    @staticmethod
    def load():
        if os.path.exists(Registry.PATH) == False:
            decision = showwarning('初めてにゃ？', 'おみゃあさん、初めて見るにゃ。違うにゃ？もし初めてでないにゃら何かおかしいにゃ。にゃあのノートが見当たらないにゃ。', button=[('初めてにゃ！','ok'),('やめるにゃ！','cancel')])
            if decision == 'cancel':
                showinfo('またにゃ！', 'にゃあはいつでもここにいるにゃ。',
                        button='またにゃ')
                sys.exit(0)
            passwd = Registry.getpassword()
            if passwd is None:
                showinfo('またにゃ！', 'にゃあはいつでもここにいるにゃ。',
                        button='またにゃ')
                sys.exit(0)

            Registry.content['password'] = Registry.get_double_hashed(passwd)
            if Registry.save() == False:
                showinfo('あきらめるでないにゃ！', 'なんかおかしいから直してからもう一度やって欲しいにゃ。', button='にゃあ')
                sys.exit(1)
            return True
        try:
            with open(Registry.PATH, 'r') as f:
                record = json.load(f)
        except Exception as e:
            showerror('大変にゃ！', '記憶ファイルが読めないにゃ！なんとかするにゃ！',
                detail=str(e))
            sys.exit(1)
        if record['version'] != Registry.version:
            showerror('やめるにゃ', 'バージョンアップがあったようにゃよ？きちんと前準備をするにゃ。')
            sys.exit(1)
        content = record['content']
        if zlib.adler32(pickle.dumps(content)) != record['check']:
            showerror('おいおい・・', '記憶が改ざんされているにゃよ・・')
            sys.exit(1)
        Registry.content = content
        Registry.n_add = record['history']['add']
        Registry.n_remove = record['history']['remove']
        Registry.n_update = record['history']['update']
        Registry.last_saved = datetime.datetime.strptime(record['last_saved'],
                '%Y-%m-%d %H:%M:%S.%f')
        return True

    @staticmethod
    def save():
        record = {
            'version': Registry.version,
            'history': {
                'add': Registry.n_add,
                'remove': Registry.n_remove,
                'update': Registry.n_update,
            },
            'last_saved': str(datetime.datetime.now()),
            'check': zlib.adler32(pickle.dumps(Registry.content)),
            'content': Registry.content,
        }
        try:
            with open(Registry.PATH, 'w', encoding='utf-8') as f:
                json.dump(record, f, indent=4)
            return True
        except Exception as e:
            showerror('一大事にゃ！', '設定ファイルが書き込めないにゃ！なんとか書き込めるようにしてくれにゃああああ',
                detail=str(e))
            return False

    @staticmethod
    def password_match(passwd):

        if Registry.get_double_hashed(passwd) != Registry.content['password']:
            return False
        Registry.fernet = Registry.make_fernet(passwd)
        return True

    # 復号されていないitemと復号されたvalueを返すにゃ
    @staticmethod
    def find(item: str):
        for k,v in Registry.content['itemlist'].items():
            dec_item = Registry.decrypt(k)
            if dec_item == item:
                return k, Registry.decrypt(v)
        raise NoSuchItem()


    @staticmethod
    def get(item: str):
        enc_item, value = Registry.find(item)
        return value

    @staticmethod
    def remove(item: str):
        enc_item, value = Registry.find(item)
        del(Registry.content['itemlist'][enc_item])
        Registry.n_remove += 1
        Registry.save()

    @staticmethod
    def update(item: str, value: str):
        enc_item, v = Registry.find(item)
        Registry.content['itemlist'][enc_item] = Registry.encrypt(value)
        Registry.n_update += 1
        Registry.save()

    @staticmethod
    def add(item: str, value: str):
        try:
            enc_item, v = Registry.find(item)
        except NoSuchItem:
            Registry.content['itemlist'][Registry.encrypt(item)] = Registry.encrypt(value)
            Registry.n_add += 1
            Registry.save()
            return
        raise ExistingItem()

    @staticmethod
    def list():
        return [Registry.decrypt(k) for k in Registry.content['itemlist'].keys()]

