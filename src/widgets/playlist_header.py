# playlist_header.py
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

from gi.repository import GObject, Gtk, Gio
from .playlist import PlaylistItem
from .song_row import SongRow
from html import escape



@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/playlistheader.ui")
class PlaylistHeader(Gtk.Box):

    __gtype_name__ = "PlaylistHeader"

    playlist_name = Gtk.Template.Child()
    _cover_image = Gtk.Template.Child()

    _songlist = Gtk.Template.Child("songlist")
    play_button = Gtk.Template.Child("play_button")
    song_click_menu_playlist = Gtk.Template.Child("song_click_menu_playlist")
    append_button = Gtk.Template.Child("append_button")
    append_next_button = Gtk.Template.Child("append_next_button")
    delete_playlist = Gtk.Template.Child("delete_playlist")



    def __init__(self):
        super().__init__()
        self._track_elements = Gio.ListStore()
        self._album = None
        self._cover_image.set_size_request(128, 128)
        self.clicked_song = None
        self.window = None
        self.playlist_to_delete = None

        song_item_factory = Gtk.SignalListItemFactory()
        song_item_factory.connect("setup", self._setup_song_list_item)
        song_item_factory.connect("bind", self._bind_song_list_item)
        self._songlist.props.factory = song_item_factory
        song_selection_model = Gtk.SingleSelection.new(self._track_elements)
        self._songlist.props.model = song_selection_model
        self._songlist.connect("activate", self.song_clicked)

        # Header buttons (some done in window.py)
        self.delete_playlist.connect("clicked", self.delete_playlist_clicked)

    def set_window(self, window):
        self.window = window

    def set_playlist(self, playlist):
        self.playlist = playlist
        self.playlist_name.set_markup(f"<span size=\"xx-large\">{escape(playlist.playlist_name)}</span>")

    def set_cover(self, cover_file):
        self._cover_image.set_from_file(cover_file)

    def set_tracks(self, tracks):
        self._track_elements.remove_all()
        current_song = self.window.current_song()
        # Add tracks
        for track in tracks:
            if current_song and track.song_id == current_song.song_id:
                track.set_now_playing(True)
            self._track_elements.append(track)

    def _setup_song_list_item(self, factory, list_item):
        list_item.props.child = SongRow()
        list_item.props.child.show_artist()
        if self.window:
            list_item.props.child.set_window(self.window)


    def _bind_song_list_item(self, factory, list_item):
        song_item = list_item.props.item
        song_row = list_item.props.child
        song_row.set_queue_item(song_item)
        song_item.set_widget(song_row)
        cover_url, album_id = self.window._client.get_album_cover_url_from_song_id(song_item.track_id)
        song_row.set_album_id(album_id)
        self.window._client.download_cover_async_generic(album_id, cover_url, self, song_row.set_cover_callback)

    def song_clicked(self, event, song_id):
        song_thing = self._track_elements[song_id]
        popover = Gtk.PopoverMenu.new_from_model(self.song_click_menu_playlist)
        popover.set_parent(song_thing.widget)
        popover.popup()
        self.clicked_song = song_thing

    def song_play_clicked(self, event, _):
        logging.info(f"Let's play {self.clicked_song.title}")
        self.window._queue.remove_all()
        self.clicked_song.set_now_playing(True)
        self.window._queue.append(self.clicked_song)

        self.window._client.get_song_async(self.clicked_song.get_song_id(), self.clicked_song.title, self.window.song_file_returned)
        self.window.controls.set_queue_pos(0)

    def song_queue_add_end_clicked(self, event, _):
        if len(self.window._queue) == 0:
            logging.debug("Same as play if the queue is empty, redirecting")
            self.song_play_clicked(None, None)
            return

        self.window._queue.append(self.clicked_song)

    def song_queue_add_next_clicked(self, event, _):
        if len(self.window._queue) == 0:
            logging.debug("Same as play if the queue is empty, redirecting")
            self.song_play_clicked(None, None)
            return

        insert_index = 0
        for queue_song in self.window._queue:
            if queue_song.is_now_playing():
                break
            insert_index += 1

        self.window._queue.insert(insert_index+1 , self.clicked_song)

    def delete_playlist_clicked(self, event):
        playlist_name = escape(self.playlist.playlist_name)
        logging.info(f"Confirm whether to delete {playlist_name} (ID {self.playlist.playlist_id})")
        self.playlist_to_delete = self.playlist.playlist_id

        dialog = Gtk.AlertDialog()
        dialog.set_detail(f"Are you sure you want to delete playlist: '{playlist_name}'")
        dialog.set_buttons(["Cancel", "Delete"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(0)
        dialog.choose(self.window, None, self.confirm_result, None)

    def confirm_result(self, dialog, task, _):
        result = dialog.choose_finish(task)
        if result == 0:
            # Chose to cancel
            return
        logging.info(f"Delete playlist {self.playlist.playlist_id}")

        self.window.playlist_nav_view.pop()
        self.window._client.delete_playlist_async(self.playlist.playlist_id)

