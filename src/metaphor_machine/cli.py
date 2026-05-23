"""Tiny CLI for smoke-testing the pipeline without spinning up Streamlit.

Usage:
    python -m metaphor_machine.cli "I have too many priorities and a tiny team."
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv
from rich import print

from .core.pipeline import Pipeline, Session


def main() -> int:
    load_dotenv()
    if len(sys.argv) < 2:
        print("[red]Usage:[/red] python -m metaphor_machine.cli '<your problem>'")
        return 1
    user_text = " ".join(sys.argv[1:])
    pipeline = Pipeline(Session(raw_input=user_text))
    print(f"[bold]Input:[/bold] {user_text}")
    try:
        problem = pipeline.run_definer(user_text)
        print(problem)
    except NotImplementedError as e:
        print(f"[yellow]Skeleton only:[/yellow] {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
