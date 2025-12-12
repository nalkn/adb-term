#---------------------------------------------------------------------------------
# -*- coding: utf-8 -*-
# Python: 3.12.0
# Author: Killian Nallet
# Date: 13/10/2025
#---------------------------------------------------------------------------------


# imports
import os
import sys
import logging
from subprocess import run
import zipfile

from keyevents import KeyMap


# define constants
current_dir_path = os.path.dirname(__file__)
temp_extract_path = os.path.join(current_dir_path, ".temp", "extract")


# variables
_log = None


# define functions
def configure_logger(log_path:str):
    """Configure and return a logger for the tool"""

    global _log

    logger = logging.getLogger(__name__)
    logger.setLevel("DEBUG")
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    _log = logger
    return logger


_conf = {}

def adb_fncts_set_conf(conf):
    """Set the conf for adb functions"""
    global _conf
    _conf = conf


def _get_encoding():
    """Return correct subprocess encoding for a platform"""

    if sys.platform == "win32":
        return "cp437"
    else:
        return "utf-8"

def exec_cmd(command:list, get_result=False, nolog=False):
    """Executes a command and returns whether it was executed successfully (or its result)."""

    if not nolog:
        _log.info(f"exec {command}")

    result = run(
        command, 
        encoding=_get_encoding(),
        text=True,
        capture_output=True
    )

    if get_result:
        return result
    else:
        return result.returncode == 0


def restart_adb():
    """Restart (or start) the adb server"""

    exec_cmd(["adb", "kill-server"])
    return exec_cmd(["adb", "start-server"])


def ping_host(host_ip:str):
    """Ping a host ip on the current network"""

    return exec_cmd(["ping", host_ip, "-w", "550", "-n", "2"])


def cmd_adb_device():
    """Return a basic adb command with the current connected adb device ip"""

    return ["adb", "-s", _conf["ip"]]


def get_connected_devices():
    """Retrieve the list of currently connected adb devices"""

    # get adb devices
    result = exec_cmd(["adb", "devices"], get_result=True, nolog=True)
    
    # extract connected devices
    device_list = []
    for line in result.stdout.splitlines():
        if "\tdevice" in line:
            device_id = line.split("\t")[0]
            device_list.append(device_id)

    return device_list


def check_conn():
    """Check the connexion status of the selected adb device"""

    return f"{_conf['ip']}:{_conf['port']}" in get_connected_devices()


def adb_shell_cmd(command:list, get_result=False):
    """Execute a command in the adb shell on a connected adb device"""

    return exec_cmd(cmd_adb_device() + ["shell"] + command, get_result)


def adb_send_text(command:str):
    """Send text input to a connected adb device"""
    
    return adb_shell_cmd(["input", "text", f"'{command}'"]) # send command (with spaces into)


def adb_send_key(*keyevents:str, keycombination=False):
    """Send keyevent(s) input to a connected adb device"""
    
    if keycombination:
        sendkeys_mode = "keycombination"
        if len(keyevents) > 2:
            raise ValueError("keycombination needs at least 2 keys to send")
    else:
        sendkeys_mode = "keyevent"
    
    return adb_shell_cmd(["input", sendkeys_mode, *keyevents])


def adb_send_cmd(command:str):
    """Send a text command to execute on a connected adb device (for a terminal app like termux)"""
    
    return adb_send_text(command) and adb_send_key(KeyMap.enter)


def _extract_apkm_or_xapk(apkm_xapk_path:str) -> list:
    """Extract .apk files from .apkm file"""
    # thanks to : https://github.com/veryraregaming/Rares-Apkm-to-APK-GUI

    basename_apkm_xapk = os.path.splitext(os.path.basename(apkm_xapk_path))[0]
    _log.info(f"extracting {os.path.splitext(apkm_xapk_path)[1]} file '{basename_apkm_xapk}' to .apk files")

    # create temp extract dir
    extract_dir = os.path.join(temp_extract_path, basename_apkm_xapk)
    os.makedirs(extract_dir, exist_ok=True)

    # extract .apkm / .xapk in a temp folder (the same of .zip file)
    with zipfile.ZipFile(apkm_xapk_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    # list new .apk files
    return [os.path.join(extract_dir, f) for f in os.listdir(extract_dir) if f.endswith('.apk')]


def check_and_extract_apk(apk_path:str) -> str | list:
    """Check format of the apk and extract or convert it to a .apk file if is needed"""

    # get apk format
    apk_ext = os.path.splitext(apk_path)[1]

    # check apk format
    if apk_ext == ".apk":
        apk_files = [apk_path]

    elif apk_ext in [".apkm", ".xapk"]:
        print(f"[*] extracting .apk files from {apk_ext} archive ...")
        apk_files = _extract_apkm_or_xapk(apk_path)

    # return new .apk file(s)
    return apk_files


def adb_install_apk(apk_files:list, replace_apk=False, allow_downgrade=False):
    """Install apk file(s) on a connected adb device"""

    # Check apk format
    for apk_file in apk_files:
        apk_ext = os.path.splitext(apk_file)[1]
        if apk_ext != ".apk":
            raise ValueError(f"apk format (.{apk_ext}) is not supported with adb !")

#    apk_files = [f for f in apk_files if ("v7a" in f) or ("base" in f)]

    # Create install command
    if len(apk_files) > 1:
        install_command = ["install-multiple"] + apk_files
    else:
        install_command = ["install"] + apk_files

    # add replace / downgrade adb args
    if replace_apk: install_command.insert(1, "-r")
    if allow_downgrade: install_command.insert(1, "-d")

    # install apk
    return exec_cmd(cmd_adb_device() + install_command, get_result=True)


def extract_apk_id(apk_path:str):
    """Extract id from a .apk file"""

    # extract package Id
    result = exec_cmd(["aapt", "dump", "badging", apk_path], get_result=True)
    if result.returncode != 0:
        print(f"[-] cannot find apk id ({result.stderr.strip()})")
        return None

    # extract package id from stdout
    id_chrs_before, id_chrs_after = result.stdout.find("package: name='"), result.stdout.find("' versionCode=")
    package_id = result.stdout[id_chrs_before+15:id_chrs_after]

    return package_id


def adb_list_packages():
    """List all packages of a connected adb device"""

    # get installed packages
    _packages_id = adb_shell_cmd(["pm", "list", "packages"], True)

    # check returncode
    if _packages_id.returncode != 0:
        return []

    # extract packages from result
    packages_id = []
    for line in _packages_id.stdout.splitlines():
        packages_id.append(line.split("package:")[1])

    return packages_id


def adb_push_path(src:str, trg:str):
    """Push a file or a directory of files to a connected adb device"""

    return exec_cmd(cmd_adb_device() + ["push", src, trg])


def adb_pull_path(src:str, trg:str):
    """Pull a file or a directory of files from a connected adb device"""

    return exec_cmd(cmd_adb_device() + ["pull", src, trg])


def adb_disable_dev_opts():
    """Disable the dev options on a connected adb device"""

    return adb_shell_cmd(["settings", "put", "global", "development_settings_enabled", "0"])
