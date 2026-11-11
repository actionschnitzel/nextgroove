# song_row.py
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


import logging


from gi.repository import GObject, Gtk, Gdk
from .albumlistitem import AlbumListItem
from .client import NextcloudMusicClient
from html import escape



@Gtk.Template(resource_path="/io/github/actionschnitzel/actiongroovenc/gtk/stats_row.ui")
class StatsRow(Gtk.Box):

    __gtype_name__ = "StatsRow"

    title_label = Gtk.Template.Child("title_label")
    sub_label = Gtk.Template.Child("sub_label")
    play_count = Gtk.Template.Child("play_count")
    position = Gtk.Template.Child()
    cover = Gtk.Template.Child()

    queue_item = None

    def __init__(self):
        super().__init__()
        self.title_label.set_hexpand(True)
        self.parent = None
        self.index = -1
        self.window = None
        self.list_item = None
        self.album_id = None

    def set_details(self, title, subtitle, position, playcount, album_id):
        self.title_label.set_label(title)
        if subtitle:
            self.sub_label.set_label(subtitle)
            self.sub_label.set_visible(True)
        self.play_count.set_label(str(playcount))
        self.position.set_label(str(position))
        if album_id:
            self.cover.set_filename(NextcloudMusicClient.get_cover_from_album_id(album_id))


