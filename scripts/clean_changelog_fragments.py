import re
import sys


def clean_changelog_fragment(file_path):
    with open(file_path, encoding="utf-8", newline="") as file:
        content = original_content = file.read()

    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Remove HTML comments (both single-line and multi-line)
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

    # Remove excess blank lines left behind (more than two consecutive newlines)
    content = re.sub(r"\n{3,}", "\n\n", content)

    content = content.strip()
    if content:
        content += "\n"

    if original_content != content:
        with open(file_path, "w", encoding="utf-8", newline="\n") as file:
            print("change:", file_path)
            file.write(content)


if __name__ == "__main__":
    for file_path in sys.argv[1:]:
        clean_changelog_fragment(file_path)
