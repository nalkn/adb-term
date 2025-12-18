#---------------------------------------------------------------------------------
# -*- coding: utf-8 -*-
# Python: 3.12.0
# Author: Killian Nallet
# Date: 14/06/2025
#---------------------------------------------------------------------------------


# imports
import os
import json
import time
from dotenv import load_dotenv

import threading
from prompt_toolkit import PromptSession

from adb_functions import *
from config import env_file_path, check_dependencies_groups


# define constants
current_dir_path = os.path.dirname(__file__)

apks_folder_path = os.path.join(current_dir_path, "apks")
device_downloads_dir = "/storage/emulated/0/Download/" # refers to the termux internal storage : "~/storage/downloads/"
pc_downloads_dir = os.path.join(current_dir_path, "adb-downloads")

conf_path = os.path.join(current_dir_path, "data", "adb_term_conf.json")
log_path = os.path.join(current_dir_path, "data", "adb_term.log")


# define variables
conf = {}
event_device_connected = threading.Event()
event_exit = threading.Event()


# initialise PromptSession for for non-blocking input
session = PromptSession()

class PromptExit(Exception):
    """Exception used to exit the PromptSession"""

    pass


# define functions
def load_conf():
    """Load the conf from a json file"""
    global conf

    with open(conf_path, "r") as file_conf: # load conf
        conf = json.load(file_conf)

    adb_fncts_set_conf(conf)

def save_conf():
    """Save the actual conf in a json file"""

    with open(conf_path, "w") as file:
        json.dump(conf, file, indent=4)

    adb_fncts_set_conf(conf)

def reconnect_device():
    """Reconnect the selected adb decice if it is disconnect"""

    # set the reconnect event
    event_device_connected.set()

    # reconnect loop
    while not event_exit.is_set():

        # check the connexion
        if check_conn():
            if not event_device_connected.is_set():
                print("\n[+] device reconnected")
            event_device_connected.set()

        else:
            # disconnected
            if event_device_connected.is_set():
                session.app.exit(exception=PromptExit())

                while session.app.is_running:
                    time.sleep(0.1)
                if not event_exit.is_set():
                    print("\n[!] device disconnected")

            event_device_connected.clear()

        # wait
        time.sleep(0.5)


# check and load env (for programs default paths)
if os.path.exists(env_file_path):
    load_dotenv()
else:
    print("Execute the config.py file to configure this tool")


# configure logger
log = configure_logger(log_path)

# check tool dependencies
check_dependencies_groups(log)

# start adb
print(f"[*] starting adb")
restart_adb()

# check program conf
if os.path.exists(conf_path):
    load_conf()

# pair new device and write conf
else:
    # get pair infos
    print("[*] pair a new device")
    conf = {}
    conf["ip"] = input("[?] device ip: ")
    conf["port"] = None
    pair_port = input("[?] device pair port: ")
    pair_code = input("[?] device pair code: ")
    save_conf()

    # pair device
    if exec_cmd(["adb", "pair", conf["ip"]+":"+pair_port, pair_code]):
        print("[+] new device paired")
    else: 
        print("[-] pair of new device failed !"); exit()


# connect device loop
while True:

    # search device
    print(f"\nSearching device {conf["ip"]}")
    ping_ip = ping_host(conf["ip"]) # ping ip (check if ip is valid on the local network)

    if ping_ip:
        # connect device
        print("[*] connecting to device")
        if not check_conn():
            
            # check port
            if conf["port"] is None:
                conf["port"] = input("[?] device connect port: ")
                save_conf()

            # try connect
            exec_cmd(["adb", "connect", conf["ip"]+":"+conf["port"]])
            device_connected = check_conn() # test shell access

    else:
        print("[!] device not found")
        device_connected = False

    # retype and save device infos
    if conf["port"] is None or not device_connected:
        print("[-] connect device failed") if conf["port"] is not None else None

        # try to connect a new port
        print("[*] input device infos :")
        if not ping_ip:
            ip = input(f"[?] device ip ({conf['ip']}) -> ")
            conf["ip"] = ip if ip != "" else conf["ip"]

        connect_port = input("[?] device connect port: ")
        conf["port"] = connect_port if connect_port != "" else conf["port"]
        save_conf()

    # device connected
    else:
        print("[+] device connected\n")
        break


# start reconnect thread
threading.Thread(target=reconnect_device, daemon=True).start()

# loop for send commands
print(f"[*] session started with {conf['ip']}")

