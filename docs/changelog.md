

``` python exec="1"
from pathlib import Path
from subprocess import run

new_changes = list(Path.cwd().glob("changelog.d/*.md"))
next_version = (
    run(["cz", "bump", "--get-next"], capture_output=True)
    .stdout.decode()
    .strip()
)

if new_changes:
    print(f"# upcomming version ({next_version})")

for file in new_changes:
    print(file.read_text().replace("###", "##"))
```


--8<-- "CHANGELOG.md"
