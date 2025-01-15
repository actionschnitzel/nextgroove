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
from requests.auth import HTTPBasicAuth


class NextcloudMusicClient:

    _auth = None
    _base_url = None

    def __init__(self, server, user, token):
        self._base_url = f"{server}/index.php/apps/music/api"
        self._auth = HTTPBasicAuth(user, token)

    def _collection(self):
        return requests.get(f"{self._base_url}/collection", auth=self._auth)

    def validate(self):
        try:
            response = self._collection()
            if response.status_code == 200:
                return True
            else:
                return False
        except:
            # TODO better error handling and user messaging
            return False



    # Got ID as 121587 "my god is the sun"

#    response = requests.get(f"{url}/file/121587/download", auth=user_auth)
#    print(f"response on download is {response.status_code}")
#    with open("test.flac", "wb") as outfile:
#        outfile.write(response.content)
#print("DONE")


