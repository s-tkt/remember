import sys
import json

class ConfigLoadError(Exception):
    pass

class ConfigSaveError(Exception):
    pass

class Config(dict):
    CONFIG_FILE = 'config.json'
    def __init__(self, **kargs):
        super().__init__(**kargs)
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                con = json.load(f)
                self.update(con)
        except Exception as e:
            tb = sys.exc_info()[2]
            raise ConfigLoadError('Error loading config.json').with_traceback(tb)


    def save(self):
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self, f, ensure_ascii=False)
        except Exception as e:
            tb = sys.exc_info()[2]
            raise ConfigSaveError('Error saving config.json').with_traceback(tb)
