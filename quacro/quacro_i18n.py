import logging
import tomllib
import typing

from . import quacro_win32
from .quacro_logging import warn_tb
from .quacro_errors import ConfigError


logger = logging.getLogger("i18n")

I18N_VERSION = 0

class Lang:
    language_code: str
    name: str
    translations: dict[str,str]
    @classmethod
    def load_lang(cls, lang_raw:dict[str,typing.Any]):
        self = cls.__new__(cls)
        self.translations = {}
        try:
            metadata = lang_raw.pop("metadata")
        except KeyError:
            raise ConfigError("Missing section 'metadata'")
        
        if type(metadata) is not dict:
            raise ConfigError("Section 'metadata' must be a dict")

        # todo:version checking

        try:
            self.language_code = metadata["language_code"]
        except KeyError:
            raise ConfigError("Missing 'metadata.language_code'")
        if type(self.language_code) is not str:
            raise ConfigError("'metadata.language_code' must be a str")
        
        try:
            self.name = metadata["name"]
        except KeyError:
            raise ConfigError("Missing 'metadata.name'")
        if type(self.name) is not str:
            raise ConfigError("'metadata.name' must be a str")
        
        def recursive_load_translation(path:list[str], data:dict[str,typing.Any]):
            for name in data:
                value = data[name]
                path.append(name)
                if type(value) is str:
                    self.translations['.'.join(path)] = value
                elif type(value) is dict:
                    recursive_load_translation(path, value)
                else:
                    warn_tb(logger, f"Ignoring invalid translation {'.'.join(path)}: translation must be str")
                path.pop()
        
        recursive_load_translation([], lang_raw)
        return self

    def get_translation(self, key:str):
        return self.translations.get(key, None)

LanguageCode:typing.TypeAlias = str
Name:typing.TypeAlias = str
languages: dict[tuple[LanguageCode, Name], Lang] = {}
current_language: Lang

class Underline:
    def __getitem__(self, key:str) -> str:
        translation = current_language.get_translation(key)
        if translation is None:
            warn_tb(logger, f"Can't find translation for string '{key}'")
            return key
        return translation
    def __call__(self, key:str, **kwargs) -> str:
        translation = current_language.get_translation(key)
        if translation is None:
            warn_tb(logger, f"Can't find translation for string '{key}'")
            return key
        return translation.format(**kwargs)
_ = Underline()

def load_language_from_file(path):
    with open(path, "rb") as lang_file:
        raw = tomllib.load(lang_file)
    lang = Lang.load_lang(raw)
    languages[(lang.language_code, lang.name)] = lang
    return lang

def set_current_language_to_environment_default() -> None:
    global current_language
    language_code = quacro_win32.get_user_defult_local_name()
    if not language_code:
        # Use en by default
        current_language = next(iter(languages.values()))
        return
    candidates: list[Lang] = []
    for key in languages:
        code = key[0]
        if code==language_code:
            current_language = languages[key]
            return
        if code.split('-')[0]==language_code.split('-')[0]:
            candidates.append(languages[key])
    if candidates:
        current_language = candidates[0]
        return
    else:
        # Use en by default
        current_language = next(iter(languages.values()))

def init():
    # load default language data
    import sys
    import os
    path_zh_cn = "i18n/quacro_lang_zh_cn.toml"
    path_en = "i18n/quacro_lang_en.toml"
    if getattr(sys, "frozen", False):
        path_zh_cn = os.path.join(getattr(sys,'_MEIPASS'), path_zh_cn)
        path_en = os.path.join(getattr(sys,'_MEIPASS'), path_en)
    else:
        path_zh_cn = os.path.join("./", path_zh_cn)
        path_en = os.path.join("./", path_en)
    load_language_from_file(path_zh_cn)
    load_language_from_file(path_en)
    set_current_language_to_environment_default()
