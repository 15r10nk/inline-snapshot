

``` python exec="1"
from pathlib import Path
from subprocess import run
import re

new_changes = list(Path.cwd().glob("changelog.d/*.md"))
next_version = (
    run(["cz", "bump", "--get-next"], capture_output=True)
    .stdout.decode()
    .strip()
)

if new_changes:
    print(f"## upcoming version ({next_version})")

for file in new_changes:
    print(file.read_text())

full_changelog = Path("CHANGELOG.md").read_text()

full_changelog = re.sub("^#", "##", full_changelog, flags=re.M)

print(full_changelog)
```
