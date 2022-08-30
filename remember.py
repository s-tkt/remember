import os
import sys
import threading
import traceback
from functools import wraps
from tkinter import Tk, ttk
from tkinter.scrolledtext import ScrolledText
import tkinter as tk
from dialog import showerror, showinfo, showwarning, askstring, place_window
from tkinter.filedialog import asksaveasfilename, askopenfilename
import csv
import json
import common
from registry import Registry, NoSuchItem, ExistingItem
from setting import Setting
from config import Config, ConfigLoadError, ConfigSaveError
from common import MSG

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
        try:
            self.config = Config()
        except ConfigLoadError as ce:
            showerror(MSG['rem-c-load-ttl'], MSG['rem-c-load-msg'],
                detail=traceback.format_exc(),
                button=MSG['rem-c-load-btn'])
            self.root.destroy()
            return
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.pack(expand=True, fill=tk.BOTH)

        # タイマー
        #self.cb_wait = self.config['interval']
        self.cb_thread = None
        self.last_remember = None

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
        ttk.Label(self, text=MSG['rem-l-cont']).grid(column=0, row=2,
            padx=5, pady=5, sticky=tk.E+tk.N)
        self.g_value = tk.scrolledtext.ScrolledText(master=self,
            height = 10,
            width = 30,
            pady = 10,
            wrap = tk.CHAR,
            exportselection = 0,
        )
        self.g_value.grid(column=1, row=2, pady=5, padx=10,
                sticky=tk.W+tk.E+tk.N+tk.S)

        # ボタン
        b_frm = ttk.Frame(self, padding=5)

        ttk.Button(b_frm, text=MSG['rem-b-show'],
                command=self.show).pack(side=tk.LEFT)
        ttk.Button(b_frm, text=MSG['rem-b-add'],
                command=self.add).pack(side=tk.LEFT)
        ttk.Button(b_frm, text=MSG['rem-b-upd'],
                command=self.update).pack(side=tk.LEFT)
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
        self.g_menu_ope = tk.Menu(self.g_menubar, tearoff=0)
        self.g_menubar.add_cascade(label=MSG['rem-me-ope'],
                menu=self.g_menu_ope)
        self.g_menu_ope.add('command', label=MSG['rem-me-ope-rm'],
                command=self.remove)
        self.g_menu_ope.add('command', label=MSG['rem-me-ope-re'],
                command=self.rename)
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
        self.g_menu_settings.add('command', label=MSG['rem-me-se-conf'],
                command=self.setting)
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
                button=MSG['rem-cp-de-btn1'], parent=self.root)
            return False
        if not Registry.password_match(passwd):
            showerror(MSG['rem-cp-de-ttl2'], MSG['rem-cp-de-msg2'],
                    button=MSG['rem-cp-de-btn2'], parent=self.root)
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


    # show() と list() で使いまわすにゃ
    def __show(self, item:str, focus=None, reset=False, parent=common.root):
        if item == '':
            showerror(MSG['rem-sh-de-ttl1'], MSG['rem-sh-de-msg1'],
                    button=MSG['rem-sh-de-btn1'], parent=parent)
            if focus:
                focus.focus_set()
            return
        try:
            value = Registry.get(item)
        except NoSuchItem:
            showerror(MSG['rem-sh-de-ttl2'], MSG['rem-sh-de-msg2'],
                    button=MSG['rem-sh-de-btn2'], parent=parent)
            if focus:
                focus.focus_set()
            return
        _value = value[:40]+MSG['rem-sh-misc'] if len(value) > 40 else value
        showinfo(MSG['rem-sh-di-ttl1'], MSG['rem-sh-di-msg1'],
                button=MSG['rem-sh-di-btn1'], detail=_value, parent=parent)
        self.clipboard_clear()
        self.clipboard_append(value)
        self.last_remember = value
        if focus:
            focus.focus_set()
        if reset:
            self.reset_entry()


    @verify_password
    def show(self):
        item = self.var_item.get()
        self.__show(item, focus=self.g_item, reset=True, parent=self.root)

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
                    button=MSG['rem-ad-de-ttl1'], parent=self.root)
            self.g_item.focus_set()
            return
        value = self.getvalue()[:-1] #最後の改行を取り除くにゃ
        if value == '':
            showerror(MSG['rem-ad-de-ttl2'], MSG['rem-ad-de-msg2'],
                    button=MSG['rem-ad-de-btn2'], parent=self.root)
            self.g_value.focus_set()
            return
        try:
            Registry.add(item, value)
        except ExistingItem:
            showerror(MSG['rem-ad-de-ttl3'], MSG['rem-ad-de-msg3'],
                    button=MSG['rem-ad-de-btn3'], parent=self.root)
            self.g_item.focus_set()
            return
        showinfo(MSG['rem-ad-di-ttl1'], MSG['rem-ad-di-msg1'],
                button=MSG['rem-ad-di-btn1'], parent=self.root)
        self.reset_entry()

    @verify_password
    def remove(self):
        item = self.var_item.get()
        if item == '':
            showerror(MSG['rem-rm-de-ttl1'], MSG['rem-rm-de-msg1'],
                    button=MSG['rem-rm-de-btn1'], parent=self.root)
            self.g_item.focus_set()
            return
        try:
            value = Registry.get(item)
            decision = showwarning(MSG['rem-rm-de-ttl2'],
                MSG['rem-rm-de-msg2'], detail = value,
                button=[
                    (MSG['rem-rm-de-btn2-ok'],'ok'),
                    (MSG['rem-rm-de-btn2-ca'],'cancel')
                ], parent=self.root)
            if decision != 'ok':
                showinfo(MSG['rem-rm-di-ttl1'], MSG['rem-rm-di-msg1'],
                        MSG['rem-rm-di-btn1'], parent=self.root)
                self.reset_entry()
                return
        except NoSuchItem:
            showerror(MSG['rem-rm-de-ttl3'], MSG['rem-rm-de-msg3'],
                    button=MSG['rem-rm-de-btn3'], parent=self.root)
            self.g_item.focus_set()
            return
        try:
            Registry.remove(item)
        except NoSuchItem:
            showerror(MSG['rem-rm-de-ttl4'], MSG['rem-rm-de-msg4'],
                    button=MSG['rem-rm-de-btn4'], parent=self.root)
            self.g_item.focus_set()
            return
        showinfo(MSG['rem-rm-di-ttl2'], MSG['rem-rm-di-msg2'],
                button=MSG['rem-rm-di-btn2'], parent=self.root)
        self.reset_entry()

    @verify_password
    def rename(self):
        item = self.g_item.get()
        if item == '':
            showerror(MSG['rem-re-de-ttl1'], MSG['rem-re-de-msg1'],
                button=MSG['rem-re-de-btn1'], parent=self.root)
            self.g_item.focus_set()
            return
        try:
            value = Registry.get(item)
        except NoSuchItem as e:
            showerror(MSG['rem-re-de-ttl4'], MSG['rem-re-de-msg4'],
                button=MSG['rem-re-de-btn4'],
                detail=item, parent=self.root)
            self.g_item.focus_set()
            return
        while True:
            new_item = askstring(MSG['rem-re-ds-ttl1'],
                MSG['rem-re-ds-msg1'],
                button=(MSG['rem-re-ds-btn1-ok'],
                    MSG['rem-re-ds-btn1-ca']),
                parent=self.root)
            if new_item is None:
                self.reset_entry()
                return
            # 同じ名前を入れるでないにゃ！
            if new_item == item:
                showerror(MSG['rem-re-de-ttl3'], MSG['rem-re-de-msg3'],
                    button=MSG['rem-re-de-btn3'], parent=self.root)
                continue

            # 項目名がDBに無いことを確認するにゃ
            try:
                v = Registry.get(new_item)
                showerror(MSG['rem-re-de-ttl2'], MSG['rem-re-de-msg2'],
                    button=MSG['rem-re-de-btn2'], parent=self.root)
                continue
            except NoSuchItem:
                break

        value = Registry.get(item)
        Registry.add(new_item, value)
        Registry.remove(item)
        showinfo(MSG['rem-re-di-ttl1'], MSG['rem-re-di-msg1'],
                button=MSG['rem-re-di-btn1'], parent=self.root)
        self.reset_entry()
        return

    # list() の選択ハンドラー
    def select_item(self, event=None):
        idx = self.g_itemlist.curselection()
        item = self.g_itemlist.get(idx)
        self.__show(item, focus=self.g_itemlist, reset=False, parent=self.g_list)


    # list() の終了ハンドラー
    def close_list(self):
        self.g_list.destroy()
        self.reset_entry()


    @verify_password
    def list(self):
        items = Registry.list()
        # まあ、ろくでもないことが起きたということにゃ
        if items is None:
            self.reset_entry()
            return
        if len(items) == 0:
            showinfo(MSG['rem-li-di-ttl1'], MSG['rem-li-di-msg1'],
                    button=MSG['rem-li-di-btn1'], parent=self.root)
            return
        # Toplevelの設定にゃ
        dlog = tk.Toplevel(takefocus=True)
        dlog.title(MSG['rem-li-di-ttl2'])
        dlog.protocol('WM_DELETE_WINDOW', self.close_list)
        dlog.grab_set()
        dlog.transient(self.root)
        self.g_list = dlog
        # 部品作りにゃ
        frm = ttk.Frame(dlog, padding=10)
        lbl = ttk.Label(frm, text=MSG['rem-li-di-msg2'])
        scr = tk.Scrollbar(frm, orient=tk.VERTICAL)
        lst = tk.Listbox(frm, yscrollcommand=scr.set, selectmode=tk.SINGLE)
        scr['command'] = lst.yview
        lst.bind('<<ListboxSelect>>', self.select_item)
        # 部品を配置するにゃ
        frm.pack(expand=True, fill=tk.BOTH)
        lbl.grid(column=0, row=0)
        lst.grid(column=0, row=1, sticky=tk.E+tk.W+tk.N+tk.S)
        scr.grid(column=1, row=1, sticky=tk.N+tk.S)
        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=0)
        frm.rowconfigure(0, weight=0)
        frm.rowconfigure(1, weight=1)
        lst.delete(0, tk.END)
        lst.insert(tk.END, *items)
        self.g_itemlist = lst
        place_window(dlog, self.root)
        dlog.focus_set()


    def hint(self):
        showinfo(MSG['rem-hi-di-ttl1'], MSG['rem-hi-di-msg1'],
                button=MSG['rem-hi-di-btn1'],
                detail=Registry.hint, parent=common.root)

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
            ], parent=common.root)
        if decision == 'ok':
            # Timer を止めるにゃ
            if self.cb_thread is not None:
                self.cb_thread.cancel()
            Registry.quit()
            # 自分で終わらせるにゃ。
            self.root.destroy()


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

    # JSONに重複がないか確かめるにゃ
    # 重複がなければ辞書を返すにゃ
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
            if  len(intersect) != 0:
                decision = showwarning(MSG['rem-im-dw-ttl1'],
                    MSG['rem-im-dw-msg1'],
                    detail=','.join(['"%s"' % i for i in intersect]),
                    button=[(MSG['rem-im-dw-btn1-ok'],'ok'),
                            (MSG['rem-im-dw-btn1-ca'], 'cancel')],
                )
                if decision == 'cancel':
                    self.reset_entry()
                    return

            Registry.import_(imp)
            self.reset_entry()

    def clear_clipboard(self):
        # にゃあが覚えたことと同じなら消すにゃ
        if self.master.clipboard_get() == self.last_remember:
            self.master.clipboard_clear()
            # どうもclearしただけでは消えないようにゃから空文字追加にゃ
            self.master.clipboard_append('')
        self.last_remenber = None

    @verify_password
    def setting(self):
        s = Setting(self.root, self.config)
        self.root.wait_window(s)
        # 後始末にゃ
        # クリップボード削除の設定変更反映
        # 同じ値になっていたら何もしないにゃ
        int_changed = False
        if s.cb_wait != self.config['interval']:
            self.config['interval'] = s.cb_wait
            int_changed = True
        lang_changed = False
        if s.v_lang.get() != self.config['lang']:
            self.config['lang'] = s.v_lang.get()
            lang_changed = True
        if int_changed or lang_changed:
            try:
                self.config.save()
            except ConfigSaveError as e:
                showerror(MSG['rem-se-se-lbl1'], MSG['rem-se-se-msg1'],
                    detail=traceback.format_exc(),
                    button=MSG['rem-se-se-btn1'])
                return
        if int_changed:
            if self.cb_thread and self.cb_thread.is_alive():
                self.cb_thread.cancel()
            if self.cb_wait != 0:
                self.cb_thread = threading.Timer(
                    self.cb_wait, self.clear_clipboard)
                self.cb_thread.start()
            else:
                self.cb_thread = None

# メインプログラムにゃよ
if __name__ == '__main__':
    Registry.load()
    common.root = Tk()
    common.root.title(MSG['rem-main-title'])
    App(common.root)
    common.root.mainloop()
