pytest_plugins = "pytester"

import black

black.files.find_project_root = black.files.find_project_root.__wrapped__  # type: ignore
