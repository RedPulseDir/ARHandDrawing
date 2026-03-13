[app]
title = ARDrawing
package.name = ardrawing
package.domain = org.example
source.dir = .
source.include_exts = py
version = 1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 1

android.permissions = INTERNET
android.api = 31
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
