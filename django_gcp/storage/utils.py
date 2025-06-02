import os
import posixpath

from django.core.exceptions import SuspiciousFileOperation
from django.utils.encoding import force_bytes


def to_bytes(content):
    """Wrap Django's force_bytes to pass through bytearrays."""
    if isinstance(content, bytearray):
        return content

    return force_bytes(content)


def clean_name(name):
    """
    Cleans the name so that Windows style paths work
    """
    # Normalize Windows style paths
    cleaned = posixpath.normpath(name).replace("\\", "/")

    # os.path.normpath() can strip trailing slashes so we implement
    # a workaround here.
    if name.endswith("/") and not cleaned.endswith("/"):
        # Add a trailing slash as it was stripped.
        cleaned = cleaned + "/"

    # Given an empty string, os.path.normpath() will return ., which we don't want
    if cleaned == ".":
        cleaned = ""

    return cleaned


def safe_join(base, *paths):
    """
    A version of django.utils._os.safe_join for S3 paths.

    Joins one or more path components to the base path component
    intelligently. Returns a normalized version of the final path.

    The final path must be located inside of the base path component
    (otherwise a ValueError is raised).

    Paths outside the base path indicate a possible security
    sensitive operation.
    """
    base_path = base
    base_path = base_path.rstrip("/")
    paths = [p for p in paths]

    final_path = base_path + "/"
    for path in paths:
        _final_path = posixpath.normpath(posixpath.join(final_path, path))
        # posixpath.normpath() strips the trailing /. Add it back.
        if path.endswith("/") or _final_path + "/" == final_path:
            _final_path += "/"
        final_path = _final_path
    if final_path == base_path:
        final_path += "/"

    # Ensure final_path starts with base_path and that the next character after
    # the base path is /.
    base_path_len = len(base_path)
    if not final_path.startswith(base_path) or final_path[base_path_len] != "/":
        raise ValueError("the joined path is located outside of the base path component")

    return final_path.lstrip("/")


def get_available_overwrite_name(name, max_length):
    """Truncate a filename to obey max_length limit"""
    if max_length is None or len(name) <= max_length:
        return name

    # Adapted from Django
    dir_name, file_name = os.path.split(name)
    file_root, file_ext = os.path.splitext(file_name)
    truncation = len(name) - max_length

    file_root = file_root[:-truncation]
    if not file_root:
        raise SuspiciousFileOperation(
            f'Storage tried to truncate away entire filename "{name}". Please make sure that the corresponding file field allows sufficient "max_length".'
        )
    return os.path.join(dir_name, f"{file_root}{file_ext}")
