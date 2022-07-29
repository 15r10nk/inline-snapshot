from black import FileMode
from black import format_str


def format(text):
    return format_str(text, mode=FileMode())
