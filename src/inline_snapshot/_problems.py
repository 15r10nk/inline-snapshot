from typing import Callable

from rich.console import Console


def raise_problem(message):
    from inline_snapshot._global_state import state

    state().all_problems.add(message)


def report_problems(console: Callable[[], Console]):

    from inline_snapshot._global_state import state

    if not state().all_problems:
        return
    console().rule("[red]Problems")
    for problem in sorted(state().all_problems):
        console().print(f"{problem}")
        console().print()
