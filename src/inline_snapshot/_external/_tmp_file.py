__all__ = ("_tmp_file",)

from uuid import uuid4

from inline_snapshot._global_state import state


def generate_tmp_file():
    storage_dir = state().config.storage_dir
    assert storage_dir

    tmp_dir = storage_dir / "tmp"

    if not tmp_dir.exists():
        tmp_dir.mkdir(parents=True)
        gitignore = tmp_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# ignore all files in this directory\n*\n",
                "utf-8",
            )
    return tmp_dir / str(uuid4())
