"""Read-only NTFS named-stream rejection shared by offline recovery helpers.

On non-Windows this adds no extended-attribute coverage. It does not certify ACLs
or protect against concurrent hostile same-user filesystem changes.
"""
import os
from pathlib import Path


def reject_named_streams(path):
    """Reject explicit stream paths and non-default NTFS streams, fail closed."""
    if os.name != 'nt':
        return
    import ctypes
    from ctypes import wintypes

    path = Path(os.path.abspath(path))
    if any(':' in part for part in path.parts[1:]):
        raise OSError('named stream rejected')

    class StreamData(ctypes.Structure):
        _fields_ = [('size', ctypes.c_longlong), ('name', wintypes.WCHAR * 296)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    first = kernel.FindFirstStreamW
    first.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(StreamData), wintypes.DWORD]
    first.restype = wintypes.HANDLE
    next_stream = kernel.FindNextStreamW
    next_stream.argtypes = [wintypes.HANDLE, ctypes.POINTER(StreamData)]
    next_stream.restype = wintypes.BOOL
    close = kernel.FindClose
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    data = StreamData()
    handle = first(str(path), 0, ctypes.byref(data), 0)
    if handle == ctypes.c_void_p(-1).value:
        if ctypes.get_last_error() == 38:  # ERROR_HANDLE_EOF, e.g. streamless directory.
            return
        raise OSError('stream enumeration rejected')
    try:
        while True:
            if data.name != '::$DATA':
                raise OSError('named stream rejected')
            if not next_stream(handle, ctypes.byref(data)):
                if ctypes.get_last_error() != 38:
                    raise OSError('stream enumeration rejected')
                break
    finally:
        close(handle)
