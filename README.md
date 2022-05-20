# SugoiOBS
A plugin script for OBS exposing additional functionality via a web server.
## Getting started
On Windows, OBS requires you manually locate a Python 3.6 interpreter before you can use Python plugin scripts. [This installer](https://github.com/sugoidogo/obs-python-installer) can automate that process for you. On all other platforms, install python as usual. Then you can [download this script](https://github.com/sugoidogo/sugoiobs/releases/latest/download/sugoiobs.py)
## Running the script
This script is primarily designed to run as an OBS plugin script, via the `Tools > Scripts` menu, but it can also be run standalone. When used as an OBS plugin script, the server is automatically started and stopped with obs, and a log file is generated in the script's data folder. When run standalone, the log is output directly to console. Specifically, `stdout` and `stderr` are redirected to a file when run under obs, because both `pip` and `http.server` are very verbose and each line output triggers obs to pop up the script log. This may cause any other python scripts running in obs to output to the sugoiobs log file as well, because OBS appears to run all scripts under one interpreter instance. **This is considered a bug and any PR attempting to fix it is welcome.**
## Server Sent Events
`/sse` and all paths under it are essentially message relays using SSE. Any data `POST`ed to a path will be sent to all clients connected to that same path. Note that the path includes any query or hash strings. The root `/sse` path cannot be `POST`ed to, and is reserved for informing event sources that a new client has connected, allowing them to only start sending events when a client is there to receive them. Any program on `localhost` can post to any path, so make sure to use unique path names to avoid conflicts.
## Audio Levels
A basic audio level endpoint is availible for clients to get the current audio level of any audio input device. `GET /audio/` will return a JSON-encoded list of availible audio devices, `GET /audio/devicename` is an SSE endpoint that will send the current audio level as an interger string, and `GET /audio` will do the same with the default input device. Note that there appears to be no upper limit on audio level, very loud noises may cause values over 100. This is considered a bug, and PRs are welcome.