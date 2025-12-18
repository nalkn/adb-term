#---------------------------------------------------------------------------------
# -*- coding: utf-8 -*-
# Python: 3.12.0
# Author: Killian Nallet
# Date: 25/08/2025
#---------------------------------------------------------------------------------


# imports
import os
import shutil
import dotenv
import logging


# define constants
current_dir_path = os.path.dirname(__file__)
env_file_path = os.path.join(current_dir_path, ".env")

dependencies_groups = [

    {
        "name": "platform-tools",
        "tools": [
            "adb"
        ],
        "env_key": "PLATFORMTOOLS_PATH"
    },

    {
        "name": "build-tools",
        "tools": [
            "aapt", 
        ],
        "env_key": "BUILDTOOLS_PATH"
    }
]


# define function
def _recursive_search_tool(tool:str, search_folder:str):
    """Recursively search a tool in a folder"""

    for path, _, _ in os.walk(search_folder):
        if shutil.which(tool, path=path) != None:
            return True

    return False

def check_miss_dependencies(_deps_group:dict, search_folder:str=None):
    """Check if a group of dependencies are in the PATH (or in a folder path) and return a lidt of missing tools"""

    # extract tools list
    required_tools = _deps_group["tools"]

    # check tools of dependencies_group
    missing_tools = []
    for required_tool in required_tools:

        # search recursively the tool from the search_folder
        if search_folder != None:
            if not _recursive_search_tool(required_tool, search_folder):
                missing_tools.append(required_tool)

        # search the tool is in the PATH
        else:
            if shutil.which(required_tool) is None:
                missing_tools.append(required_tool)

    return missing_tools

def check_dependencies_groups(log:logging.Logger):
    """Check the dependensies of this tool and add the tools paths to the PATH"""

    print("[*] Checking dependencies")

    # check tools in each dependencies groups
    all_miss_deps = []
    for deps_group in dependencies_groups:

        # check a group (in the same folder)
        deps_group_folder = os.getenv(deps_group["env_key"])
        miss_deps = check_miss_dependencies(deps_group, deps_group_folder)

        # add missing tools to a global list
        if miss_deps != []:
            all_miss_deps += miss_deps

        # add it to the PATH
        else:
            # if program are already in the path, deps_group_folder is None
            if deps_group_folder is None:
                deps_group_folder = "the PATH"
            else:
                os.environ["PATH"] += ";"+deps_group_folder

            # log found tools
            log.info(f"{", ".join(deps_group["tools"])} found in {deps_group_folder}")

    # if some tools are missing
    if all_miss_deps != []:
        # log missing tools
        for miss_dep in all_miss_deps:
            log.critical(f"{miss_dep} is not found on your computer")

        # print missing tools
        print(f"[-] {", ".join(all_miss_deps)} : not found on your computer, check your .env file")
        exit()


# main function
def main():

    # change default search dir (os.path.exists and os.path.isfile)
    root_path = "".join(os.path.splitroot(__file__)[:2])
    os.chdir(root_path) # Linux : "/", Winwows: "C:\"

    # search tools path
    print(f"\n[*] Type required tools paths")

    # first check tools (to store them after)
    dependencies_paths = []
    for deps_group in dependencies_groups:

        # define some text to display
        all_tools_txt = ", ".join(deps_group["tools"])
        nb_tools = len(deps_group["tools"])
        used_tools_txt = f" (used for {all_tools_txt})" if nb_tools < 1 else "" # no print that if less 1 tool (name gp = tool)

        # check if the dependencies of the group are in the path
        if check_miss_dependencies(deps_group) == []:
            print(f"[+] Tool{'s' if nb_tools > 1 else ''} {all_tools_txt} are present in the PATH")

        else:
            # give the path (folder)
            while True:
                try:
                    folder_path = input(f"[?] Enter the path of {deps_group["name"]} folder{used_tools_txt}: ")
                except KeyboardInterrupt:
                    print("\n[!] Program exit")
                    exit()

                # check if the path exists
                if os.path.exists(folder_path):

                    # if is filepath : get a directory
                    if os.path.isfile(folder_path):
                        folder_path = os.path.dirname(folder_path)

                    # check dependencies with the new path
                    miss_deps = check_miss_dependencies(deps_group, search_folder=folder_path)
                    if miss_deps != []:
                        print(f"[!] missing {", ".join(miss_deps)} in '{folder_path}'")
                        exit()
                    else:
                        # add dependencies group path
                        dependencies_paths.append((deps_group["env_key"], folder_path))
                        break

                # the path given is not valid
                else:
                    print("[!] The path given is not valid")

    # store .env file
    print("\n[*] Saving .env file")

    for key, path in dependencies_paths:
        dotenv.set_key(
            env_file_path, 
            key, 
            path.rstrip("\\") # in Windows, delete the last "\" of the folder path (may break the .env file)
        )

    print("[+] .env file saved")


# main
if __name__ == "__main__":
    main()
