#!/usr/bin/env python3
# Starts NextGroove directly from the source tree, without installing.

import gettext
import glob
import os
import shutil
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
WORK = os.path.join(os.path.expanduser("~/.cache"), "nextgroove-dev")


def main():
    os.makedirs(WORK, exist_ok=True)

    gresource = os.path.join(WORK, "nextgroove.gresource")
    subprocess.run(
        ["glib-compile-resources", f"--sourcedir={SRC}", f"--target={gresource}",
         os.path.join(SRC, "nextgroove.gresource.xml")],
        check=True,
    )

    # Meson installs models/ and widgets/ flat into one package; mirror that layout with symlinks.
    pkg_dir = os.path.join(WORK, "pkg", "nextgroove")
    if os.path.islink(pkg_dir):
        os.unlink(pkg_dir)
    shutil.rmtree(pkg_dir, ignore_errors=True)
    os.makedirs(pkg_dir)
    for pattern in ("*.py", "models/*.py", "widgets/*.py"):
        for path in glob.glob(os.path.join(SRC, pattern)):
            os.symlink(path, os.path.join(pkg_dir, os.path.basename(path)))
    sys.path.insert(0, os.path.dirname(pkg_dir))

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    gettext.install("nextgroove")

    from gi.repository import Gio
    Gio.Resource.load(gresource)._register()

    from nextgroove import main as app
    sys.exit(app.main("dev"))


if __name__ == "__main__":
    main()
