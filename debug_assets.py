from pathlib import Path
import os
from src import theme

print("CWD:", os.getcwd())
print("WWW_DIR:", theme.WWW_DIR)
print("VIDEO_PATH:", theme.VIDEO_PATH, "=>", "FOUND" if theme.VIDEO_PATH.exists() else "MISSING")
print("BANNER_LOGO_PATH:", theme.BANNER_LOGO_PATH, "=>", "FOUND" if theme.BANNER_LOGO_PATH.exists() else "MISSING")
print("ICON_LOGO_PATH:", theme.ICON_LOGO_PATH, "=>", "FOUND" if theme.ICON_LOGO_PATH.exists() else "MISSING")
