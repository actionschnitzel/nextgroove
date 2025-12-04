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

import logging

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio, GObject, GLib
from html import escape
from .albumtile import AlbumTile
from .queueitem import QueueItem
from .client import NextcloudMusicClient
from html import escape


@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/controls.ui")
class Controls(Gtk.Box):
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
    max_duration_label = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    duration_scale = Gtk.Template.Child()
    loading = Gtk.Template.Child()
    network_issue_icon = Gtk.Template.Child()
    # Now playing
    now_playing_box = Gtk.Template.Child()
    small_now_playing_area = Gtk.Template.Child()
    action_bar = Gtk.Template.Child()

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
        self.queue_pos = -1
        self.duration_scale.set_size_request(150,1)
        self.application = None
        # Now playing portrait/landscape logic
        self.shown = False
        self.portrait = False
        self.scrobbled = False

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

        # Restore it to it's saved position
        self.volume_changed(self.volumescale)

    def on_play_pause_button_pressed(self, event):
        if not self._media:
            logging.debug("Not playing yet, ignoring play/pause")
            return
        logging.debug(
            f"play/pause pressed"
        )
        if self._media.get_playing():
            logging.info("Pausing")
            self._media.pause()
            self.application.allow_suspend()
            self.play_pause_button.set_icon_name("media-playback-start-symbolic")
        elif self._media.get_duration() > 0:
            logging.info("Play")
            self._media.play()
            self.application.prevent_suspend()
            self.play_pause_button.set_icon_name("media-playback-pause-symbolic")
        else:
            logging.debug("Likely no media loaded yet, no action from play/pause")
        self.mpris._on_playing_changed(None, None)

    def on_previous_button_pressed(self, event):
        if len(self._queue) == 0:
            logging.debug("Queue empty, ignoring previous button")
            return
        logging.debug("Previous button pressed")
        if self.queue_pos == 0:
            logging.info("No previous song, just replay the same one")
            current_song = self._queue[self.queue_pos]
            song_file = self._client.get_song(current_song.get_song_id())
            self._window.play_song(song_file, current_song.get_title())
            return

        current_song_queue_item = self._queue[self.queue_pos]
        previous_song_queue_item = self._queue[self.queue_pos - 1]

        previous_song_queue_item.set_now_playing(True)
        previous_song_queue_item.notify("now_playing")
        current_song_queue_item.set_now_playing(False)
        current_song_queue_item.notify("now_playing")
        logging.info(f"Try and play {previous_song_queue_item.get_title()}")
        self._client.get_song_async(previous_song_queue_item.get_song_id(), previous_song_queue_item.get_title(), self.prev_song_file_returned)
        self.start_loading()

    def prev_song_file_returned(self, source_object, result, user_data):
        self.increment_queue_pos(-1)
        self.finished_loading()
        if result.had_error():
            logging.error("Had an error, stop")
            self.network_issue_icon.set_visible(True)
            self.network_issue_icon.set_tooltip_text(self._client.last_error)
            return
        song_file = result.propagate_value().value
        self._window.play_song(song_file, self._client.song_title_last_callback)


    def on_next_button_pressed(self, event):
        if len(self._queue) == 0:
            logging.debug("Queue empty, ignoring next button")
            self.application.allow_suspend()
            return

        current_song_queue_item = self._queue[self.queue_pos]
        next_song_index = self.queue_pos + 1

        song_queue_item = None
        if next_song_index < len(self._queue):  # Then this is valid
            song_queue_item = self._queue[next_song_index]

        if not song_queue_item:
            logging.info("Reached end of queue, not playing new song.")
            self.play_pause_button.set_icon_name("media-playback-start-symbolic")
            self.application.allow_suspend()
            self.mpris._on_playing_changed(None, None)
            return

        current_song_queue_item.set_now_playing(False)
        current_song_queue_item.notify("now_playing")
        song_queue_item.set_now_playing(True)
        song_queue_item.notify("now_playing")

        self._client.get_song_async(song_queue_item.get_song_id(), song_queue_item.get_title(), self.next_song_file_returned)
        self.start_loading()

    def next_song_file_returned(self, source_object, result, user_data):
        self.increment_queue_pos()
        self.finished_loading()
        if result.had_error():
            logging.error("Had an error, stop")
            self.network_issue_icon.set_visible(True)
            self.network_issue_icon.set_tooltip_text(self._client.last_error)
            return
        song_file = result.propagate_value().value
        self._window.play_song(song_file, self._client.song_title_last_callback)

    def set_now_playing(self, queue_item):
        self.shown = True
        self.action_bar.set_visible(True)
        self.scrobbled = False
        if self.portrait:
            self.small_now_playing_area.set_visible(True)
            current_width = self.get_size_request()[0]
            self.small_now_playing_area.set_size_request(current_width, 50)
        self.queue_resize()

        song_title = queue_item.title
        artist_title = self._client.artist_name_by_id[queue_item.artist_id]
        album_title = self._client.album_name_by_id[queue_item.album_id]
        self.cover.set_filename(NextcloudMusicClient.get_cover_from_album_id(queue_item.album_id))
        self.now_playing_label.set_text(song_title)
        self.current_album_artist.set_markup(f"{escape(artist_title)}: <i>{escape(album_title)}</i>")
        self.play_pause_button.set_icon_name("media-playback-pause-symbolic")
        # Duration
        if not self.timeout:
            self.timeout = GLib.timeout_add(1000, self.update_duration, None)
        self.queue_item = queue_item
        self.duration_scale.set_max_value(self.queue_item.duration)
        self.duration_scale.set_visible(True)
        full_duration_string = QueueItem.duration_string_util(self.queue_item.duration  )
        self.max_duration_label.set_text(full_duration_string)

    def update_duration(self, thing):
        # Get current timestamp in MICROseconds
        current_duration = self._media.get_timestamp()
        current_duration_seconds = int(current_duration / 1000000)
        time_string = QueueItem.duration_string_util(current_duration_seconds)

        if self.queue_item:
            self.duration_label.set_text(time_string)
        else:
            self.duration_label.set_text("")
        self.duration_scale.set_value(current_duration_seconds)

        # At half way trigger a scrobble
        if self.queue_item and not self.scrobbled and current_duration_seconds > self.queue_item.duration / 2.0:
            logging.debug(f"Scrobble as over half way through song: {current_duration_seconds} / {self.queue_item.duration}")
            self.scrobbled = True  # Don't trigger twice
            self._client.scrobble_async(self.queue_item.get_track_id(), self)

        return True

    def song_ended(self, foo, bar):
        logging.info("Song ended")
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

    def set_queue_pos(self, queue_pos):
        self.queue_pos = queue_pos

    def increment_queue_pos(self, increment=1):
        if self.queue_pos < 0:
            logging.debug("Not initialized queue_pos yet")
            return
        self.queue_pos += increment

    def set_application(self, application):
        self.application = application

    def start_loading(self):
        self.loading.set_visible(True)
        self.network_issue_icon.set_visible(False)

    def finished_loading(self):
        self.loading.set_visible(False)


    def go_big(self):
        logging.debug("Moving now playing to bottom left")
        current_width = self.get_size_request()[0]
        self.small_now_playing_area.remove(self.now_playing_box)
        self.small_now_playing_area.set_visible(False)
        self.action_bar.pack_start(self.now_playing_box)
        self.queue_resize()
        self.portrait = False

    def go_small(self):
        logging.debug("Moving now playing above controls")
        current_width = self.get_size_request()[0]
        if self.shown:
            self.small_now_playing_area.set_visible(True)
            self.small_now_playing_area.set_size_request(current_width, 50)
        self.action_bar.remove(self.now_playing_box)
        self.small_now_playing_area.set_center_widget(self.now_playing_box)
        self.queue_resize()
        self.portrait = True
