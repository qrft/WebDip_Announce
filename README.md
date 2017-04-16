# WebDip_Announce
Custom Announcements for WebDiplomacy games. The script was tested on webDiplomacy version 1.43

# How it works 
The script expects a settings file in valid json format (settings.json) in the same location. An example settings file is provided as settings_example.json.

# Local Notifications using notify-send
If your system uses libnotify and has the notify-send binary you could pipe the output of the script to show local notifications.
Example:
```
fetch.py | while read OUTPUT; do notify-send "$OUTPUT"; done
```

# Notification using stmplib
if `NOTIFYBYMAIL` is set, the script tries to use the function `mail_me` in `notify_mail.py` to send the mail. The mail addresses are defined in the settings as `users` (a dictionary of either Country:mailaddress or Username:mailaddress). Please note that the function `mail_me` is just an example. You should alter the function to fit your needs.

# Settings
| Value        |  Information          | Type  |
| ------------- |:-------------:| -----:|
| gameID      | "123456" | string |
| gameURL      | "http://webdiplomacy.net/board.php?"      |   string |
| ONESHOT | if set to true, the script runs only once. Otherwise it runs continuously waiting the specified time (`WAITTIME`)   |    boolean |
| WAITTIME | Time to wait (in minutes) until refreshing. Works only if `ONESHOT` is `true`   |    integer |
| TURNWARNING | Time in hours when the first warning should be sent that no orders were issued.   |    integer |
| TURNFATAL | Time in hours when a urgent warning should be sent that no orders were issued.   |    integer |
| ANNOUNCESTATUSCHANGE | If true, also announce if a player changed his status.   |    boolean |
| SAVEPATH | Path where the database file is stored. Default: scriptpath. Has to end with the delimier ('/'), can be absolute or relative to scriptpath   |    string |
| NOTIFYBYMAIL | If true, try to send notification by mail using the `mail_me` function   |   boolean |
| users | A dictionary with username and email-addresses used by `mail_me`.  |  dictionary |
| NOTIFYBYSTDOUT | If true, print the notification to the `stdout`  |   boolean |

# Roadmap
* support multiple gameIDs


