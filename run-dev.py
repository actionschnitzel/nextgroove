#!/usr/bin/env python3
# Starts ActionGrooveNC directly from the source tree, without installing.

import gettext
import glob
import os
import shutil
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
WORK = os.path.join(os.path.expanduser("~/.cache"), "actiongroovenc-dev")


def main():
    os.makedirs(WORK, exist_ok=True)

    gresource = os.path.join(WORK, "actiongroovenc.gresource")
    subprocess.run(
        ["glib-compile-resources", f"--sourcedir={SRC}", f"--target={gresource}",
         os.path.join(SRC, "actiongroovenc.gresource.xml")],
        check=True,
    )

    schema_dir = os.path.join(WORK, "schemas")
    os.makedirs(schema_dir, exist_ok=True)
    shutil.copy(os.path.join(HERE, "data", "io.github.actionschnitzel.actiongroovenc.gschema.xml"), schema_dir)
    subprocess.run(["glib-compile-schemas", schema_dir], check=True)
    os.environ["GSETTINGS_SCHEMA_DIR"] = schema_dir

    # Meson installs models/ and widgets/ flat into one package; mirror that layout with symlinks.
    pkg_dir = os.path.join(WORK, "pkg", "actiongroovenc")
    if os.path.islink(pkg_dir):
        os.unlink(pkg_dir)
    shutil.rmtree(pkg_dir, ignore_errors=True)
    os.makedirs(pkg_dir)
    for pattern in ("*.py", "models/*.py", "widgets/*.py"):
        for path in glob.glob(os.path.join(SRC, pattern)):
            os.symlink(path, os.path.join(pkg_dir, os.path.basename(path)))
    sys.path.insert(0, os.path.dirname(pkg_dir))

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    gettext.install("actiongroovenc")

    from gi.repository import Gio
    Gio.Resource.load(gresource)._register()

    from actiongroovenc import main as app
    sys.exit(app.main("dev"))


if __name__ == "__main__":
    main()
