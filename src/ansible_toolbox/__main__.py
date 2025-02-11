from __future__ import annotations

import argparse
import logging
import sys
import traceback

from .core import AnsibleToolbox, DockerRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger(__name__)


def parse_arguments(args: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Ansible commands in a Docker container.",
        add_help=False,
    )
    parser.add_argument(
        "--at-help",
        dest="help",
        action="store_true",
        help="Show this help message and exit",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help="The Ansible command to run",
    )
    parser.add_argument(
        "--at-i",
        dest="interactive",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--at-add-py-package",
        dest="additional_python_packages",
        action="append",
        default=[],
        help="Additional python packages to add to the toolbox",
    )
    parser.add_argument(
        "--at-volume",
        dest="volumes",
        action="append",
        default=[],
        help="Additional volumes to mount",
    )
    parser.add_argument(
        "--at-env",
        dest="envs",
        action="append",
        default=[],
        help="Additional environment variables",
    )

    args = parser.parse_args(args)

    if args.help:
        parser.print_help()
        sys.exit(0)

    if not args.command:
        parser.error("Please provide the `command` to be executed")

    return args


def main() -> None:
    try:
        args = parse_arguments(sys.argv[1:])
        toolbox = AnsibleToolbox(DockerRunner())
        toolbox.run(args)

    except Exception as exc:
        logger.exception(
            "An unexpected error occurred: %s",
            str(exc),  # noqa: TRY401
        )

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    main()
