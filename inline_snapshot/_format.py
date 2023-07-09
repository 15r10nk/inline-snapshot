from black import main
from click.testing import CliRunner


def format_code(text, filename):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["--stdin-filename", str(filename), "-"], input=text)

    return result.stdout
