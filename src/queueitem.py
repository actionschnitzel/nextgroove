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

class QueueItem(GObject.Object):

    title = None
    song_id = None
    now_playing = None

    def __init__(self, title, song_id):
        super().__init__()
        self.title = title
        self.song_id = song_id

    def get_title(self):
        return self.title

    def get_song_id(self):
        return self.song_id

    def is_now_playing(self):
        return self.now_playing

    def set_now_playing(self, now_playing):
        self.now_playing = now_playing
