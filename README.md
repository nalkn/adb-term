# ADB Terminal

A python tool for install .apk .apkm .xapk files with adb.

## Requirements

Install [platform-tools](https://developer.android.com/tools/releases/platform-tools?hl=fr) (for adb)

Install [build-tools](https://androidsdkmanager.azurewebsites.net/build_tools.html) (for aapt)

NOTE : Platform-tools and build-tools can be otherwise downloaded with the Android Studio Sdk Manager.

## Usage

The `adb_terminal` tool uses .env file for practical and privacy reasons. You must first run the config.py file to configure the paths (stored in the .env file) of the required programs.

Configure the .env file (for dependencies) :

``` shell
python3 config.py
```

Start the main program :

``` shell
python3 adb_term.py
```

## Sources

Thanks to this project :

- [Rares-Apkm-to-APK-GUI](https://github.com/veryraregaming/Rares-Apkm-to-APK-GUI)
