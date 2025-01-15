# controls.py
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

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio, GObject
from html import escape
from .albumtile import AlbumTile
from .queueitem import QueueItem
from html import escape


@Gtk.Template(resource_path="/net/rosebirch/nextcloudmusic/controls.ui")
class Controls(Gtk.ActionBar):
    __gtype_name__ = "Controls"

    # Child Widgets
    play_pause_button = Gtk.Template.Child("playpause")
    previous_button = Gtk.Template.Child("previous")
    next_button = Gtk.Template.Child("next")
    now_playing_label = Gtk.Template.Child("nowplaying")

    # Data refs
    _client = None
    _media = None
    _queue = None
    _window = None

    # Signal handlers for disconnecting
    play_pause_handler_id = None
    next_handler_id = None
    previous_handler_id = None

    def __init__(self):
        super().__init__()
        self.set_size_request(120, 50)

    def connections(self, client, media, queue, window):
        # Remove old connections
        if self.play_pause_handler_id:
            self.play_pause_button.disconnect(self.play_pause_handler_id)
        if self.next_handler_id:
            self.next_button.disconnect(self.next_handler_id)
        if self.previous_handler_id:
            self.previous_button.disconnect(self.previous_handler_id)

        # Connect new items
        self.play_pause_handler_id = self.play_pause_button.connect(
            "clicked", self.on_play_pause_button_pressed
        )
        self.next_handler_id = self.next_button.connect(
            "clicked", self.on_next_button_pressed
        )
        self.previous_handler_id = self.previous_button.connect(
            "clicked", self.on_previous_button_pressed
        )
        media.connect("notify::ended", self.song_ended)

        self._media = media
        self._client = client
        self._queue = queue
        self._window = window

        if self._media.get_duration() > 0:
            self.play_pause_button.set_icon_name("media-playback-pause-symbolic")

    def on_play_pause_button_pressed(self, event):
        if not self._media:
            print("Not playing yet, ignoring play/pause")
            return
        print(
            f"play pressed and apparently is it playing already {self._media.get_playing()} and duration is {self._media.get_timestamp()}"
        )
        if self._media.get_playing():
            print("PAUSE")
            self._media.pause()
            self.play_pause_button.set_icon_name("media-playback-start-symbolic")
        else:
            print("PLAY")
            self._media.play()
            self.play_pause_button.set_icon_name("media-playback-pause-symbolic")

    def on_previous_button_pressed(self, event):
        print("Previous button pressed")
        last_song = None
        current_song = None
        for song in self._queue:
            if song.is_now_playing():
                current_song = song
                break
            last_song = song
        if not last_song:
            print("No previous song, just replay the same one")
            song_file = self._client.get_song(current_song.get_song_id())
            self._window.play_song(song_file, current_song.get_title())
        else:
            last_song.set_now_playing(True)
            current_song.set_now_playing(False)
            print(f"Try and play {last_song.get_title()}")
            song_file = self._client.get_song(last_song.get_song_id())
            self._window.play_song(song_file, last_song.get_title())

    def on_next_button_pressed(self, event):
        next_song = False
        song_queue_item = None
        current_song_queue_item = None
        for song in self._queue:
            if next_song:
                song_queue_item = song
                break
            if song.is_now_playing():
                current_song_queue_item = song
                next_song = True

        if not song_queue_item:
            print("Reached end of queue, not playing new song.")
            return

        current_song_queue_item.set_now_playing(False)
        song_queue_item.set_now_playing(True)
        song_file = self._client.get_song(song_queue_item.get_song_id())
        self._window.play_song(song_file, song_queue_item.get_title())

    def set_now_playing(self, song):
        self.now_playing_label.set_text(f"{escape(song)}")
        self.play_pause_button.set_icon_name("media-playback-pause-symbolic")

    def song_ended(self, foo, bar):
        print("Song ended")
        self.on_next_button_pressed(None)