while True:

    # wait reconnect
    if not event_device_connected.is_set():
        print(f"Reconnecting device {conf['ip']}...")
        try:
            while not event_device_connected.is_set(): 
                time.sleep(0.1)
        except KeyboardInterrupt: 
            break

    # interactive prompt
    try:
        send_crtlc = False
        cmd = session.prompt("adb-term> ").strip()

    except PromptExit:
        if not event_device_connected.is_set():
            continue

    except KeyboardInterrupt: # ctrl-c
        send_crtlc = True

    except EOFError: # ctrl-d (from session.prompt())
        event_exit.set()
        break


    # ctrl-C
    if send_crtlc:
        adb_send_key(KeyMap.ctrl_right, KeyMap.c, keycombination=True)
        print("\rKeyboardInterrupt -> [Ctrl-c] send to device")
        continue


    # no command
    if cmd == "":
        adb_send_key(KeyMap.enter) # enter

    # quit this program
    elif cmd == ".quit":
        break


    # on / off screen
    elif cmd == ".on_screen":
        adb_send_key(KeyMap.power)

    elif cmd == ".off_screen":
        adb_send_key(KeyMap.endcall) # or soft_sleep


    # disable dev options
    elif cmd == ".dev-off":
        if adb_disable_dev_opts():
            print("-> dev options are disabled")


    # get devices
    elif cmd.startswith(".get-devices"):
        # get devices
        #TODO: set connected device
        print(get_connected_devices())


    # set user password (termux)
    elif cmd.startswith(".termux-passwd "):
        # get passwd
        passwd = cmd.split(".termux-passwd ")[1]
        # change passwd
        if adb_send_cmd("passwd") and adb_send_cmd(passwd) and adb_send_cmd(passwd): # retype password
            print("[*] password set")
            save_conf()


    # install apk
    elif cmd.startswith(".install "):
        # get apk
        apk_filename = cmd.split(".install ")[1]
        apk_exts = [".apk", ".apkm", ".xapk"]
        apk_filenames = [apk_filename+ext for ext in apk_exts]
        apk_path = None

        # check if the path is valid
        if os.path.exists(apk_filename):
            if os.path.isfile(apk_filename):
                apk_ext = os.path.splitext()[1]
                if apk_ext in apk_exts:
                    apk_path = apk_filename
                else:
                    print(f"[!] .{apk_ext} files are not supported")
            else:
                print(f"[!] {apk_filename} is not a file")

        # search apk in apk dirs
        else:
            # recursive search
            for search_dir, _, files in os.walk(apks_folder_path):
                for file in files:
                    if apk_filename == file:
                        pass # ok
                    elif file in apk_filenames:
                        apk_filename = file # ok
                    else: 
                        continue
                    apk_path = os.path.join(current_dir_path, search_dir, apk_filename)
                    break

                # if no break
                else:
                    continue

                # if a break, quit loop
                break

        # install apk
        if apk_path is not None:
            print(f"[*] installing '{apk_filename}' on {conf["ip"]}")

            # extract or convert the apk file if needed
            install_start = time.time()
            apk_files = check_and_extract_apk(apk_path)

            # check if the package is already installed
            replace_apk = False
            try: apk_id = extract_apk_id(apk_files[1] if len(apk_files) > 1 else apk_files[0])
            except: apk_id = None

            if (apk_id is not None) and (apk_id in adb_list_packages()):
                print("[!] This apk is already installed on device")
                if input("[?] Install the new apk without erasing old apk data (-> apk update) ? [y/n] ") in ["y", "yes"]:
                    replace_apk = True

            # try install and get result
            result = adb_install_apk(apk_files, replace_apk)
            if result.returncode == 0: # no error
                print(f"[+] apk '{apk_filename}' installed in {time.time()-install_start:.1f}s")
                continue

            # error occured
            else:
                # strip error
                err = result.stderr.strip()

                # downgrade detected
                if "INSTALL_FAILED_VERSION_DOWNGRADE" in err and "Downgrade detected" in err:

                    # try reinstall with downgrade
                    print("[!] Downgrade detected")
                    if input("[?] Install this old apk version ? [y/n] ") in ["yes", "y"]:
                        print(f"[*] installing '{apk_filename}'")
                        result = adb_install_apk(apk_files, replace_apk, allow_downgrade=True)
                        if result.returncode == 0: # no error
                            print(f"[+] apk '{apk_filename}' installed in {time.time()-install_start:.1f}s")
                        else:
                            print(f"[-] install apk failed ({result.stderr.strip().replace("\n", "")})")

                    # install (downgrade) cancelled
                    else:
                        print(f"[-] install apk cancelled")

                # other error in install apk
                else:
                    print(f"[-] install apk failed ({err})")

        # apk not found
        else:
            print(f"[!] apk '{apk_filename}' not found")


    # push files
    elif cmd.startswith(".push "):
        # get file / dir
        src_path = cmd.split(".push ")[1]

        # check if the file exists
        if not os.path.exists(src_path):
            print(f"[!] the path {src_path} don't exists, cannot push this")
            continue

        # choose trg path
        print(f"[*] By default, push path to \"{device_downloads_dir}\"")
        try: trg_dir = input("[?] New target path (empty=default): ") or device_downloads_dir
        except KeyboardInterrupt: continue
        trg_path = os.path.join(trg_dir, os.path.basename(src_path))

        # send file
        print(f"[*] pushing '{src_path}' to the device")
        if adb_push_path(src_path, trg_path):
            print(f"[+] path pushed to \"{trg_path}\"")
        else:
            print("[-] push of path failed")


    # pull files
    elif cmd.startswith(".pull "):
        # choose trg path
        print(f"[*] By default, path are pulled from \"{device_downloads_dir}\"")
        try: src_device = input("[?] New source path (empty=default): ") or device_downloads_dir
        except KeyboardInterrupt: continue

        # get file / dir
        src_path = os.path.join(src_device, cmd.split(".pull ")[1])
        pc_downloads_path = os.path.join(pc_downloads_dir, os.path.basename(src_path))

        # check download dir
        if not os.path.exists(pc_downloads_dir):
            os.mkdir(pc_downloads_dir)

        # pull file
        print(f"[*] pulling '{src_path}' from the device")
        if adb_pull_path(src_path, pc_downloads_path):
            print(f"[+] path pulled to {pc_downloads_path}")
        else:
            print("[-] pull of path failed")


    # execute command
    else:
        adb_send_cmd(cmd)
