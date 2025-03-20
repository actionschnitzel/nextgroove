#  NextGroove

GNOME based client for Nextcloud Music created as a holiday programming
project and therefore its functionality is quite limited: check the current capabilities section.

![a](screenshots/screenshot1.png "Screenshot of NextGroove")

## Current Capabilities

 - Connects to a Nextcloud instance of your choice via normal API tokens (does not use subsonic/ampache endpoints but the [Nextcloud ones](https://github.com/owncloud/music?tab=readme-ov-file#api)
 - Can select music from an album view (most recent first), filtering by an artist first, or playlists.
 - Allows adding albums/playlists/songs to the queue, either at the end or after the current song.
 - Basic MPRIS support allowing to be controlled via common controls and shortcuts.
 - Does *not* support shuffle play or repeating the queued music.
 - Does *not* support other media like podcasts.
 - Does *not* cache music/album-art/collection details. Therefore this will do many calls on every startup to retrieve album art. This was tested with the server sitting next to the desktop running this client.

## Contributing and Issues

Haven't defined a contributing guide yet at such an early stage.
Pushing the project out there to see if anyone finds this useful.
