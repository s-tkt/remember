from tkinter import Tk, ttk, messagebox, simpledialog
import tkinter as tk
import common
from winsound import (
        MessageBeep,
        MB_ICONASTERISK, # SystemDefault
        MB_ICONEXCLAMATION, # SystemExclamation
        MB_ICONHAND, # SystemHadn
        MB_ICONQUESTION, # SystemQuestion
        MB_OK, # SystemDefault
    )

SOUND_DICT = {
    '*' : MB_ICONASTERISK,
    '!' : MB_ICONEXCLAMATION,
    'hand' : MB_ICONHAND,
    '?' : MB_ICONQUESTION,
    'ok' : MB_OK,
}

class PlaceDialog(simpledialog.Dialog):
    def __init__(self, title='', message='', button=[('OK','ok')], default='ok', detail=None, icon=None, sound='ok', parent=None):
        self.message = message
        self.detail = detail
        self.button = button
        self.defualt = default
        self.result = None
        if icon == 'info':
            icon = 'information'
        if icon in ('information', 'error', 'warning', 'question'):
            self.icon = '::tk::icons::' + icon
        else:
            self.icon = None
        self.sound = SOUND_DICT.get(sound)
        super().__init__(parent, title=title)

    def body(self, master):
        label = tk.Label(master, text=self.message,
                image=self.icon, compound=tk.LEFT)
        label.pack(padx=5, pady=5)
        if self.detail:
            detail = tk.Label(master, text = self.detail)
            detail.pack(padx=5, pady=5)
        MessageBeep(self.sound)

    def __c2f(self, c:str):
        if c == 'ok':
            return self.ok
        if c == 'cancel':
            return self.cancel
        return self.cancel

    def buttonbox(self):
        frm = tk.Frame(self)
        for text, command in self.button:
            w = tk.Button(frm, text=text, command=self.__c2f(command))
            w.pack(side=tk.RIGHT, padx=5, pady=5)
        self.bind('<Return>', self.ok)
        self.bind('<Escape>', self.cancel)
        frm.pack()

    def ok(self, event=None):
        self.result = 'ok'
        super().ok(event)

    def cancel(self, event=None):
        if self.result is None:
            self.result = 'cancel'
        super().cancel(event)

    def getresult(self):
        return self.result


class QueryString(simpledialog._QueryString):
    def ok(self, event=None):
        if self.entry.get() == '':
            return
        self.result = self.entry.get()
        super().ok(event)

    def getresult(self):
        return self.result


def showinfo(title, message, detail=None, button='納得にゃ'):
    PlaceDialog(title, message, detail=detail, button=[(button,'ok')],
            default='ok', icon='info', sound='ok', parent=common.root)

def showerror(title, message, detail=None, button='勘弁にゃ'):
    PlaceDialog(title, message, detail=detail, button=[(button, 'ok')],
            default='ok', icon='error', sound='!', parent=common.root)

def showwarning(title, message, detail=None,
        button=[('行くにゃ！','ok'),('嫌にゃ！','cancel')]):
    d = PlaceDialog(title, message, detail=detail, button=button,
            default='cancel', icon='warning', sound='?', parent=common.root)
    return d.getresult()

def askpassword(title, prompt, **kw):
    q = QueryString(title, prompt, show='*', parent=common.root, **kw)
    return q.getresult()
