import os
import sys
import traceback
import inspect
import datetime
import hashlib
from functools import wraps
import zlib
import base64
import json
import pickle
import dbm
from cryptography.fernet import Fernet
from dialog import showinfo, showerror, showwarning, askpassword
import common
import msg

MSG = msg.m['cat']

class NoSuchItem(Exception):
    pass

class ExistingItem(Exception):
    pass

class Registry:
    PATH = 'memory'
    db = None
    version = '1.0'
    n_add = 0
    n_remove = 0
    n_update = 0
    last_saved = None
    password = None # hashされたパスワード
    hint = None
    fernet = None
    error = False
    lang = 'cat'
    syskeys = ('version', 'password', 'n_add', 'n_remove', 'n_update',
            'last_saved', 'created', 'lang')

    @classmethod
    def get_fernet_key(cls, passwd: str) -> bytes:
        sha = hashlib.sha256(passwd.encode())
        digest = sha.digest()[:32]
        return base64.urlsafe_b64encode(digest)

    @classmethod
    def get_double_hashed(cls, passwd: str) -> str:
        hashed = cls.get_fernet_key(passwd)
        sha = hashlib.sha256(hashed)
        digest = sha.digest()
        sha = hashlib.sha256(digest)
        return sha.hexdigest()

    @classmethod
    def make_fernet(cls, passwd: str) -> Fernet:
        fernet_key = cls.get_fernet_key(passwd)
        cls.fernet = Fernet(fernet_key)
        return cls.fernet

    @classmethod
    def encrypt(cls, data: str) -> str:
        return cls.fernet.encrypt(data.encode()).decode()

    @classmethod
    def decrypt(cls, data: str) -> str:
        #print('called: ' + inspect.stack()[1].function)
        return cls.fernet.decrypt(data.encode()).decode()


    @classmethod
    def getpassword(cls) -> str:
        while(True):
            passwd1 = askpassword('準備にゃ', '秘密の合言葉を決めるにゃ。忘れたら何も思い出せなくなるにゃ。しっかり覚えるにゃ！',
                    button=('もちろんにゃ！', '今はちょっと、にゃ'))
            if passwd1 == None:
                return None
            passwd2 = askpassword('準備にゃ', '念のためもう一度合言葉を教えるにゃ。', button=('これにゃ！', 'やめるにゃ'))
            if passwd2 == None:
                return None
            if passwd1 != passwd2:
                showerror('あわてるでないにゃ', 'パスワードが不一致にゃよ。')
            else:
                break
        return passwd1

    # DBのアクセスでエラーが出たらメッセージ窓を出すにゃ！
    @classmethod
    def dbaccesserror(cls, e: Exception, mode:str='r') -> None:
        if mode == 'r':
            msg = '記憶ファイルが読めないにゃ！なんとかするにゃ！'
        elif mode == 'w':
            msg = '記憶ファイルが書き込めないにゃ！なんとか書き込めるようにしてくれにゃああああ！',
        else:
            msg = '記憶ファイルに読み書きできないにゃ！なんとかするにゃああああ！',
        cls.error = True
        errormsg = '%s\n%s' % (str(e), traceback.format_exc())
        showerror('一大事にゃ！', msg, detail=errormsg)

    # DBアクセスチェックのデコレータにゃ
    def dbaccess(mode='r', ret=...):
        def _dbaccess(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except dbm.error as e:
                    cls.dbaccesserror(e, mode)
                    if ret == 'exit':
                        sys.exit(1)
                    else:
                        return ret
            return wrapper
        return _dbaccess


    @classmethod
    @dbaccess('c', 'exit')
    def load(cls) -> None:
        # 初めて使うにゃ
        if os.path.exists(cls.PATH + '.dat') == False:
            decision = showwarning(MSG['reg-lo-dw-ttl1'],
                MSG['reg-lo-dw-ttk1'],
                button=[(MSG['reg-lo-dw-btn1-ok'],'cancel'),
                    (MSG['reg-lo-dw-btn1-ok'],'ok')])
            if decision == 'cancel':
                showinfo(MSG['reg-lo-in-ttl1'], MSG['reg-lo-in-msg1'],
                        button=MSG['reg-lo-in-btn1'])
                sys.exit(0)
            passwd = cls.getpassword()
            if passwd is None:
                showinfo(MSG['reg-lo-in-ttl1'], MSG['reg-lo-in-msg1'],
                        button=MSG['reg-lo-in-btn1'])
                sys.exit(0)
            cls.hint = ascstring(MSG['reg-lo-da-ttl1'],
                    MSG['reg-lo-da-msg1'],
                    button=(MSG['reg-lo-da-btn1-ok'],
                        MSG['reg-lo-da-btn1-ca']))
            cls.password = cls.get_double_hashed(passwd)
            cls.db = dbm.open(Registry.PATH, 'c')
            cls.save(init=True)

        # 2回目以降にゃ
        else:
            db = dbm.open(Registry.PATH, 'c')
            if db['version'].decode() != cls.version:
                showerror(MSG['reg-lo-de-ttl1'], MSG['reg-lo-de-msg1'],
                        MSG['reg-lo-de-btn1'])
                cls.quit()
            cls.password = db['password'].decode()
            cls.n_add = int(db['n_add'])
            cls.n_remove = int(db['n_remove'])
            cls.n_update = int(db['n_update'])
            cls.last_saved = datetime.datetime.strptime(
                    db['last_saved'].decode(), '%Y-%m-%d %H:%M:%S.%f')
            cls.created = db['created'].decode()
            cls.version = db['version'].decode()
            cls.db = db

    @classmethod
    @dbaccess('w', 'exit')
    def save(cls, init=False) -> bool:
        if cls.error:
            dicision = showwarning(MSG['reg-sa-dw-ttl1'],
                MSG['reg-sa-dw-msg1'],
                button=[(MSG['reg-sa-dw-btn1-ok'],'ok'),
                (MSG['reg-sa-dw-btn1-ca'],'cancel')])
            if dicision == 'cancel':
                showinfo(MSG['reg-sa-di-ttl1'], MSG['reg-sa-di-msg1'],
                        MSG['reg-sa-di-btn1'])
                return False
        db = cls.db
        now = str(datetime.datetime.now())
        if init:
            db['version'] = cls.version
            db['created'] = now
            db['password'] = cls.password
            db['lang'] = cls.lang
        db['n_add'] = str(cls.n_add)
        db['n_remove'] = str(cls.n_remove)
        db['n_update'] = str(cls.n_update)
        db['last_saved'] = now
        db.sync()
        return True

    @classmethod
    def quit(cls) -> None:
        try:
            cls.db.close()
        except Exception as e:
            showerror(MSG['reg-qu-de-ttl1'], MSG['reg-qu-de-msg1'], detail=str(e), button=MSG['reg-qu-de-btn1'])
        sys.exit(0)

    # DBからにゃあが覚えたデータのキーだけとってくるにゃ
    # 毎回DBから検索するのは効率が悪いかもしれないにゃ
    @classmethod
    @dbaccess('r')
    def get_keys(cls) -> list[str]:
        key_list = []
        for key in cls.db.keys():
            key = key.decode()
            if key not in cls.syskeys:
                key_list.append(key)
        return key_list

    @classmethod
    def password_match(cls, passwd: str) -> bool:
        if cls.get_double_hashed(passwd) != cls.password:
            return False
        if cls.fernet is None:
            cls.make_fernet(passwd)
        return True


    # 復号されていないitemと復号されたvalueを返すにゃ
    @classmethod
    @dbaccess('r')
    def find(cls, item: str) -> tuple[str, str]:
        for k in cls.get_keys():
            if item == cls.decrypt(k):
                return k, cls.decrypt(cls.db[k].decode())
        raise NoSuchItem()

    @classmethod
    def get(cls, item: str) -> str:
        k, v = cls.find(item)
        return v

    @classmethod
    @dbaccess('w', False)
    def remove(cls, item: str) -> bool:
        key, value = cls.find(item)
        del(cls.db[key])
        cls.n_remove += 1
        cls.save()
        return True

    @classmethod
    @dbaccess('w', False)
    def update(cls, item: str, value: str) -> bool:
        key, v = cls.find(item)
        cls.db[key] = cls.encrypt(value)
        cls.n_update += 1
        cls.save()
        return True

    @classmethod
    @dbaccess('w', False)
    def add(cls, item: str, value: str) -> bool:
        try:
            key, v = cls.find(item)
        except NoSuchItem:
            cls.db[cls.encrypt(item)] = cls.encrypt(value)
            cls.n_add += 1
            cls.save()
            return True
        raise ExistingItem()

    @classmethod
    @dbaccess('w', None)
    def list(cls) -> list[str]:
        item_list = []
        for key in cls.get_keys():
            item_list.append(cls.decrypt(key))
        return item_list

