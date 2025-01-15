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

import requests
import json
import os
from requests.auth import HTTPBasicAuth
from gi.repository import GObject, Gio


class NextcloudMusicClient(GObject.Object):

    _auth = None
    _base_url = None
    collection = None

    def __init__(self, server, user, token):
        super().__init__()
        self._base_url = f"{server}/index.php/apps/music/api"
        self._auth = HTTPBasicAuth(user, token)

    def _collection(self):
        return requests.get(f"{self._base_url}/collection", auth=self._auth)

    def validate(self):
        # FIXME remove this call, this is just testing the function prior to getting the async shit in place
        self.update_collection()
        try:
            response = self._collection()
            if response.status_code == 200:
                return True
            else:
                return False
        except:
            # TODO better error handling and user messaging
            return False

    def validate_async(self, callback):
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.run_in_thread(self.validate_sync)

    def validate_sync(self, task, source_object, task_data, cancellable):
        valid = self.validate()
        task.return_value(valid)

    def update_collection(self):
        try:
            response = self._collection()
            if response.status_code != 200:
                print(f"return code was {response.status_code}")
                return None
            self.collection = json.loads(response.text)
            return self.collection
        except requests.exceptions.RequestException as e:
            # TODO better error handling and user messaging
            print(f"Exception in updating collection {e}")
            return None

    def collection_async(self, callback):
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.run_in_thread(self.collection_sync)

    def collection_sync(self, task, source_object, task_data, cancellable):
        collection = self.update_collection()
        task.return_value(collection)

    def get_song(self, song_id):
        print(f"Attempting to call {self._base_url}/file/{song_id}/download")
        response = requests.get(f"{self._base_url}/file/{song_id}/download", auth=self._auth)
        if not os.path.exists(f"/tmp/net.rosebirch.nextcloudmusic/"):
            os.makedirs(f"/tmp/net.rosebirch.nextcloudmusic/")
        song_location = f"/tmp/net.rosebirch.nextcloudmusic/{song_id}"
        with open(song_location, "wb") as song_file:
            song_file.write(response.content)
        return os.path.abspath(song_location)

