import os
import sys
from functools import wraps
from tkinter import Tk, ttk
import tkinter as tk
from dialog import showerror, showinfo, showwarning
from tkinter.filedialog import asksaveasfilename, askopenfilename
import csv
import json
from registry import Registry, NoSuchItem, ExistingItem
import common
import msg

MSG = msg.m['cat']

class DupKeyError(Exception):
    def __init__(self, keys):
        self.keys = keys

class CsvColError(Exception):
    def __init__(self, number, row):
        self.number = number
        self.row = row

class JsonDataError(Exception):
    def __init__(self, key, val):
        self.key = json.dumps(key)
        self.val = json.dumps(val)

class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=10)
        self.root = root
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.pack(expand=True, fill=tk.BOTH)

        # 合言葉
        ttk.Label(self, text=MSG['rem-l-pass']).grid(column=0, row=0,
                sticky=tk.E)
        self.var_passwd = tk.StringVar()
        self.g_passwd = ttk.Entry(self,
                exportselection=0,
                show='*',
                textvariable = self.var_passwd
        )
        self.g_passwd.grid(column=1, row=0, padx=10, sticky=tk.W+tk.E)

        # 項目
        ttk.Label(self, text=MSG['rem-l-item']).grid(column=0, row=1, pady=5, sticky=tk.E)
        self.var_item = tk.StringVar()
        self.g_item = ttk.Entry(self,
                exportselection = 0,
                textvariable = self.var_item,
        )
        self.g_item.grid(column=1, row=1, padx=10, pady=5, sticky=tk.E+tk.W)
        self.g_item.bind('<Return>', self.check_and_show)

        # 内容
        ttk.Label(self, text=MSG['rem-l-cont']).grid(column=0, row=2, pady=5, sticky=tk.E+tk.N)
        t_frm = ttk.Frame(self, padding=5)
        self.g_value = tk.Text(t_frm,
                #padx = 5,
                #pady = 5,
                height = 10,
                width = 30,
                wrap = tk.CHAR,
                exportselection = 0,
        )
        self.g_value.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.g_scroll = ttk.Scrollbar(t_frm,
                orient=tk.VERTICAL,
                command=self.g_value.yview)
        self.g_value['yscrollcommand'] = self.g_scroll.set
        self.g_scroll.pack(anchor=tk.E, expand=True, fill=tk.Y)
        t_frm.grid(column=1, row=2,
                sticky=tk.W+tk.E+tk.N+tk.S)

        b_frm = ttk.Frame(self, padding=5)

        # ボタン
        ttk.Button(b_frm, text=MSG['rem-b-show'],
                command=self.show).pack(side=tk.LEFT)
        ttk.Button(b_frm, text=MSG['rem-b-add'],
                command=self.add).pack(side=tk.LEFT)
        ttk.Button(b_frm, text=MSG['rem-b-upd'],
                command=self.update).pack(side=tk.LEFT)
        ttk.Button(b_frm, text=MSG['rem-b-fgt'],
                command=self.remove).pack(side=tk.LEFT)
        #ttk.Button(b_frm, text=MSG['rem-b-list'],
        #        command=self.list).pack(side=tk.LEFT)
        b_frm.grid(column=0, row=3, columnspan=2)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=0)

        # メニューバー
        self.g_menubar = tk.Menu(self.root)
        self.root.config(menu=self.g_menubar)
        # メニュー
        # 表示
        self.g_menu_info = tk.Menu(self.g_menubar, tearoff=0)
        self.g_menubar.add_cascade(label=MSG['rem-me-sh'],
                menu=self.g_menu_info)
        self.g_menu_info.add('command', label=MSG['rem-me-sh-item'],
                command=self.list)
        self.g_menu_info.add('command', label=MSG['rem-me-sh-hint'],
                command=self.hint)
        # 設定
        self.g_menu_settings = tk.Menu(self.g_menubar, tearoff=0)
        self.g_menubar.add_cascade(label='設定', menu=self.g_menu_settings)
        #self.g_menu_settings.add('command', label='言語', command=self.
        # データ
        self.g_menu_data = tk.Menu(self.g_menubar, tearoff=0)
        self.g_menubar.add_cascade(label=MSG['rem-me-da'],
                menu=self.g_menu_data)
        self.g_menu_data.add('command', label=MSG['rem-me-da-ex'],
                command=self.export)
        self.g_menu_data.add('command', label=MSG['rem-me-da-im'],
                command=self.import_)

        self.g_passwd.focus_force()


    def check_passwd(self):
        passwd = self.var_passwd.get()
        if len(passwd) == 0:
            showerror(MSG['rem-cp-de-ttl1'],
                MSG['rem-cp-de-msg1'],
                button=MSG['rem-cp-de-btn1'])
            return False
        if not Registry.password_match(passwd):
            showerror(MSG['rem-cp-de-ttl2'], MSG['rem-cp-de-msg2'],
                    button=MSG['rem-cp-de-btn2'])
            self.g_passwd.focus_set()
            return False
        return True

    def getvalue(self):
        return self.g_value.get(1.0, tk.END)

    def reset_entry(self):
        self.var_passwd.set('')
        self.var_item.set('')
        self.g_value.delete(1.0, tk.END)
        self.g_passwd.focus_set()

    def check_and_show(self, event):
        if self.var_passwd.get() != '' and self.var_item.get() != '':
            self.show()

    # パスワードをチェックするデコレーターにゃ
    def verify_password(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if args[0].check_passwd() == False:
                return
            return func(*args, **kwargs)
        return wrapper


    @verify_password
    def show(self):
        item = self.var_item.get()
        if item == '':
            showerror(MSG['rem-sh-de-ttl1'], MSG['rem-sh-de-msg1'],
                    button=MSG['rem-sh-de-btn1'])
            self.g_item.focus_set()
            return
        try:
            value = Registry.get(item)
        except NoSuchItem:
            showerror(MSG['rem-sh-de-ttl2'], MSG['rem-sh-de-msg2'],
                    button=MSG['rem-sh-de-btn2'])
            self.g_item.focus_set()
            return
        _value = value[:40]+MSG['rem-sh-misc'] if len(value) > 40 else value
        showinfo(MSG['rem-sh-di-ttl1'], MSG['rem-sh-di-msg1'],
                button=MSG['rem-sh-di-btn1'], detail=_value)
        self.clipboard_clear()
        self.clipboard_append(value)
        self.reset_entry()

    @verify_password
    def update(self):
        item = self.var_item.get()
        if item == '':
            showerror(MSG['rem-up-de-ttl1'], MSG['rem-up-de-msg1'],
                    button=MSG['rem-up-de-btn1'])
            self.g_item.focus_set()
            return
        value = self.getvalue()[:-1] #最後の改行を取り除くにゃ
        if value == '':
            showerror(MSG['rem-up-de-ttl3'], MSG['rem-up-de-msg3'],
                    button=MSG['rem-up-de-btn3'])
            self.g_item.focus_set()
            return
        try:
            Registry.update(item, value)
        except NoSuchItem:
            showerror(MSG['rem-up-de-ttl2'], MSG['rem-up-de-msg2'],
                    button=MSG['rem-up-de-btn2'])
            self.g_item.focus_set()
            return
        showinfo(MSG['rem-up-di-ttl1'], MSG['rem-up-di-msg1'], button=MSG['rem-up-di-btn1'])
        self.reset_entry()

    @verify_password
    def add(self):
        item = self.var_item.get()
        if item == '':
            showerror(MSG['rem-ad-de-ttl1'], MSG['rem-ad-de-msg1'],
                    button=MSG['rem-ad-de-ttl1'])
            self.g_item.focus_set()
            return
        value = self.getvalue()[:-1] #最後の改行を取り除くにゃ
        if value == '':
            showerror(MSG['rem-ad-de-ttl2'], MSG['rem-ad-de-msg2'],
                    button=MSG['rem-ad-de-btn2'])
            self.g_value.focus_set()
            return
        try:
            Registry.add(item, value)
        except ExistingItem:
            showerror(MSG['rem-ad-de-ttl3'], MSG['rem-ad-de-msg3'],
                    button=MSG['rem-ad-de-btn3'])
            self.g_item.focus_set()
            return
        showinfo(MSG['rem-ad-di-ttl1'], MSG['rem-ad-di-msg1'],
                button=MSG['rem-ad-di-btn1'])
        self.reset_entry()

    @verify_password
    def remove(self):
        item = self.var_item.get()
        if item == '':
            showerror(MSG['rem-rm-de-ttl1'], MSG['rem-rm-de-msg1'],
                    button=MSG['rem-rm-de-btn1'])
            self.g_item.focus_set()
            return
        try:
            value = Registry.get(item)
            decision = showwarning(MSG['rem-rm-de-ttl2'], MSG['rem-rm-de-msg2'],
                button=[
                    (MSG['rem-rm-de-btn2-ok'],'ok'),
                    (MSG['rem-rm-de-btn2-ca'],'cancel')
                ])
            if decision != 'ok':
                showinfo(MSG['rem-rm-di-ttl1'], MSG['rem-rm-di-msg1'],
                        MSG['rem-rm-di-btn1'])
                self.reset_entry()
                return
        except NoSuchItem:
            showerror(MSG['rem-rm-de-ttl3'], MSG['rem-rm-de-msg3'],
                    button=MSG['rem-rm-de-btn3'])
            self.g_item.focus_set()
            return
        try:
            Registry.remove(item)
        except NoSuchItem:
            showerror(MSG['rem-rm-de-ttl4'], MSG['rem-rm-de-msg4'],
                    button=MSG['rem-rm-de-btn4'])
            self.g_item.focus_set()
            return
        showinfo(MSG['rem-rm-di-ttl2'], MSG['rem-rm-di-msg2'],
                button=MSG['rem-rm-di-btn2'])
        self.reset_entry()

    @verify_password
    def list(self):
        items = Registry.list()
        if items is None:
            self.reset_entry()
            return
        if len(items) == 0:
            showinfo(MSG['rem-li-di-ttl1'], MSG['rem-li-di-msg1'],
                    button=MSG['rem-li-di-btn1'])
        else:
            def fmt(items):
                ret = ''
                s = ''
                for i in items:
                    if len(s) + len(i) > 50:
                        ret += ',\n%s' % s
                        s = '"%s"' % i
                    else:
                        s += ',"%s"' % i
                if s != '':
                    ret += ',\n%s' % s
                return ret

            showinfo(MSG['rem-li-di-ttl2'], MSG['rem-li-di-msg2'],
                button=MSG['rem-li-di-btn2'], detail=fmt(items)
            )

    def hint(self):
        showinfo(MSG['rem-hi-di-ttl1'], MSG['rem-hi-di-msg1'],
                button=MSG['rem-hi-di-btn1'],
                detail=Registry.hint)

    def quit(self):
        if Registry.error:
            msg = MSG['rem-qu-dw-dtl1']
        else:
            msg = None
        decision = showwarning(MSG['rem-qu-dw-ttl1'], MSG['rem-qu-dw-msg1'],
            detail=msg,
            button=[
                (MSG['rem-qu-dw-btn1-ok'], 'ok'),
                (MSG['rem-qu-dw-btn1-ca'], 'cancel')
            ])
        if decision == 'ok':
            Registry.quit()

    @verify_password
    def export(self):
        fn = asksaveasfilename(parent=self.root,
                title=MSG['rem-ex-df-ttl1'],
                initialdir = os.getcwd(),
                #initialfile = UserDataFile,
                filetypes = [('CSV', '*.csv'),('JSON', '*.json')],
                defaultextension = 'csv',
                confirmoverwrite = True,
            )
        if fn == '':
            self.reset_entry()
            return
        try:
            Registry.export(fn)
        except OSError as e:
            showerror(MSG['rem-ex-de-ttl1'], MSG['rem-ex-de-msg1'],
                detail=str(e),
                button=MSG['rem-ex-de-btn1']
            )
        finally:
            self.reset_entry()

    def __json_check_dup(self, d):
        uniq_key = {x[0] for x in d}
        if len(d) != len(uniq_key):
            dup_key = [x[0] for x in d]
            for u in uniq_key:
                self.dup_key.remove(u)
            raise DupKeyError(dup_key)
        else:
            return {x[0]:x[1] for x in d}

    @verify_password
    def import_(self):
        fn = askopenfilename(parent=self.root,
                title=MSG['rem-im-df-ttl1'],
                initialdir = os.getcwd(),
                #initialfile = UserDataFile,
                filetypes = [('CSV', '*.csv'),('JSON', '*.json')],
                defaultextension = 'csv',
            )
        if fn == '':
            self.reset_entry()
            return
        ext = os.path.splitext(fn)[1]
        with open(fn, 'r', newline='', encoding='utf-8') as f:
            try:
                if ext == '.json':
                    imp = json.load(f,
                        object_pairs_hook=lambda x:self.__json_check_dup(x))
                    # jsonのデータ型をチェックするにゃ！
                    for key, val in imp.items():
                        if type(key) != str or type(val) != str:
                            raise JsonDataError(key, val)
                elif ext == '.csv':
                    imp, key_list = [], []
                    reader = csv.reader(f)
                    for i, row in enumerate(reader):
                        if len(row) != 2:
                            raise CsvColError(i, row)
                        imp.append(row)
                        key_list.append(row[0])
                    if len(key_list) != len(set(key_list)):
                        dup_key = key_list
                        for u in set(key_list):
                            dup_key.remove(u)
                        raise DupKeyError(dup_key)
            # フォーマットがおかしいにゃよ
            except (ValueError, csv.Error) as e:
                showerror(MSG['rem-im-de-ttl1'],
                    MSG['rem-im-de-msg1'],
                    detail = str(e),
                    button = MSG['rem-im-de-btn1'])
                self.reset_entry()
                return
            # 2カラムでない行があるCSVファイルにゃ
            except CsvColError as e:
                showerror(MSG['rem-im-de-ttl2'],
                    MSG['rem-im-de-msg2'],
                    detail = '%s: %s' % (e.number, e.row),
                    button = MSG['rem-im-de-btn2'])
                self.reset_entry()
                return
            except JsonDataError as e:
                showerror(MSG['rem-im-de-ttl3'],
                    MSG['rem-im-de-msg3'],
                    detail = '"%s": "%s"' % (e.key, e.val),
                    button = MSG['rem-im-de-btn3'])
                self.reset_entry()
                return
            except DupKeyError as e:
                showerror(MSG['rem-im-de-ttl4'],
                    MSG['rem-im-de-msg4'],
                    detail = '"' + '","'.join(dup_key) + '"',
                    button = MSG['rem-im-de-btn4'],
                )
                self.reset_entry()
                return

            # DBの中のキーと重複がないかチェックするにゃ。
            intersect = set(Registry.list()) & set(imp.keys())
            if  intersect != set():
                decision = showwarning(MSG['rem-im-dw-ttl1'],
                    MSG['rem-im-dw-msg1'],
                    detail=','.join(['"%s"' % i for i in intersect]),
                    button=[(MSG['rem-im-dw-btn1-ok'],'ok'),
                            (MSG['rem-im-dw-btn1-ca'], 'cancel')],
                )
                if decision == 'cancel':
                    self.reset_entry()
                    self.reset_entry()
                    return

            Registry.import_(imp)
            self.reset_entry()


if __name__ == '__main__':
    Registry.load()
    common.root = Tk()
    common.root.title(MSG['rem-main-title'])
    App(common.root)
    common.root.mainloop()
