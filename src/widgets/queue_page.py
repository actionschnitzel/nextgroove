# queue_page.py
#
# Copyright 2025 Dean Birch
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
from .song_row import SongRow
from .queueitem import QueueItem


_QUEUE_CSS = (
    "listview.queue-list > row:selected { background: none; }\n"
    ".queue-placeholder { border: 2px dashed alpha(currentColor, 0.3); border-radius: 12px; padding: 24px; }"
)


@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/queuepage.ui")
class QueuePage(Gtk.Overlay):

    __gtype_name__ = "QueuePage"

    queueview = Gtk.Template.Child()
    _save_queue_as_playlist_button = Gtk.Template.Child()
    _clear_queue_button = Gtk.Template.Child()
    _queue_name_entry = Gtk.Template.Child()
    _hide_playlist_save = Gtk.Template.Child()
    _queue_placeholder = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self._queue = None
        self._client = None
        self.controls = None
        self.window = None
        self._save_queue_as_playlist_button.set_sensitive(False)
        self._save_queue_as_playlist_button.connect("clicked", self.save_queue_button_clicked)
        self._clear_queue_button.set_sensitive(False)
        self._clear_queue_button.connect("clicked", self._clear_queue_clicked)
        self._hide_playlist_save.connect("clicked", self._hide_playlist_save_clicked)
        self._rows = set()
        provider = Gtk.CssProvider()
        provider.load_from_string(_QUEUE_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


    def set_client(self, client):
        self._client = client

    def set_queue(self, queue):
        self._queue = queue

        self._queue.connect("items-changed", self.queue_items_changed)

        queue_item_factory = Gtk.SignalListItemFactory()
        queue_item_factory.connect("setup", self._setup_queue_list_item)
        queue_item_factory.connect("bind", self._bind_queue_list_item)
        self.queueview.props.factory = queue_item_factory
        selection_model = Gtk.MultiSelection.new(self._queue)
        self.queueview.props.model = selection_model
        self.queueview.connect("activate", self.queue_clicked)
        queue_drop = Gtk.DropTarget.new(QueueItem, Gdk.DragAction.COPY)
        queue_drop.connect("enter", self._queue_drag_enter)
        queue_drop.connect("motion", self._queue_drag_enter)
        queue_drop.connect("drop", self._queue_drop)
        self.add_controller(queue_drop)

    def set_controls(self, controls):
        self.controls = controls

    def set_window(self, window):
        self.window = window


    ##############
    # Queue View #
    ##############

    def _setup_queue_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Generate UI element"""
        list_item.props.child = SongRow()
        list_item.props.child.show_artist()
        list_item.props.child.set_window(self)
        list_item.props.child.setup_drag(self)
        list_item.connect("notify::selected", self.list_item_selection_changed)

    def list_item_selection_changed(self, list_item, selected):
        list_item.props.child.set_selected(list_item.get_selected())

    def _bind_queue_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Populate UI element.
        As we don't have a specialised widget, we just make the now playing the bold one.
        """
        queue_list_item = list_item.props.item
        if queue_list_item.artist_id == -1:
            # This is being called with a fake value to redraw the others, ignore this
            return

        song_widget = list_item.props.child
        song_widget.set_index(list_item.get_position())
        song_widget.set_window(self.window)
        song_widget.set_list_item(list_item)
        cover_url, album_id = self.window._client.get_album_cover_url_from_song_id(queue_list_item.track_id)
        song_widget.set_album_id(album_id)
        self.window._client.download_cover_async_generic(album_id, cover_url, self, song_widget.set_cover_callback)
        self._rows.add(song_widget)

        if queue_list_item.album_id not in self._client.album_name_by_id:
            # We are repopulating during a client refresh, try again soon
            return
        album_str = self._client.album_name_by_id[queue_list_item.album_id]
        if queue_list_item.artist_id not in self._client.artist_name_by_id:
            # We are repopulating during a client refresh, try again in a sec
            return
        artist_str = self._client.artist_name_by_id[queue_list_item.artist_id]

        song_widget.set_queue_item(queue_list_item)

    def queue_clicked(self, event, queue_id):
        """When (double) clicked on the queue item, play it!"""
        song = self._queue[queue_id]
        logging.debug(f"Clicked on song {song.get_title()} from queue")
        # Set other( or all until next section) songs in queue to not playing
        for _song in self._queue:
            _song.set_now_playing(False)
        # Set current song to playing to show in bold
        song.set_now_playing(True)
        self.controls.set_queue_pos(queue_id)

        self._client.get_song_async(song.get_song_id(), song.get_title(), self.window.song_file_returned)

    def _queue_drag_enter(self, drop_target, x, y):
        return Gdk.DragAction.COPY

    def _queue_drop(self, drop_target, value, x, y):
        if not isinstance(value, QueueItem):
            return False
        was_empty = self._queue.get_n_items() == 0
        self._queue.append(value)
        if was_empty:
            self.queue_clicked(None, 0)
        return True

    def _hide_playlist_save_clicked(self, event):
        self._hide_playlist_save.set_visible(False)
        self._queue_name_entry.set_visible(False)
        self._queue_name_entry.set_text("")

    def save_queue_button_clicked(self, event):
        # First time, show the text field
        if not self._queue_name_entry.is_visible():
            self._hide_playlist_save.set_visible(True)
            self._queue_name_entry.set_visible(True)
            self._queue_name_entry.grab_focus()
            return

        # Second time, take the text field value
        playlist_name = self._queue_name_entry.get_text()
        logging.info(f"Asked to save to a playlist named {playlist_name}")
        # No need to check for existing playlist, this always creates a new one
        self._hide_playlist_save_clicked(None)
        self._client.create_new_playlist_async(playlist_name, self._queue, self.call_update_playlist)

    def _clear_queue_clicked(self, event):
        self._queue.remove_all()

    def call_update_playlist(self, one, two, three):
        self._client.playlist_async(None)

    def queue_items_changed(self, position, removed, added, user_data):
        has_items = self._queue.get_n_items() > 0
        self._save_queue_as_playlist_button.set_sensitive(has_items)
        self._clear_queue_button.set_sensitive(has_items)
        self._queue_placeholder.set_visible(not has_items)

    def queue_reorder(self):
        for row in self._rows:
            row.set_index(row.list_item.get_position())
