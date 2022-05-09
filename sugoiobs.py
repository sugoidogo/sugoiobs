from threading import Thread
from os.path import basename,splitext,join
from sys import platform,path,executable
from os import environ,makedirs,system
from http.server import HTTPServer,SimpleHTTPRequestHandler
from traceback import format_exc,print_exc
from urllib.request import urlopen
import pip
import sys
import urllib

try:
    from obspython import *
except:
    pass

server=None

def get_data_dir(name=None):
    if name == None:
        name=splitext(basename(__file__))[0]
    if platform=='win32':
        base=environ['appdata']
    else:
        base=environ['HOME']
    return join(base,name)

def pip_install(*args,target=join(get_data_dir(),'packages')):
    path.insert(1, target)
    pip.main(['install','--no-warn-script-location','--progress-bar=off','--target='+target,'--upgrade',*args])

def silence(log_path=join(get_data_dir(),'sugoiobs.log')):
    log_file=open(log_path,'wb')
    sys.stdout=log_file
    sys.stderr=log_file

def start_server(static_dir=join(get_data_dir(),'static')):
    class PluginHTTPRequestHandler(SimpleHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        sse={}
        def initSSEPath(self,path):
            sse[path]={
                history:[],
                clients:[]
            }
        def translate_path(self, path):
            return join(static_dir,path[1:])
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            return super().end_headers()
        def do_ERROR(self,e):
            self.send_error(500,str(e),format_exc())
        def do_PUT_SSE(self):
            if self.path not in sse.keys():
                self.initSSEPath(self.path[1:])
            message=self.rfile.read()
            sse[self.path].history.append(message)
            self.send_response(202)
            for client in sse[self.path].clients:
                if not client.closed:
                    client.write(message+'\n\n'.encode())
                    client.flush()
        def do_PUT(self):
            try:
                if(self.path.endswith("#sse")):
                    return self.do_PUT_SSE()
                else:
                    file_path=translate_path(self.path)
                    file=open(file_path,'wb')
                    file.write(self.rfile)
                    file.close()
                    return self.send_response(200)
            except Exception as e:
                return self.do_ERROR(e)
        def do_GET_SSE(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                if self.path not in sse.keys():
                    self.initSSEPath(self.path)
                for message in sse[self.path].history:
                    self.wfile.write(message+'\n\n'.encode())
                sse[self.path].clients.append(self.wfile)
        def do_GET_AUDIO(self):
            import sounddevice,numpy
            if self.path == '/audio/':
                response=json.dumps(sounddevice.query_devices(kind='input'))
                if response.startswith('{'):
                    response="["+response+"]"
                response+="\n"
                self.send_response(200)
                self.send_header('Content-Type','text/json')
                self.send_header('Content-Length',str(len(response)))
                self.end_headers()
                self.wfile.write(response.encode())
                return
            device=urllib.parse.unquote(self.path[len('/audio/'):]) or None
            try:
                sounddevice.check_input_settings(device=device)
                self.send_response(200)
                self.send_header('Content-Type','text/event-stream')
                self.end_headers()
            except Exception as e:
                self.send_error(500,explain=str(e))
            def audioLoop():
                def audioCallback(indata, frames, time, status):
                    try:
                        volume=numpy.linalg.norm(indata)*10
                        message='data: '+str(volume)+'\n\n'
                        self.wfile.write(message.encode())
                        self.wfile.flush()
                    except:
                        pass
                with sounddevice.InputStream(device=device,callback=audioCallback):
                    while not self.wfile.closed:
                        sounddevice.sleep(1)
            Thread(target=audioLoop,name='sugoiobs.py audioLoop').start()
        def do_GET(self):
            try:
                if self.path.startswith('/audio'):
                    return self.do_GET_AUDIO()
                elif(self.path.endswith("#sse")):
                    return self.do_GET_SSE()
                else:
                    return super().do_GET()
            except Exception as e:
                return self.do_ERROR(e)
    makedirs(static_dir,exist_ok=True)
    global server
    server=HTTPServer(('localhost',5000), PluginHTTPRequestHandler)
    Thread(target=server.serve_forever,name='sugoiobs.py HTTPServer').start()

def open_data_dir(*args):
    if platform=='win32':
        command='explorer /e,"'
    elif platform=='darwin':
        command='open "'
    else:
        command='xdg-open "'
    command+=get_data_dir()+'"'
    print(command)
    Popen(command)

def update():
    try:
        u=urlopen('https://github.com/sugoidogo/sugoiobs/releases/latest/download/sugoiobs.py')
        new=u.read()
        u.close
        f=open(__file__,'r+b')
        old=f.read()
        if(old != new):
            f.seek(0)
            f.truncate()
            f.write(new)
        f.close()
        return old != new
    except:
        print('The auto-updater encountered an issue')
        print_exc()
        print('The script will continue with the current version')
        return False

def init():
    pip_install('sounddevice','numpy')
    start_server()

def script_load(settings):
    if update():
        print('Update downloaded, please restart OBS')
    silence()
    Thread(target=init,name='sugoiobs.py init').start()

def script_unload():
    global server
    Thread(target=server.shutdown,name='sugoiobs.py HTTPServer.shutdown').start()

def script_properties():
    props=obs_properties_create()
    obs_properties_add_button(props, 'datadir','Open data folder',open_data_dir)
    return props

def script_description():
    return """
    SugoiOBS starts a web server exposing extra functionality from OBS and the OS
    """

if __name__ == '__main__':
    if update():
        print('Update downloaded, restarting')
        exit(system(executable+' '+__file__))
    else:
        init()
        input('Press enter to stop\n')
        script_unload()