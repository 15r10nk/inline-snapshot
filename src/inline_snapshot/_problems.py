from rich.console import Console

all_problems = set()


def raise_problem(message):
    all_problems.add(message)


def report_problems(console: Console):

    global all_problems
    if not all_problems:
        return
    console.rule("[red]Problems")
    for problem in all_problems:
        console.print(f"[b]{problem}")

    all_problems = set()
