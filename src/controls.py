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
from gi.repository import Gio, GObject, GLib
from html import escape
from .albumtile import AlbumTile
from .queueitem import QueueItem
from html import escape


@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/controls.ui")
class Controls(Gtk.ActionBar):
    __gtype_name__ = "Controls"

    # Child Widgets
    play_pause_button = Gtk.Template.Child("playpause")
    previous_button = Gtk.Template.Child("previous")
    next_button = Gtk.Template.Child("next")
    now_playing_label = Gtk.Template.Child("nowplaying")
    current_album_artist = Gtk.Template.Child("current_album_artist")
    volumebutton = Gtk.Template.Child("volumebutton")
    volumepopover = Gtk.Template.Child("volumepopover")
    volumescale = Gtk.Template.Child("volumescale")
    # Duration
    duration_label = Gtk.Template.Child("duration_label")

    # Data refs
    _client = None
    _media = None
    _queue = None
    _window = None
    mpris = None

    # Signal handlers for disconnecting
    play_pause_handler_id = None
    next_handler_id = None
    previous_handler_id = None

    def __init__(self):
        super().__init__()
        self.set_size_request(120, 50)
        self.volumescale.set_range(0, 100)
        self.volumescale.set_increments(5,10)
        self.volumescale.set_size_request(150, 30)
        self.volumescale.connect("value-changed", self.volume_changed)
        self.queue_item = None

    def set_mpris(self, mpris):
        self.mpris = mpris

    def connections(self, client, media, queue, window):
        # Remove old connections
        if self.play_pause_handler_id:
            self.play_pause_button.disconnect(self.play_pause_handler_id)
        if self.next_handler_id:
            self.next_button.disconnect(self.next_handler_id)
        if self.previous_handler_id:
            self.previous_button.disconnect(self.previous_handler_id)

        self.volumescale.set_value(window.settings.get_int("volume"))

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
        self.volumebutton.connect("clicked", self.volume_clicked)

        self._media = media
        self._client = client
        self._queue = queue
        self._window = window
        self.timeout = None

        if self._media.get_playing():
            self.play_pause_button.set_icon_name("media-playback-pause-symbolic")

    def on_play_pause_button_pressed(self, event):
        if not self._media:
            print("Not playing yet, ignoring play/pause")
            return
        print(
            f"play/pause pressed"
        )
        if self._media.get_playing():
            print("Pausing")
            self._media.pause()
            self.play_pause_button.set_icon_name("media-playback-start-symbolic")
        elif self._media.get_duration() > 0:
            print("Play")
            self._media.play()
            self.play_pause_button.set_icon_name("media-playback-pause-symbolic")
        else:
            print("Likely no media loaded yet, no action from play/pause")
        self.mpris._on_playing_changed(None, None)

    def on_previous_button_pressed(self, event):
        if len(self._queue) == 0:
            print("Queue empty, ignoring previous button")
            return
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
        if len(self._queue) == 0:
            print("Queue empty, ignoring next button")
            return
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
            self.play_pause_button.set_icon_name("media-playback-start-symbolic")
            return

        current_song_queue_item.set_now_playing(False)
        song_queue_item.set_now_playing(True)
        song_file = self._client.get_song(song_queue_item.get_song_id())
        self._window.play_song(song_file, song_queue_item.get_title())

    def set_now_playing(self, queue_item):
        song_title = queue_item.title
        artist_title = self._client.artist_name_by_id[queue_item.artist_id]
        album_title = self._client.album_name_by_id[queue_item.album_id]
        self.now_playing_label.set_text(song_title)
        self.current_album_artist.set_markup(f"{escape(artist_title)}: <i>{escape(album_title)}</i>")
        self.play_pause_button.set_icon_name("media-playback-pause-symbolic")
        # Duration
        if not self.timeout:
            self.timeout = GLib.timeout_add(1000, self.update_duration, None)
        self.queue_item = queue_item

    def update_duration(self, thing):
        # Get current timestamp in MICROseconds
        current_duration = self._media.get_timestamp()
        current_duration_seconds = int(current_duration / 1000000)
        time_string = QueueItem.duration_string_util(current_duration_seconds)
        full_duration_string = QueueItem.duration_string_util(self.queue_item.duration  )
        if self.queue_item:
            self.duration_label.set_text(f"{time_string} / {full_duration_string}")
        else:
            self.duration_label.set_text("")

        return True

    def song_ended(self, foo, bar):
        print("Song ended")
        self.on_next_button_pressed(None)

    def volume_clicked(self, event):
        self.volumepopover.set_size_request(100, 25)
        self.volumepopover.popup()

    def volume_changed(self, scale):
        value = scale.get_value()
        new_volume = value / 100
        if not self._media:
            # Being modified before welcome page dismissed
            return

        self._media.set_volume(new_volume)
        if value == 0:
            self.volumebutton.set_icon_name("audio-volume-muted")
        elif value < 40:
            self.volumebutton.set_icon_name("audio-volume-low")
        elif value < 70:
            self.volumebutton.set_icon_name("audio-volume-medium")
        else:
            self.volumebutton.set_icon_name("audio-volume-high")

        self._window.props.settings.set_int("volume", int(value))

    def is_playing(self):
        return self._media.get_playing()
