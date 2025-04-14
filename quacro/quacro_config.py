import tomllib

from .quacro_errors import ConfigError

class Config:
    window_groups_config_dict:dict
    @classmethod
    def load_config(cls, path:str):
        with open(path, "rb") as config_file:
            config_dict = tomllib.load(config_file)
        self = cls()
        if "window_groups" not in config_dict:
            raise ConfigError("Config 'window_groups' is not found")
        if type(config_dict["window_groups"]) is not dict:
            raise ConfigError("Type of config 'window_groups' must be dict")
        self.window_groups_config_dict = config_dict["window_groups"]
        return self


