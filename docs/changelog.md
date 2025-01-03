

``` python exec="1"
from pathlib import Path

new_changes = list(Path.cwd().glob("changelog.d/*.md"))

if new_changes:
    print("# upcomming changes")

for file in new_changes:
    print(file.read_text().replace("###", "##"))
```


--8<-- "CHANGELOG.md"
