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



@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/songrow.ui")
class SongRow(Gtk.Box):

    __gtype_name__ = "SongRow"

    _song_title = Gtk.Template.Child("title_label")
    _artist_title = Gtk.Template.Child("artist_label")
    _song_number = Gtk.Template.Child("song_number")
    _song_duration = Gtk.Template.Child("song_duration")
    cover = Gtk.Template.Child()
    drag_source = Gtk.Template.Child()
    remove_button = Gtk.Template.Child()

    queue_item = None

    def __init__(self):
        super().__init__()
        self._song_title.set_hexpand(True)
        self.parent = None
        self.index = -1
        self.window = None
        self.list_item = None
        self.album_id = None
        self.drag_enabled = False
        self.setup_queue_drag()

    def set_index(self, index):
        self.index = index

    def set_window(self, window):
        self.window = window

    def set_list_item(self, list_item):
        self.list_item = list_item

    def show_artist(self):
        self._artist_title.set_visible(True)
        self._song_number.set_visible(False)

    def set_window(self, window):
        self.window = window

    def set_queue_item(self, queue_item):
        queue_item.connect("notify", self.now_playing_changed)
        self.queue_item = queue_item
        self.draw(self.queue_item)
        if self.parent:
            # That means we want drag
            self.setup_drag(self.parent)
            # Also
            self.remove_button.connect("clicked", self.remove_clicked)

    def draw(self, queue_item):
        weight = "normal"
        if queue_item.now_playing:
            weight = "bold"
        self._song_title.set_markup(f"<span weight=\"{weight}\" size=\"large\">{escape(queue_item.title)}</span>")
        if queue_item.track_number and queue_item.track_number != -1:
            self._song_number.set_markup(f"<span weight=\"{weight}\" size=\"small\">{queue_item.track_number}</span>")
        if queue_item.duration and queue_item.duration != -1:
            self._song_duration.set_markup(f"<span weight=\"{weight}\">{queue_item.duration_string()}</span>")
        if self._artist_title.is_visible():
            self._song_number.set_label("")
            artist_label = self.window._client.artist_name_by_id[queue_item.artist_id]
            self._artist_title.set_markup(f"<span weight=\"{weight}\" size=\"small\">{escape(artist_label)}</span>")

    def now_playing_changed(self, thing_1, thing_2):
        self.draw(self.queue_item)

    def set_album_id(self, album_id):
        self.album_id = album_id

    def set_cover_callback(self, foo, bar, baz):
        self.cover.set_filename(NextcloudMusicClient.get_cover_from_album_id(self.album_id))

    def setup_drag(self, parent):
        # Called once before we have a queue_item
        self.parent = parent
        if self.queue_item == None:
            return
        # Called again if we have set parent
        source = Gtk.DragSource.new()
        source.set_actions(Gdk.DragAction.MOVE)
        source.set_content(Gdk.ContentProvider.new_for_value(self))
        content_type = source.get_content().ref_formats().get_gtypes()[0]

        self.drag_source.add_controller(source)
        self.drag_enabled = True
        self.drag_source.set_visible(True)

        target = Gtk.DropTarget.new(content_type ,Gdk.DragAction.MOVE)
        target.connect("drop", self.on_drag_drop)
        self.add_controller(target)

    def setup_queue_drag(self):
        source = Gtk.DragSource.new()
        source.set_actions(Gdk.DragAction.COPY)
        source.connect("prepare", self._queue_drag_prepare)
        self.add_controller(source)

    def _queue_drag_prepare(self, source, x, y):
        # Queue rows reorder via their handle instead
        if self.parent or self.queue_item is None:
            return None
        return Gdk.ContentProvider.new_for_value(self.queue_item)

    def on_drag_drop(self, drop_target, source, x, y):
        logging.debug(f"Dragged {source.queue_item.title} to {self.queue_item.title}")
        logging.debug(f"That's moving index {source.index} to {self.index}")
        self.window.reorder_queue(source.index, self.index)

    def set_selected(self, selected):
        if not self.drag_enabled:
            return
        self.remove_button.set_visible(selected)

    def remove_clicked(self, _):
        logging.debug(f"want to remove {self.queue_item} at index {self.index}")
        self.window.remove_queue_item(self.index)
