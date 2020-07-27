"""
Utility functions for Artie platform.
"""
import os


def validate_path(parser, arg) -> bool:
    """
    Checks if the argparse argument is a valid path. If you want to check if
    the argument is a valid file path only, use `validate_fpath`, and if you
    want to check if the argument is a valid directory path, use `validate_dpath`.

    Use like this:

    ```
    parser.add_argument("config", type=lambda arg: validate_path(parser, arg))
    ```

    If the path is invalid, we raise a parser error.
    """
    if not os.path.exists(arg):
        parser.error(f"The given argument is not a valid file or directory path: {arg}")
    return arg

def validate_fpath(parser, arg) -> bool:
    """
    Checks if the argparse argument is a valid file path. If you want to check if
    the argument is a valid directory path, use `validate_dpath`, and if you want
    to know only whether the path is valid at all (directory or file), use
    `validate_path`.

    Use like this:

    ```
    parser.add_argument("config", type=lambda arg: validate_fpath(parser, arg))
    ```

    If the path is invalid, we raise a parser error.
    """
    if not os.path.isfile(arg):
        parser.error(f"The given argument is not a valid file path: {arg}")
    return arg

def validate_dpath(parser, arg) -> bool:
    """
    Checks if the argparse argument is a valid directory path. If you want to check if
    the argument is a valid file path, use `validate_fpath`, and if you want
    to know only whether the path is valid at all (directory or file), use `validate_path`.

    Use like this:

    ```
    parser.add_argument("config", type=lambda arg: validate_dpath(parser, arg))
    ```

    If the path is invalid, we raise a parser error.
    """
    if not os.path.isdir(arg):
        parser.error(f"The given argument is not a valid directory path: {arg}")
    return arg
