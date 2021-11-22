import re
import os
import json
import pathlib
import shutil
from datetime import datetime as dt
import numpy as np

SEPARATOR = (
    "================================================================================"
)


RE = r"[-+]? (?: (?: \d* \. \d+ ) | (?: \d+ \.? ) )(?: [Ee] [+-]? \d+ ) ?"
rx = re.compile(RE, re.VERBOSE)

ORDINAL = lambda n: "%d%s" % (
    n,
    "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
)

DTFORMAT = "%Y-%m-%d-%H-%M"


def clearTerminal():
    os.system("cls" if os.name == "nt" else "clear")


def isfile(path):
    return os.path.isfile(path)


def isdir(path):
    return os.path.isdir(path)


def now() -> str:
    return dt.now().strftime(DTFORMAT)


def homedir() -> str:
    return str(pathlib.Path.home())


def joinpath(directory, *the_rest) -> str:
    joined = directory
    for part in the_rest:
        joined = os.path.join(joined, part)
    return joined


def getFolderList(directory, reverse=False):
    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    FullPathList = [
        joinpath(directory, f) for f in os.listdir(directory)
    ]  # files and folders
    PathList = [f for f in FullPathList if isdir(f)]  # folders only
    PathList.sort(reverse=reverse)
    return PathList


def getFileList(directory, reverse=False):
    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    FullPathList = [
        joinpath(directory, f) for f in os.listdir(directory)
    ]  # files and folders
    PathList = [f for f in FullPathList if isfile(f)]  # folders only
    PathList.sort(reverse=reverse)
    return PathList


def getNameFromPath(FullPath, IncludeFileExtension=False):
    if IncludeFileExtension:
        file_name = pathlib.Path(FullPath).name
    else:
        file_name = pathlib.Path(FullPath).stem
    return file_name


def getDirFromPath(FullPath):
    return os.path.dirname(FullPath)


def mkdir(directory):
    created_now = False
    if not exists(directory):
        try:
            os.makedirs(directory)
            created_now = True
        except FileExistsError:
            pass
    return created_now


def rmdir(directory):
    removed_now = False
    if exists(directory):
        shutil.rmtree(directory)
        removed_now = True
    return removed_now


def exists(path):
    return os.path.exists(path)


class Stat:
    def __init__(self, np_array):
        if isinstance(np_array, list):
            np_array = np.array(np_array)
        self.max = np.nanmax(np_array, axis=0)
        self.min = np.nanmin(np_array, axis=0)
        self.mean = np.nanmean(np_array, axis=0)
        self.std = np.nanstd(np_array, axis=0, ddof=1)
        self.count = np.count_nonzero(~np.isnan(np_array))
        self.positive = ((~np.isnan(np_array)) & (np_array >= 0.001)).sum()


def jsondump(filepath, obj):
    with open(filepath, "w") as f:
        json.dump(vars(obj), f, indent=4, sort_keys=True, default=lambda o: vars(o))


def empty_dir(directory):
    rmdir(directory)
    mkdir(directory)


def empty_file(file):
    try:
        open(file, "w").close()
    except:
        pass


def write(filepath, message, mode="a", endl=False):
    try:
        with open(filepath, mode) as file:
            file.write(f"{message}\r\n" if endl else f"{message}")
    except:
        pass


def writeln(filepath, message="", mode="a"):
    write(filepath, message, mode=mode, endl=True)


class Writer:
    def __init__(self, filepath, sep="", empty=True):
        if empty:
            empty_file(filepath)
        self.filepath = filepath
        self.sep = sep

    def clean(self, message):
        cleaned = str(message)
        if self.sep != "" and self.sep in cleaned:
            cleaned = cleaned.replace(self.sep, " ")
        return cleaned

    def out(self, message):
        write(self.filepath, self.clean(message) + self.sep, "a")

    def outln(self, message=""):
        writeln(self.filepath, self.clean(message) + self.sep, "a")

    def outdict(self, messages: dict, condition=None):
        for key, val in messages.items():
            if condition and not condition(key, val):
                continue
            self.out(key)
            self.outln(str(val))

    def pretty_out(self, messages: list[str], max_words=None):
        if max_words is None:
            expected_chars = 100
            current_chars = ""
            for message in messages:
                current_chars += message
                if len(current_chars) < expected_chars:
                    self.out(message)
                else:
                    current_chars = ""
                    self.outln(message)
        else:
            current_words = 1
            for message in messages:
                if current_words < max_words:
                    current_words += 1
                    self.out(message)
                else:
                    current_words = 1
                    self.outln(message)

