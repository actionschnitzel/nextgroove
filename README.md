#  ActionGrooveNC

This project is a fork of [NextGroove](https://gitlab.gnome.org/dean36963/nextgroove). Since the original project is no longer maintained, ActionGrooveNC aims to continue its development, improve the existing codebase, and introduce further enhancements.


GNOME based client for Nextcloud Music created as a holiday programming
project and therefore its functionality is quite limited: check the current capabilities section.

![a](screenshots/screenshot1.png "Screenshot of ActionGrooveNC")

## Current Capabilities

 - Connects to a Nextcloud instance of your choice.
 - Can select music from an album view (most recent first), filtering by an artist first, or playlists.
 - Allows adding albums/playlists/songs to the queue, either at the end or after the current song.
 - Basic MPRIS support allowing to be controlled via common controls and shortcuts.
 - Drag&Drop to Queue 
 - Caches album art, and can optionally cache songs.
 - Can save current play queue as a playlist.
 - Adaptive and works at mobile resolution.
 - Does *not* support other media like podcasts.

## Contributing and Issues

Haven't defined a contributing guide yet at such an early stage.
Pushing the project out there to see if anyone finds this useful.

Raising issues is welcome, but I don't devote much time to this project.

A lot of the current code needs a heavy refactor into something much tidier
and using preferred patterns of signal based connections.
