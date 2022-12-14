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
import csv
import pickle
import dbm
from cryptography.fernet import Fernet
import bcrypt
from dialog import showinfo, showerror, showwarning, askpassword, askstring
import common
from common import MSG

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
            'last_saved', 'created', 'lang', 'hint')

    @classmethod
    def get_fernet_key(cls, passwd: str) -> bytes:
        sha = hashlib.sha256(passwd.encode())
        digest = sha.digest()[:32]
        return base64.urlsafe_b64encode(digest)

    '''@classmethod
    def get_double_hashed(cls, passwd: str) -> str:
        hashed = cls.get_fernet_key(passwd)
        sha = hashlib.sha256(hashed)
        digest = sha.digest()
        sha = hashlib.sha256(digest)
        return sha.hexdigest()'''

    @classmethod
    def get_hashed(cls, passwd: str) -> str:
        salt = bcrypt.gensalt(rounds=10, prefix=b'2a')
        return bcrypt.hashpw(passwd.encode(), salt)

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
            passwd1 = askpassword(MSG['reg-gp-da-ttl1'],
                    MSG['reg-gp-da-msg1'],
                    button = (MSG['reg-gp-da-btn1-ok'],
                        MSG['reg-gp-da-btn1-ca'])
                )
            if passwd1 == None:
                return None
            passwd2 = askpassword(MSG['reg-gp-da-ttl2'],
                MSG['reg-gp-da-msg2'],
                button = (MSG['reg-gp-da-btn2-ok'],
                    MSG['reg-gp-da-btn2-ca']))
            if passwd2 == None:
                return None
            if passwd1 != passwd2:
                showerror(MSG['reg-gp-de-ttl1'],
                    MSG['reg-gp-de-msg1'],
                    button = MSG['reg-gp-de-btn1'])
            else:
                break
        return passwd1

    # DBのアクセスでエラーが出たらメッセージ窓を出すにゃ！
    @classmethod
    def dbaccesserror(cls, e: Exception, mode:str='r') -> None:
        if mode == 'r':
            msg = MSG['reg-da-de-msg-r']
        elif mode == 'w':
            msg = MSG['reg-da-de-msg-w']
        else:
            msg = MSG['reg-da-de-msg-c']
        cls.error = True
        errormsg = '%s\n%s' % (str(e), traceback.format_exc())
        showerror(MSG['reg-da-de-ttl1'], msg, detail=errormsg)

    # DBアクセスチェックのデコレータにゃ
    def dbaccess(mode='r', ret=...):
        def _dbaccess(func):
            def wrapper(cls, *args, **kwargs):
                try:
                    return func(cls, *args, **kwargs)
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
                MSG['reg-lo-dw-msg1'],
                button=[(MSG['reg-lo-dw-btn1-ca'],'cancel'),
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
            cls.hint = askstring(MSG['reg-lo-da-ttl1'],
                    MSG['reg-lo-da-msg1'],
                    button=(MSG['reg-lo-da-btn1-ok'],
                        MSG['reg-lo-da-btn1-ca']))
            cls.password = cls.get_hashed(passwd)
            cls.db = dbm.open(Registry.PATH, 'c')
            cls.save(init=True)

        # 2回目以降にゃ
        else:
            db = dbm.open(Registry.PATH, 'c')
            if db['version'].decode() != cls.version:
                showerror(MSG['reg-lo-de-ttl1'], MSG['reg-lo-de-msg1'],
                        MSG['reg-lo-de-btn1'])
                cls.quit()
            cls.password = db['password']
            cls.hint = db['hint'].decode()
            cls.lang = db['lang'].decode()
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
            db['hint'] = cls.hint
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
            # どうしようもないにゃ。ズドンと終わらせるにゃ
            os._exit(-1)

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
        if bcrypt.checkpw(passwd.encode(), cls.password) == False:
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

    @classmethod
    @dbaccess('r', None)
    def export(cls, filename: str):
        # データが多いかもしれにゃから、1行ずつ書いていくにゃよ
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            ext = os.path.splitext(filename)[1]
            if ext == '.json':
                je = json.JSONEncoder(ensure_ascii=False)
                first = True
                for key, val in cls.db.items():
                    if key.decode() in cls.syskeys:
                        continue
                    ekey = je.encode(cls.decrypt(key.decode()))
                    evalue = je.encode(cls.decrypt(val.decode()))
                    if first == False:
                        f.write(',\n')
                    else:
                        f.write('{\n')
                        first = False
                    f.write('    %s: %s' % (ekey, evalue))
                f.write('\n}\n')
            elif ext == '.csv':
                writer = csv.writer(f)
                writer.writerow(['item', 'value'])
                for key, val in cls.db.items():
                    if key.decode() in cls.syskeys:
                        continue
                    writer.writerow([
                            cls.decrypt(key.decode()),
                            cls.decrypt(val.decode())
                        ])


    @classmethod
    @dbaccess('c', None)
    def import_(cls, imp: dict):
        for impkey in imp:
            try:
                k, v = cls.find(impkey)
                cls.db[k] = cls.encrypt(imp[impkey])
            except NoSuchItem:
                cls.db[cls.encrypt(impkey)] = cls.encrypt(imp[impkey])
        cls.db.sync()

