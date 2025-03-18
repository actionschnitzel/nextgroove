# queueitem.py
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

from gi.repository import GObject
import datetime


class QueueItem(GObject.Object):

    title = None
    song_id = None
    now_playing = None
    album_id = None
    artist_id = None
    widget = None

    def __init__(self, title, song_id, album_id, artist_id):
        super().__init__()
        self.title = title
        self.song_id = song_id
        self.artist_id = artist_id
        self.album_id = album_id
        self.track_number = -1
        self.duration = -1
        self.fake = False

    def set_track_number(self, number):
        self.track_number = number

    def set_duration(self, duration):
        self.duration = duration

    def set_fake(self):
        # So we don't bother rendering
        self.fake = True

    def duration_string(self):
        if not self.duration:
            return "-"
        time_string = str(datetime.timedelta(seconds=self.duration))
        index=0
        for char in time_string:
            if char not in [":", "0"]:
                break
            index+=1
        return time_string[index:]

    def get_title(self):
        return self.title

    def get_song_id(self):
        return self.song_id

    def is_now_playing(self):
        return self.now_playing

    def set_now_playing(self, now_playing):
        self.now_playing = now_playing

    @GObject.Property(
        type=str, flags=GObject.ParamFlags.READWRITE, default=None
    )
    def song_title(self):
        return self.title

    def set_widget(self, widget):
        self.widget = widget
