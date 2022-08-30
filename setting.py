import tkinter as tk
from tkinter import Tk, ttk
from tkinter.scrolledtext import ScrolledText
import msg
from dialog import place_window
from common import MSG


class Setting(tk.Toplevel):
    def __init__(self, master, config):
        super().__init__(takefocus=True)
        self.master = master
        self.config = config
        # Toplevelの設定にゃ
        self.title(MSG['set-in-ttl'])
        self.protocol('WM_DELETE_WINDOW', self.close_setting)
        self.grab_set()
        self.transient(self.master)
        # 部品作りにゃ
        frm = ttk.Frame(self, padding=10)
        lfrm1 = ttk.LabelFrame(frm, text=MSG['set-in-frm1'], padding=5)
        lbl1 = ttk.Label(lfrm1, text=MSG['set-in-lbl1'])
        ent1 = ttk.Entry(lfrm1, exportselection=0, justify=tk.LEFT,
                validate='key',
                validatecommand=(frm.register(self.clip_validate), '%P'),
                )
        ent1.insert(tk.END, config['interval'])
        lfrm2 = ttk.LabelFrame(frm, text=MSG['set-in-frm2'], padding=5)
        lbl2 = ttk.Label(lfrm2, text=MSG['set-in-lbl2'])
        v_ome2 = tk.StringVar()
        optlist = ('English', '日本語', 'にゃあ語')
        v_ome2.set(optlist[0])
        ome2 = tk.OptionMenu(lfrm2, v_ome2, *optlist)
        self.v_lang = v_ome2
        btn1 = ttk.Button(frm, text=MSG['set-in-btn1'],
                command = self.close_setting)
        # 部品を配置するにゃ
        frm.pack(expand=True, fill=tk.BOTH)
        lfrm1.pack(expand=True, fill=tk.X)
        lbl1.grid(column=0, row=0)
        ent1.grid(column=1, row=0, sticky=tk.E+tk.W+tk.N+tk.S)
        lfrm2.pack(expand=True, fill=tk.X)
        lbl2.grid(column=0, row=0)
        ome2.grid(column=1, row=0, sticky=tk.E+tk.W+tk.N+tk.S)
        btn1.pack(anchor=tk.SE, padx=5, pady=5)
        self.g_ent1 = ent1
        #scr.grid(column=1, row=1, sticky=tk.N+tk.S)
        #frm.columnconfigure(0, weight=1)
        #frm.columnconfigure(1, weight=0)
        #frm.rowconfigure(0, weight=0)
        #frm.rowconfigure(1, weight=1)
        #lst.delete(0, tk.END)
        #lst.insert(tk.END, *items)
        #self.g_itemlist = lst
        place_window(self, self.master)


    def close_setting(self):
        # クリップボード関連
        ent1 = self.g_ent1.get()
        if ent1 == '':
            self.cb_wait = 0
        else:
            self.cb_wait = int(ent1)

        self.destroy()

    def clip_validate(self, text):
        # 数字だけにゃ。
        # 0はクリップボードから消さないの意味にゃ。
        for c in text:
            if c not in '0123456789':
                return False
        return True


