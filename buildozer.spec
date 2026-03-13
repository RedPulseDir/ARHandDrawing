[app]
title = AR Drawing
package.name = ardrawing
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 1
android.permissions = CAMERA
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
p4a.branch = master
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
