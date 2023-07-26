"""App version string"""

import os


path = os.path.dirname(os.path.dirname(__file__))
VERSION_FILE = f"{path}/VERSION"
with open(VERSION_FILE, "rt", encoding="utf-8") as file1:
    VERSION = file1.read()

_ver = VERSION.split(".")
if _ver is not None and len(_ver) > 2:
    VER_MAJOR = int(_ver[0])
    VER_MINOR = int(_ver[1])
    VER_PATCH = "".join(_ver[2:]).rstrip()
    API_VERSION = VER_MAJOR
    __version__ = f"{VER_MAJOR}.{VER_MINOR}.{VER_PATCH}"

else:
    raise RuntimeError(f"Unable to find version string in {VERSION_FILE}.")


if __name__ == "__main__":
    print(__version__)
