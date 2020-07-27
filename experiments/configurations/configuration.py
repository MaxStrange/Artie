"""
This file contains the code to load configuration files for a given experiment.
"""
import ast
import collections
import configparser
import importlib
import os
import shutil


class ConfigError(Exception):
    """
    An exception raised in the case of a problem with the configuration.
    """
    pass


class Configuration:
    """
    Exposes the raw configparser object via self.rawconfig, but also provides convenience
    methods that will help to parse the file and return more useful error messages to the
    user if things go wrong.
    """
    def __init__(self, rawconfigparser, config_file_path):
        self.rawconfig = rawconfigparser
        self.config_fpath = config_file_path

    def _sanity_check_args(self, section, value):
        """Throws an exception if section or value aren't in the config file."""
        if not section in self.rawconfig:
            raise ConfigError("Could not find section", section, "in config file. Available sections are:", self.rawconfig.sections())
        if not value in self.rawconfig[section]:
            raise ConfigError("Could not find value {} in section {}. Available values are: {}".format(value, section, [k for k in self.rawconfig[section]]))

    def getbool(self, section, value, default=None):
        """Attempts to get the value from section as a bool."""
        if default is not None:
            try:
                self._sanity_check_args(section, value)
            except ConfigError:
                return default
        else:
            self._sanity_check_args(section, value)

        if self.rawconfig[section][value].lower().startswith("true"):
            return True
        elif self.rawconfig[section][value].lower().startswith("false"):
            return False
        else:
            raise ConfigError("Could not determine truth value of {}. Try setting it to 'true' or 'false'.".format(self.rawconfig[section][value]))

    def getdict(self, section, value, default=None, none_okay=False):
        """
        Attempts to get the value from section as a dict.

        Evaluates the given dict using the ast module, so make sure it is trusted.
        """
        if default is not None:
            try:
                self._sanity_check_args(section, value)
            except ConfigError:
                return default
        else:
            self._sanity_check_args(section, value)

        rawdict = self.rawconfig[section][value]
        if rawdict.lower() == "none" and none_okay:
            return None
        elif rawdict.lower() == "none" and not none_okay:
            raise ConfigError(f"{section}: {value} cannot be parsed into a dict. Found value: {rawdict}")

        return make_dict_from_str(rawdict)


    def getint(self, section, value, none_okay=False, default=None):
        """Attempts to get the value from section as an int."""
        if default is not None:
            try:
                self._sanity_check_args(section, value)
            except ConfigError:
                return default
        else:
            self._sanity_check_args(section, value)

        try:
            return int(self.rawconfig[section][value])
        except ValueError as e:
            if self.rawconfig[section][value].lower() == "none" and none_okay:
                return None
            else:
                raise ConfigError("Could not convert {} to int. Error message: {}".format(self.rawconfig[section][value], e))

    def getfloat(self, section, value, none_okay=False, default=None):
        """Attempts to get the value from section as a float."""
        if default is not None:
            try:
                self._sanity_check_args(section, value)
            except ConfigError:
                return default
        else:
            self._sanity_check_args(section, value)

        try:
            return float(self.rawconfig[section][value])
        except ValueError as e:
            if self.rawconfig[section][value].lower() == "none" and none_okay:
                return None
            else:
                raise ConfigError("Could not convert {} to float. Error message: {}".format(self.rawconfig[section][value], e))

    def getlist(self, section, value, none_okay=False, default=None):
        """
        Attempts to parse value from section as a list of items.

        Uses ast to literal_eval. Make sure you trust the given string!
        """
        if default is not None:
            try:
                self._sanity_check_args(section, value)
            except ConfigError:
                return default
        else:
            self._sanity_check_args(section, value)

        configval = self.rawconfig[section][value].strip()
        if configval.lower() == "none":
            return None
        else:
            return make_list_from_str(configval)

    def getimportablelist(self, section, value, none_okay=False, default=None):
        """
        Attempts to get a list of importable objects and imports them, then
        returns the list of those items.
        """
        items = self.getlist(section, value, none_okay=True, default=default)
        if type(items) == list:
            items = [self._import_and_instantiate_from_string(s, section, value) for s in items]
        return items

    def getpath(self, section, value, default=None, should_exist=False):
        """
        Attempts to get a str from the given `section` and `value` as a path.
        Attempts to expand the path if it contains "~" or "$HOME" (or any other shell variables).

        If `should_exist` is `True`, we raise a `FileNotFoundException` if the item does not
        exist.
        """
        rawstr = self.getstr(section, value, default=default)
        if rawstr is None:
            return None

        path = os.path.expanduser(rawstr)
        path = os.path.expandvars(path)

        if should_exist and not os.path.exists(path):
            raise FileNotFoundError(f"File or directory {path} does not seem to exist.")

        return path

    def getstr(self, section, value, default=None):
        """Attempts to get the value from section as a str."""
        if default is not None:
            try:
                self._sanity_check_args(section, value)
            except ConfigError:
                return default
        else:
            self._sanity_check_args(section, value)

        return self.rawconfig[section][value].strip()

    def _import_and_instantiate_from_string(self, module_and_itemname: str, section: str, value: str):
        """
        """
        tmp = module_and_itemname.split('.')
        importpath = '.'.join(tmp[:-1])
        itemname = tmp[-1]
        try:
            mod = importlib.import_module(importpath)
        except ValueError:
            raise ConfigError(f"Could not load item {itemname} from module {importpath}. Section {section} and value {value}.")

        if not hasattr(mod, itemname):
            raise ConfigError(f"Could not load item {itemname} from module {importpath}. Section {section} and value {value}.")
        else:
            return getattr(mod, itemname)

    def getimportable(self, section, value, default=None):
        """
        Attempts to retrieve a string from section/value, then treat
        it as an item from a module that is importable. It attempts
        to import the module, then find the item in the module
        and return that item.

        For example, if the value is 'agent.dqn.dqn_loss', this
        will attempt to import a module 'agent.dqn' and then return
        the item called 'dqn_loss' in that module.
        """
        if default is not None:
            try:
                self._sanity_check_args(section, value)
            except ConfigError:
                return default
        else:
            self._sanity_check_args(section, value)

        module_and_itemname = self.rawconfig[section][value].strip()
        return self._import_and_instantiate_from_string(module_and_itemname, section, value)

    def save(self, fpath: str):
        """
        Saves the raw configuration file to the given `fpath` by copying
        it from its original location into the new location.
        """
        shutil.copyfile(self.config_fpath, fpath)


def load(fpath):
    """
    Loads the given `fpath`.

    If we can't find the file, we throw a ValueError.
    """
    if not os.path.isfile(fpath):
        raise ValueError("Could not find {} to load as a config file.".format(fpath))

    config = configparser.ConfigParser()
    config.read(fpath)
    return Configuration(config, fpath)

def make_dict_from_str(rawdict: str) -> dict:
    """
    Attempts to make a dict from the given string.
    """
    if not rawdict.strip().startswith("{"):
        raise ConfigError("A dict must start with '{{', but instead starts with {}".format(rawdict[0]))
    elif not rawdict.strip().endswith("}"):
        raise ConfigError("A dict must end with '}}', but instead starts with {}".format(rawdict[-1]))

    return ast.literal_eval(rawdict)

def make_list_from_str(s: str) -> list:
    """
    Attempts to make a list from the given string.

    Uses ast to literal_eval. Make sure you trust the given string!
    """
    return ast.literal_eval(s)
