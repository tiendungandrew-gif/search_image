"""Portable browser environment; no credential loading."""

import os
from pathlib import Path


def browser_environment(root: Path, inherited=None):
    env = (os.environ if inherited is None else inherited).copy()
    # IDE installed via Snap can inject incompatible glib/pthread modules into WebKit.
    # Change only the child test process, leaving the shell and system untouched.
    for name in (
        "GIO_EXTRA_MODULES",
        "GIO_MODULE_DIR",
        "GTK_PATH",
        "GTK_EXE_PREFIX",
        "GDK_PIXBUF_MODULEDIR",
        "GDK_PIXBUF_MODULE_FILE",
        "GSETTINGS_SCHEMA_DIR",
        "GI_TYPELIB_PATH",
        "LIBGL_DRIVERS_PATH",
        "__EGL_VENDOR_LIBRARY_DIRS",
        "LD_PRELOAD",
    ):
        if "/snap/" in env.get(name, ""):
            env.pop(name)
    env["PATH"] = str(root / ".tools/node/bin") + os.pathsep + env["PATH"]
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(root / ".cache/playwright")
    env["LD_LIBRARY_PATH"] = (
        str(root / ".cache/browser-libs/root/usr/lib/x86_64-linux-gnu")
        + os.pathsep
        + os.pathsep.join(
            part
            for part in env.get("LD_LIBRARY_PATH", "").split(os.pathsep)
            if "/snap/" not in part
        )
    )
    return env
