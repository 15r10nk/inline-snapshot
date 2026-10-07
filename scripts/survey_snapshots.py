"""Survey imported snapshot() calls in tracked Python files of local repos.

Usage: python scripts/survey_snapshots.py [test-repos] > benchmarks/corpus.json
This reads existing checkouts only; it never fetches or executes their code.
"""

import argparse
import ast
import json
import subprocess
from collections import Counter
from pathlib import Path


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def survey(repo):
    calls = []
    skipped = []
    for filename in git(repo, "ls-files", "-z", "--", "*.py").split("\0"):
        if not filename:
            continue
        path = repo / filename
        try:
            tree = ast.parse(path.read_bytes(), filename=filename)
        except (SyntaxError, UnicodeError, OSError) as error:
            skipped.append({"file": filename, "reason": str(error)})
            continue
        aliases = set()
        modules = set()
        for node in ast.walk(tree):
            # pydantic-ai routes snapshots through tests/_inline_snapshot.py;
            # that wrapper imports the real API when recording is enabled.
            if isinstance(node, ast.ImportFrom) and node.module in {
                "inline_snapshot",
                "_inline_snapshot",
            }:
                aliases.update(
                    a.asname or a.name for a in node.names if a.name == "snapshot"
                )
            elif isinstance(node, ast.Import):
                modules.update(
                    a.asname or a.name
                    for a in node.names
                    if a.name == "inline_snapshot"
                )
        parents = {
            child: node
            for node in ast.walk(tree)
            for child in ast.iter_child_nodes(node)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Name)
                and func.id in aliases
                or isinstance(func, ast.Attribute)
                and func.attr == "snapshot"
                and isinstance(func.value, ast.Name)
                and func.value.id in modules
            ):
                continue
            argument = (
                node.args[0]
                if node.args
                else next((k.value for k in node.keywords if k.arg == "obj"), None)
            )
            nodes = list(ast.walk(argument)) if argument is not None else []
            parent = parents.get(node)
            calls.append(
                {
                    "file": filename,
                    "line": node.lineno,
                    "shape": (
                        type(argument.value).__name__
                        if isinstance(argument, ast.Constant)
                        else (
                            type(argument).__name__ if argument is not None else "empty"
                        )
                    ),
                    "ast_nodes": len(nodes),
                    "source_lines": node.end_lineno - node.lineno + 1,
                    "nested_calls": [
                        ast.unparse(n.func) for n in nodes if isinstance(n, ast.Call)
                    ],
                    "comparison": (
                        ",".join(type(op).__name__ for op in parent.ops)
                        if isinstance(parent, ast.Compare)
                        else "indirect"
                    ),
                }
            )

    def percentiles(key):
        values = sorted(call[key] for call in calls)
        return (
            {str(p): values[(len(values) - 1) * p // 100] for p in (50, 90, 99, 100)}
            if values
            else {}
        )

    return {
        "revision": git(repo, "rev-parse", "HEAD"),
        "tracked_changes": bool(
            git(repo, "status", "--porcelain", "--untracked-files=no")
        ),
        "calls": len(calls),
        "files": len({call["file"] for call in calls}),
        "shapes": dict(sorted(Counter(call["shape"] for call in calls).items())),
        "comparisons": dict(Counter(call["comparison"] for call in calls)),
        "nested_calls": Counter(
            name for call in calls for name in call["nested_calls"]
        ).most_common(15),
        "ast_nodes_percentiles": percentiles("ast_nodes"),
        "source_lines_percentiles": percentiles("source_lines"),
        "largest": [
            {k: v for k, v in call.items() if k != "nested_calls"}
            for call in sorted(calls, key=lambda call: call["ast_nodes"], reverse=True)[
                :3
            ]
        ],
        "skipped_files": skipped,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("test-repos"))
    args = parser.parse_args()
    repos = sorted(path for path in args.root.iterdir() if (path / ".git").exists())
    if not repos:
        parser.error(f"No Git checkouts found in {args.root}")
    print(
        json.dumps(
            {
                "method": "Static imported call sites in tracked Python files, including pydantic-ai's _inline_snapshot wrapper; not runtime frequencies. Aliases are resolved per file, without scope/shadowing analysis. Strings containing Python are not inspected.",
                "repositories": {repo.name: survey(repo) for repo in repos},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
