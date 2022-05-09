# SugoiOBS
A plugin script for OBS exposing additional functionality via a web server.
## Getting started
On Windows, OBS requires you manually locate a Python 3.6 interpreter before you can use Python plugin scripts. [This installer]() can automate that process for you. On all other platforms, install python as usual.
## Running the script
This script is primarily designed to run as an OBS plugin script, via the `Tools > Scripts` menu, but it can also be run standalone. When used as an OBS plugin script, the server is automatically started and stopped with obs, and a log file is generated in the script's data folder. When run standalone, the log is output directly to console. Specifically, `stdout` and `stderr` are redirected to a file when run under obs, because both `pip` and `http.server` are very verbose and each line output triggers obs to pop up the script log. This may cause any other python scripts running in obs to output to the sugoiobs log file as well, because OBS appears to run all scripts under one interpreter instance. **This is considered a bug and any PR attempting to fix it is welcome.**
## GET and PUT
The web server doesn't come with any data to `GET`, but you can `PUT` data to any path under the web root that you'd want to get later.
## Server Sent Events
Using the hash `#sse` at the end of any path causes the web server to treat it as an SSE endpoint. `GET` requests will immediately receive the SSE headers and the history of any messages `PUT` to the same path, along with any future messages. `PUT` requests will receive a `202` response once the data has been stored in the history buffer, and then the data is sent to each connected SSE client.
## Audio Levels
A basic audio level endpoint is availible for clients to get the current audio level of any audio input device. `GET /audio/` will return a JSON-encoded list of availible audio devices, `GET /audio/devicename` is an SSE endpoint that will send the current audio level as an interger string, and `GET /audio` will do the same with the default input device.