# Media-Convert

Media-Convert was built out of a need to take 18 TB of data and normalize it into one single format automatically. The goal is to have this script run on a schedule.

The script will search all files and either re-encode files that do not meet target criteria or switch container for those applicaple files.

### Required Software
1. ffmpeg
2. MediaInfo (included)


### How to setup
1. First insure ffmpeg and Handbrake are setup on your machine
2. Open handbrake and either import my plex-cc.plist or create your own and name it plex-cc.
3. In the media_convert.py, add a set of paths to the watched_folders list.
4. Configure variables, generally I set JUST_CHECK to True for first run to get a jist. Then DELETE = False on second run on small set of videos to ensure my handbrake settings are fine.


If you enjoy this program, please let me know. If you find better handbrake settings, please create a pull request or message me.
