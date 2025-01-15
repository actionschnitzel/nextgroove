# Copyright 2024 Dean Birch
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import GObject

class PlaylistItem(GObject.Object):

    playlist_name = ""
    track_ids = []
    playlist_id = ""
    cover = ""
    created = ""
    updated = ""

    def __init__(self, playlist_name, track_ids, playlist_id, cover, created, updated):
        super().__init__()
        self.playlist_name = playlist_name
        self.track_ids = track_ids
        self.playlist_id = playlist_id
        self.cover = cover
        self.created = created
        self.updated = updated

