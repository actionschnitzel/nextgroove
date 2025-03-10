# album_header.py
#
# Copyright 2024 Dean Birch
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later


from __future__ import annotations
from typing import Optional

from gi.repository import GObject, Gtk
from .albumlistitem import AlbumListItem
from html import escape



@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/albumheader.ui")
class AlbumHeader(Gtk.Box):

    __gtype_name__ = "AlbumHeader"

    _album_label = Gtk.Template.Child()
    _cover_image = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self._album = None
        self._cover_image.set_size_request(128, 128)

    def set_album(self, album):
        self._album = album
        self._album_label.set_markup(f"<span size=\"x-large\">{escape(album.album)}</span>")

    def set_cover(self, cover_file):
        self._cover_image.set_from_file(cover_file)
