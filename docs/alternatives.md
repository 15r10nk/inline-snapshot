inline-snapshot is not the only snapshot testing library for Python.
There are several others to:

<!--[[[cog
import cog
from urllib.parse import urlencode

packages = [
    ("syrupy", "https://github.com/syrupy-project/syrupy"),
    ("snapshottest", "https://github.com/syrusakbary/snapshottest"),
    ("pytest-snapshot", "https://github.com/joseph-roitman/pytest-snapshot"),
    ("pytest-insta", "https://github.com/vberlier/pytest-insta"),
    ("pytest-accept", "https://github.com/max-sixty/pytest-accept"),
]

for name, url in packages:
    cog.out(f"* [{name}]({url})\n")


query = urlencode(
    [
        ("packages", package)
        for package in ["inline-snapshot", *[name for name, _ in packages]]
    ]
    + [("time_range", "2years")]
)

cog.out(
    f"""
<iframe
    src="https://pypacktrends.com/embed?{query}"
    width="100%"
    height="520"
    frameborder="0"
>
</iframe>
"""
)
]]]-->
* [syrupy](https://github.com/syrupy-project/syrupy)
* [snapshottest](https://github.com/syrusakbary/snapshottest)
* [pytest-snapshot](https://github.com/joseph-roitman/pytest-snapshot)
* [pytest-insta](https://github.com/vberlier/pytest-insta)
* [pytest-accept](https://github.com/max-sixty/pytest-accept)

<iframe
    src="https://pypacktrends.com/embed?packages=inline-snapshot&packages=syrupy&packages=snapshottest&packages=pytest-snapshot&packages=pytest-insta&packages=pytest-accept&time_range=2years"
    width="100%"
    height="520"
    frameborder="0"
>
</iframe>
<!--[[[end]]]-->
