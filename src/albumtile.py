# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Forked from https://gitlab.gnome.org/GNOME/gnome-music/-/blob/master/gnomemusic/mpris.py
# Used along with the corresponding UI file as a template for a Gtk Widget
# It's been heavily stripped but covers setting the basic widget shape

from __future__ import annotations
from typing import Optional

from gi.repository import GObject, Gtk
from .albumlistitem import AlbumListItem


@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/albumtile.ui")
class AlbumTile(Gtk.Box):

    __gtype_name__ = "AlbumTile"

    _album_label = Gtk.Template.Child()
    _artist_label = Gtk.Template.Child()
    _cover_image = Gtk.Template.Child()

    def __init__(self) -> None:
        """Initialise AlbumTile"""
        super().__init__()
        self._album = None
        self._cover_image.set_size_request(128, 128)


    @GObject.Property(
        type=AlbumListItem, flags=GObject.ParamFlags.READWRITE, default=None
    )
    def album(self):
        return self._album

    def set_album(self, album):
        self._album = album
        self._artist_label.set_text(album.artist)
        self._album_label.set_text(album.album)

    def set_cover(self, cover_file):
        self._cover_image.set_filename(cover_file)
