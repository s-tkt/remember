import os
import sys
from functools import wraps
from tkinter import Tk, ttk
import tkinter as tk
from dialog import showerror, showinfo, showwarning
from registry import Registry, NoSuchItem, ExistingItem
import common

MIN_PASSWORD_LEN = 4

class App(ttk.Frame):
    ENT_OK = 1
    ENT_NO_ENT = 2
    ENT_NOT_FOUND = 3
    def __init__(self, root):
        super().__init__(root, padding=10)
        self.root = root
        self.pack(expand=True, fill=tk.BOTH)
        ttk.Label(self, text='大切な合言葉にゃ！').grid(column=0, row=0,
                sticky=tk.E)
        self.var_passwd = tk.StringVar()
        self.g_passwd = ttk.Entry(self,
                exportselection=0,
                show='*',
                textvariable = self.var_passwd
        )
        self.g_passwd.grid(column=1, row=0, padx=10, sticky=tk.W+tk.E)
        ttk.Label(self, text='何を知りたい/覚えたいにゃ？').grid(column=0, row=1, pady=5, sticky=tk.E)
        self.var_item = tk.StringVar()
        self.g_item = ttk.Entry(self,
                exportselection = 0,
                textvariable = self.var_item,
        )
        self.g_item.grid(column=1, row=1, padx=10, pady=5, sticky=tk.E+tk.W)
        self.g_item.bind('<Return>', self.check_and_show)
        ttk.Label(self, text='覚えたい内容にゃ').grid(column=0, row=2, pady=5, sticky=tk.E+tk.N)
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
        ttk.Button(b_frm, text='思い出すにゃ',
                command=self.show).pack(side=tk.LEFT)
        ttk.Button(b_frm, text='覚えるにゃ',
                command=self.add).pack(side=tk.LEFT)
        ttk.Button(b_frm, text='覚えなおすにゃ',
                command=self.update).pack(side=tk.LEFT)
        ttk.Button(b_frm, text='忘れるにゃ',
                command=self.remove).pack(side=tk.LEFT)
        ttk.Button(b_frm, text='一覧にゃ',
                command=self.list).pack(side=tk.LEFT)
        b_frm.grid(column=0, row=3, columnspan=2)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=0)
        self.g_passwd.focus_set()


    def check_passwd(self):
        passwd = self.var_passwd.get()
        if len(passwd) == 0:
            showerror('あわてるにゃ',
                'パスワードを入れてないじゃにゃいか',
                button='もう一度にゃ')
            return False
        if not Registry.password_match(passwd):
            showerror('あせるにゃ', 'パスワードが違うにゃ！よく確認するにゃ。', button='落ち着くにゃ')
            return False
        Registry.make_fernet(passwd)
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
            showerror('無理にゃよ', '知りたいことを教えてくれにゃ・・・',
                    button='またくるにゃ')
            self.g_iterm.focus_set()
            return
        try:
            value = Registry.get(item)
        except NoSuchItem:
            showerror('だめにゃった', 'そんなことは知らないにゃ・・・',
                    button='よく思い出すにゃ')
            self.g_item.focus_set()
            return
        _value = value[:40]+'...むにゃむにゃ' if len(value) > 40 else value
        showinfo('みつけたにゃ！', 'あったにゃ！クリップボードにコピーしたにゃ。',
                button='納得にゃあ', detail='%s' % _value)
        self.clipboard_clear()
        self.clipboard_append(value)
        self.reset_entry()

    @verify_password
    def update(self):
        item = self.var_item.get()
        if item == '':
            showerror('無理にゃよ', '覚えなおしたいことを教えてくれにゃ・・・',
                    button='またくるにゃ')
            self.g_iterm.focus_set()
            return
        try:
            Registry.update(item, self.getvalue())
        except:
            showerror('だめにゃった', 'そんなことは知らないにゃ・・・',
                    button='よく思い出すにゃ')
            self.g_item.focus_set()
            return
        showinfo('できたにゃ', '覚え直したにゃ。',
                button='納得にゃあ')
        self.reset_entry()

    @verify_password
    def add(self):
        item = self.var_item.get()
        if item == '':
            showerror('無理にゃよ', '覚えたいことを教えてくれにゃ・・・',
                    button='またくるにゃ')
            self.g_iterm.focus_set()
            return
        value = self.getvalue()
        if value == '':
            showerror('意味ないにゃ', '中身が空っぽにゃが？',
                    button='またくるにゃ')
            self.g_value.focus_set()
            return
        try:
            Registry.add(item, value)
        except ExistingItem:
            showerror('やめるにゃ', 'その項目はもうあるにゃよ？上書きしたいなら覚えなおすにゃ',
                    button='考え直すにゃ')
            self.g_item.focus_set()
            return
        showinfo('できたにゃ', '新しいことを覚えたにゃ。',
                button='納得にゃあ')
        self.reset_entry()

    @verify_password
    def remove(self):
        item = self.var_item.get()
        if item == '':
            showerror('無理にゃよ', '何を忘れたいにゃ？',
                    button='またくるにゃ')
            self.g_iterm.focus_set()
            return
        try:
            value = Registry.get(item)
            decision = showwarning('もう一度考えるにゃ', 'それは本当に忘れてもいいことにゃ？もう二度と思い出せないにゃよ？')
            if decision != 'ok':
                showinfo('わかったにゃ', 'そういう思い出もあるにゃ・・・')
                self.reset_entry()
                return
        except NoSuchItem:
            showerror('それ何にゃ？', 'そんな思い出はないにゃ・・・',
                    button='よく思い出すにゃ')
            self.g_item.focus_set()
            return
        try:
            Registry.remove(item)
        except NoSuchItem:
            showerror('ありえないにゃ', 'さっきまで覚えていたのに忘れたにゃ！',
                    button='怖いにゃ')
            self.g_item.focus_set()
            return
        showinfo('できたにゃ', 'もうそのことは忘れたにゃ。忘れることも大切にゃ・・・',
                button='諸行無常にゃあ')
        self.reset_entry()

    @verify_password
    def list(self):
        items = Registry.list()
        if len(items) == 0:
            showinfo('にゃぁぁ', 'にゃあはまだ何も覚えてないにゃ・・・')
        else:
            showinfo('にゃ～ん', '忘れたのかにゃ？特別に見せてやるにゃよ。おさかな持ってくるにゃ',
                button='わかったにゃ！', detail=','.join(items)
            )
        self.reset_entry()

if __name__ == '__main__':
    Registry.load()
    common.root = Tk()
    common.root.title('猫の秘密帳～おさかな食べさせるにゃ！')
    App(common.root)
    common.root.mainloop()
