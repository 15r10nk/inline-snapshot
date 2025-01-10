import re
import sys


def replace_words(file_path, replacements):
    with open(file_path) as file:
        content = file.read()

    for old_word, new_word in replacements.items():
        content = re.sub(rf"\b{re.escape(old_word)}\b", new_word, content)

    with open(file_path, "w") as file:
        file.write(content)


if __name__ == "__main__":

    replacements = {
        "http://localhost:8000/inline-snapshot/": "https://15r10nk.github.io/inline-snapshot/latest/",
    }

    for file_path in sys.argv[1:]:
        print(file_path)
        replace_words(file_path, replacements)
