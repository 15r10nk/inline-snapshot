is_insider = False

insider_version = ""

__version__ = "0.27.2"

if is_insider:
    __version__ += "." + insider_version
