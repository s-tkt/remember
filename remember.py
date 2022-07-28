import os
import sys
from functools import wraps
from tkinter import Tk, ttk
import tkinter as tk
from dialog import showerror, showinfo, showwarning
from registry import Registry, NoSuchItem, ExistingItem
import common
import msg

MSG = msg.m['cat']

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
                command=self.show_hint)
        # 設定
        self.g_menu_settings = tk.Menu(self.g_menubar, tearoff=0)
        self.g_menubar.add_cascade(label='設定', menu=self.g_menu_settings)
        #self.g_menu_settings.add('command', label='言語', command=self.

        self.g_passwd.focus_set()


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
            self.g_iterm.focus_set()
            return
        try:
            Registry.update(item, self.getvalue())
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
            self.g_iterm.focus_set()
            return
        value = self.getvalue()
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
            self.g_iterm.focus_set()
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
            showinfo(MSG['rem-li-di-ttl2'], MSG['rem-li-di-msg2'],
                button=MSG['rem-li-di-btn2'], detail=','.join(items)
            )
        self.reset_entry()

    def show_hint(self):
        showinfo(MSG['rem-sh-di-ttl1'], MSG['rem-sh-di-msg1'],
                button=MSG['rem-sh-di-btn1'],
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

if __name__ == '__main__':
    Registry.load()
    common.root = Tk()
    common.root.title(MSG['rem-main-title'])
    App(common.root)
    common.root.mainloop()
