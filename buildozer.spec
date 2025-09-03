[app]

# (str) Title of your application
title = 校园签到系统

# (str) Package name
package.name = signinapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.example

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
#source.exclude_dirs = tests, bin

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 1.0

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,requests,pycryptodome,yagmail

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivy = ../../kivy

# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

#
# OSX Specific
#

#
# author = © Copyright Info

# (str) App longer description
#description = 

# (str) On OSX, the background image for the .app bundle
#osx.background_image = 

# (str) On OSX, the background color of the .app bundle
#osx.background_color = #FFFFFF

# (str) On OSX, the background color of the .app bundle content area
#osx.background_color_content = #FFFFFF

# (str) On OSX, the position of the .app bundle content area
#osx.background_content_position = 0,0

# (str) On OSX, the minimum version of OSX required
#osx.min_osx_version = 10.7

# (bool) On OSX, indicates whether the application should be started in fullscreen
#osx.fullscreen = 0

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for new android toolchain)
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray,
# darkgray, grey, lightgrey, darkgrey, aqua, fuchsia, lime, maroon, navy,
# olive, purple, silver, teal.
#android.presplash_color = #FFFFFF

# (list) Permissions
android.permissions = INTERNET

# (int) Target Android API, should be as high as possible.
#android.api = 27

# (int) Minimum API your APK will support.
#android.minapi = 21

# (int) Android SDK version to use
#android.sdk = 20

# (str) Android NDK version to use
#android.ndk = 19b

# (int) Android NDK API to use. This is the minimum API your app will support, it should usually match android.minapi.
#android.ndk_api = 21

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_path =

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you do not want to wait for it.
#android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only. If set to False,
# the default, you will be shown the license when first running
# buildozer.
#android.accept_sdk_license = False

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.renpy.android.PythonActivity

# (str) Android app theme, default is ok for Kivy-based app
# android.apptheme = "@android:style/Theme.NoTitleBar"

# (list) Pattern to whitelist for the whole project
#android.whitelist =

# (str) Path to a custom whitelist file
#android.whitelist_src =

# (str) Path to a custom blacklist file
#android.blacklist_src =

# (list) List of Java .jar files to add to the libs so that gradle can compile them.
#android.add_jar = 

# (list) List of Java files to add to the android project (can be java or aar)
#android.add_src =

# (list) List of Java .jar files to add to the libs so that gradle can package them.
#android.add_libs_jar = 

# (list) List of Java .jar files to add to the libs so that gradle can package them.
#android.add_libs_aar = 

# (list) List of gradle plugins to add
#android.add_gradle_plugins =

# (list) The libraries to compile and include in the APK
#android.add_libs = 

# (list) The shared libraries to include in the APK
#android.add_shlibs = 

# (list) Java classes to add as activities to the manifest.
#android.add_activities = 

# (str) OUYA Console category. For example: GAME or APP
# If you leave this blank, OUYA support will not be enabled
#android.ouya.category =

# (str) Filename of OUYA Console icon. It must be a 732x412 png image.
#android.ouya.icon.filename =

# (str) XML file to include as an intent filters in the activity
#android.manifest.intent_filters =

# (str) launchMode to set for the main activity
#android.manifest.launch_mode =

# (list) Android additional libraries to copy into libs/armeabi
#android.add_libs_armeabi = 
#android.add_libs_armeabi_v7a = 
#android.add_libs_arm64_v8a = 
#android.add_libs_x86 = 
#android.add_libs_x86_64 = 
#android.add_libs_mips = 
#android.add_libs_mips64 = 

# (bool) Indicate whether the screen should stay on
# Don't forget to add the WAKE_LOCK permission if you set this to True
#android.wakelock = False

# (list) Android (meta-data) to add (only for GooglePlay)
#android.meta_data =

# (list) Android (resources) to add (only for GooglePlay)
#android.resources =

# (list) Android (features) to add (only for GooglePlay)
#android.features =

# (list) Android (expandable list of resource) to add (only for GooglePlay)
#android.expandable_list =

# (str) BSD license id (for GooglePlay)
#android.license_id =

# (str) Android Keystore path (if empty, will skip the signing process)
#android.keystore_path =

# (str) Android Keystore alias (if empty, will be set to the package name)
#android.keystore_alias =

# (str) Android Key password (if empty, will be set to the keystore password)
#android.key_password =

# (str) Android Keystore password
#android.keystore_password =

# (str) Android signing certificate owner
#android.certificate_owner =

# (int) Android signing certificate validity (in years)
#android.certificate_validity =

# (bool) If set to True, then the APK will be installed on the device/emulator without verification
#android.nosign = False

#
# Python for android (p4a) specific
#

# (str) python-for-android branch to use, defaults to stable
#p4a.branch = stable

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
#p4a.source_dir =

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# Defaults to the first found in the following list: arm64-v8a, armeabi-v7a, x86_64, x86
#arch = armeabi-v7a

# (int) overrides API version for Python
#p4a.min_api = 21

# (int) overrides API version for Android
#p4a.android_api = 27

# (int) overrides API version for NDK
#p4a.ndk_api = 21

# (bool) If True, enables AndroidX support (default is false)
#p4a.androidx = False

# (bool) If True, enables --use-idna
#p4a.use_idna = False

# (bool) If True, enables --use-deprecated-python (for older Python versions)
#p4a.use_deprecated_python = False

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2