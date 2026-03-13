[app]
title = AR Hand Drawing
package.name = arhanddrawing
package.domain = org.arhand
source.dir = .
source.include_exts = py
version = 1.0
requirements = python3,kivy,android,pyjnius
orientation = portrait
fullscreen = 1

android.permissions = CAMERA,INTERNET
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.branch = master
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
