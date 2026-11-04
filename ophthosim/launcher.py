"""Shared desktop entry point for the educational Python edition."""
import argparse
import os
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description='OphthoSim desktop launcher',
                                     add_help=False)
    parser.add_argument('--mode', choices=('2d', '3d'), default='3d')
    options, remaining = parser.parse_known_args(argv)
    if getattr(sys, 'frozen', False):
        for index, arg in enumerate(remaining):
            if arg.startswith('--resume='):
                value = arg.partition('=')[2]
                if value:
                    remaining[index] = '--resume=' + str(Path(value).resolve())
            elif arg == '--resume' and index + 1 < len(remaining):
                value = remaining[index + 1]
                if not value.startswith('-'):
                    remaining[index + 1] = str(Path(value).resolve())
        # Relative journals/exports must not depend on a shortcut's working
        # directory or require writing beside an installed executable.
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'OphthoSim'
        base.mkdir(parents=True, exist_ok=True)
        os.chdir(base)
    if not any(arg == '--lang' or arg.startswith('--lang=') for arg in remaining):
        remaining = ['--lang', 'ko', *remaining]
    if options.mode == '2d':
        from .app import main as launch
    else:
        from .gl_surgery import main as launch
    return launch(remaining) or 0


if __name__ == '__main__':
    raise SystemExit(main())
