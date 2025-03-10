# client.py
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
from .queueitem import QueueItem


class AlbumListItem(GObject.Object):

    artist = None
    album = None
    cover_url = None
    album_id = None
    widget = None
    songs = None
    year = 0
    tracks = None

    def __init__(self, artist, album, cover_url, album_id):
        super().__init__()
        self.artist = artist
        self.album = album
        self.cover_url = cover_url
        self.album_id = album_id
        self.tracks = []

    def set_widget(self, widget):
        self.widget = widget

    def set_collection(self, collection):
        """Idea is to pass in the json details for the album, then we extract what we can"""
        self.year = collection.get("year", 0)
        for track in collection.get("tracks", []):
            print(f"Adding {track['title']} to album")
            song_id = list(track['files'].values())[0]
            self.tracks.append(QueueItem(track['title'], song_id, self.album_id, track['artistId']))
