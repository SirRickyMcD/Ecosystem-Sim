[app]

# (str) Title of your application
title = Ecosystem Sim

# (str) Package name
package.name = ecosystemsim

# (str) Package domain (needed for android packaging)
package.domain = org.nexus

# (list) Source files to include (let it include python files)
source.include_exts = py,png,jpg,kv,atlas

# (list) Application requirements
# Note: python3, pygame, and numpy are required
requirements = python3,pygame,numpy

# (str) Supported orientations (landscape is ideal for this simulation)
orientation = landscape

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support
android.minapi = 21

# (bool) If True, then application is full screen
fullscreen = 1

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2
