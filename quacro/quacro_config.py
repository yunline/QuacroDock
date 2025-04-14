import tomllib

from . import quacro_window_filters
from .quacro_window_group import WindowGrup
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

    def load_window_filter_config(self) -> tuple:
        group_config_raw = self.window_groups_config_dict
        groups:dict[str, WindowGrup] = {}
        zero_level_groups: list[WindowGrup] = []
        primary_group: WindowGrup

        has_primary = False
        for name in group_config_raw:
            cfg = group_config_raw[name]
            grp = WindowGrup(name)
            groups[name] = grp
            if type(cfg) is not dict:
                raise ConfigError("Type of window group config must be dict")
            if "primary" in cfg:
                primary = cfg["primary"]
                if type(primary) is not bool:
                    raise ConfigError("Type of config 'primary' must be bool")
                if primary:
                    if has_primary:
                        raise ConfigError("Only one group can be set as primary")
                    has_primary = True
                    primary_group = grp
                    grp.primary = True
        if not has_primary:
            raise ConfigError("No primary group is specified")

        for name in groups:
            cfg = group_config_raw[name]
            grp = groups[name]

            if "source_groups" not in cfg:
                raise ConfigError(f"Config 'source_group' is not found in '{name}'")
            elif cfg["source_groups"]=="all_windows":
                zero_level_groups.append(grp)
            elif type(cfg["source_groups"]) is not list:
                raise ConfigError(
                    "The value of 'source_group' must be a list of group name or 'all_windows'"
                )
            elif len(cfg["source_groups"])==0:
                raise ConfigError("'source_groups' is empty")
            else:
                for source_name in cfg["source_groups"]:
                    if type(source_name) is not str:
                        raise ConfigError("Item of 'source_groups' must be str")
                    if source_name not in groups:
                        raise ConfigError(f"Source group '{source_name}' not found")
                    grp.source_groups.append(groups[source_name])
                    groups[source_name].sink_groups.append(grp)

            if "filter_when" in cfg:
                if type(cfg["filter_when"]) is not str:
                    raise ConfigError("Type of 'filter_when' must be str")
                
                if cfg["filter_when"] == "window_created":
                    grp.only_filter_when_window_created = True
                elif cfg["filter_when"] == "each_update":
                    grp.only_filter_when_window_created = False
                else:
                    ConfigError("Invalid value of 'filter_when'")
            else:
                grp.only_filter_when_window_created = True

            if "filter" not in cfg:
                pass
            elif type(cfg["filter"]) is not dict:
                raise ConfigError(
                    f"Incorrect type of config 'filter'. "
                    f"Expected 'dict', got '{type(cfg['filter']).__name__}'"
                )
            else:
                for filter_name in cfg["filter"]:
                    _filter = quacro_window_filters.generate_filter(
                        filter_name, 
                        cfg["filter"][filter_name],
                    )
                    grp.filters.append(_filter)
                # END for filter_name in cfg["filter"]
        # END for name in groups    

        # DFS, check if there are loop referenced groups or unused groups
        stack:list[WindowGrup] = [primary_group]
        walked_names:set[str] = set()
        while stack:
            poped = stack.pop()
            if poped.name in walked_names:
                raise ConfigError(f"Group '{poped.name}' loop referenced")
            walked_names.add(poped.name)
            stack.extend(poped.source_groups)
        
        all_names = set(groups)
        diff = all_names - walked_names
        if diff:
            raise ConfigError(f"Unused window group(s): {diff}")
        
        return groups,zero_level_groups,primary_group
    # END def load_window_filter_config
