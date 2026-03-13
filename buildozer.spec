[app]
title = ARDrawing
package.name = ardrawing
package.domain = org.example
source.dir = .
source.include_exts = py
version = 1.0
requirements = python3,kivy==2.2.1,pillow
orientation = portrait
fullscreen = 1

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True

p4a.branch = master
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
