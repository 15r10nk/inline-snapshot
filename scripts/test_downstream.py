#!/usr/bin/env python3
"""
Test inline-snapshot in downstream repositories before a release.

Usage:
    uv run scripts/test_downstream.py [REPO_NAME ...]

With no arguments all configured repos are tested. Pass one or more repo
names (keys from REPOS below) to test only those.

Each repo is cloned into test-repos/<name> (shallow, depth=1) the first
time and pulled on subsequent runs.  The local inline-snapshot source tree
is injected via `uv`'s `--override` / path-dependency mechanism so the
downstream tests always run against the current checkout.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
REPOS_DIR = ROOT / "test-repos"
REPOS_JSON = ROOT / "test-repos.json"
REPOS: dict[str, dict] = json.loads(REPOS_JSON.read_text())


def save_repos() -> None:
    REPOS_JSON.write_text(json.dumps(REPOS, indent=2) + "\n")


def git_head(repo_dir: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True
    ).strip()


# uv ignores VIRTUAL_ENV when it doesn't match the project's own .venv.
# Strip it so downstream repos don't inherit the inline-snapshot venv.
_ENV = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}


def run(
    cmd: list[str], cwd: Path, check: bool = True, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    env = {**_ENV, **(extra_env or {})}
    return subprocess.run(cmd, cwd=cwd, check=check, env=env)


def clone_or_update(name: str, cfg: dict) -> Path:
    url = cfg["url"]
    ref = cfg.get("ref")
    repo_dir = REPOS_DIR / name

    if repo_dir.exists():
        if ref:
            print(f"\n[{name}] Checking out pinned ref {ref[:12]} …")
            run(["git", "fetch", "--depth=1", "origin", ref], cwd=repo_dir)
            run(["git", "checkout", ref], cwd=repo_dir)
        else:
            print(f"\n[{name}] Updating existing clone …")
            run(["git", "pull", "--ff-only"], cwd=repo_dir)
    else:
        REPOS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\n[{name}] Cloning {url} …")
        run(["git", "clone", "--depth=1", url, str(repo_dir)], cwd=REPOS_DIR)

        # Record the HEAD commit so future runs use the same baseline.
        head = git_head(repo_dir)
        print(f"\n[{name}] Pinning ref to {head[:12]}")
        REPOS[name]["ref"] = head
        save_repos()

    return repo_dir


def run_tests(
    name: str, repo_dir: Path, pytest_args: list[str], extra_env: dict | None = None
) -> bool:
    print(f"\n{'='*60}")
    print(f"  Running tests for: {name}")
    print(f"{'='*60}")
    result = run(
        ["uv", "run", "--with", f"inline-snapshot @ {ROOT}", "pytest", *pytest_args],
        cwd=repo_dir,
        check=False,
        extra_env=extra_env,
    )
    ok = result.returncode == 0
    status = "✓ PASSED" if ok else "✗ FAILED"
    print(f"\n[{name}] {status} (exit code {result.returncode})")
    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repos",
        nargs="*",
        help="Names of repos to test (default: all). Available: " + ", ".join(REPOS),
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Skip git pull on already-cloned repos.",
    )
    args = parser.parse_args()

    names = args.repos or list(REPOS.keys())
    unknown = set(names) - set(REPOS.keys())
    if unknown:
        print(f"Unknown repo(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        print(f"Available: {', '.join(REPOS)}", file=sys.stderr)
        sys.exit(1)

    results: dict[str, bool] = {}

    for name in names:
        cfg = REPOS[name]
        try:
            repo_dir = REPOS_DIR / name
            if args.no_update and repo_dir.exists():
                print(f"\n[{name}] Using existing clone (--no-update).")
                already_cloned = True
            else:
                already_cloned = repo_dir.exists()
                repo_dir = clone_or_update(name, cfg)

            if not already_cloned:
                if install_cmd := cfg.get("install_cmd"):
                    print(f"\n[{name}] Running install command …")
                    run(install_cmd, cwd=repo_dir)
            else:
                if install_cmd := cfg.get("install_cmd"):
                    print(f"\n[{name}] Syncing dependencies …")
                    run(install_cmd, cwd=repo_dir)
            ok = run_tests(
                name, repo_dir, cfg.get("pytest_args", []), extra_env=cfg.get("env")
            )
            results[name] = ok
        except subprocess.CalledProcessError as exc:
            print(f"\n[{name}] ERROR: command failed with exit code {exc.returncode}")
            results[name] = False

    # Summary
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    for name, ok in results.items():
        print(f"  {'✓' if ok else '✗'}  {name}")
    print()

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
