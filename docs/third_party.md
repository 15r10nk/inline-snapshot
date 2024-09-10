
Third-party extensions can be used to enhance the testing experience with other frameworks.
The goal of inline-snapshot is to provide the core functionality for many different use cases.

List of current third-party extensions:

<!--[[[cog
from lxml import html
import requests
import cog

response = requests.get("https://pypi.org/simple/")

tree = html.fromstring(response.content)

package_list = [str(package) for package in tree.xpath('//a/text()') if str(package).startswith("inline-snapshot")]



for package_name in package_list:
    if package_name == "inline-snapshot":
        continue

    r = requests.get(f'https://pypi.org/pypi/{package_name}/json', headers = {'Accept': 'application/json'});

    summary=r.json()['info']["summary"]
    cog.out(f"* [{package_name}](https://pypi.org/project/{package_name}/) {summary}")

]]]-->
* [inline-snapshot-pandas](https://pypi.org/project/inline-snapshot-pandas/) pandas integration for inline-snapshot (insider only)
<!--[[[end]]]-->


!!! info "How to add your extension to this list?"
    Your package name has to start with `inline-snapshot-` and has to be available on [PyPI](https://pypi.org).
    The summary of your package will be used as description.

    I will update this list from time to time but you can accelerate this process by creating a new [issue](https://github.com/15r10nk/inline-snapshot/issues).
