from threading import Thread
from os.path import basename,splitext,join,normpath
from sys import platform,path,executable
from os import environ,makedirs,system
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
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
        base=environ['APPDATA']
    elif platform=='darwin':
        base=join(environ['HOME'],'Library','Application Support')
    else:
        base=join(environ['HOME'],'.config')
    return join(base,name)

def pip_install(*args,target=join(get_data_dir(),'packages')):
    from sys import path
    path.append(target)
    if('--no-pip' in sys.argv):
        print('skipping pip install')
        return
    from sys import platform
    import importlib.util
    if platform=='win32' and importlib.util.find_spec('obspython') is not None:
        from configparser import ConfigParser
        config=ConfigParser()
        obs_ini_path=join(get_data_dir('obs-studio'),'global.ini')
        obs_ini=open(obs_ini_path,'r',encoding='utf-8')
        config.read_string(obs_ini.read().replace('\ufeff',''))
        obs_ini.close()
        from sys import maxsize
        if maxsize > 2**32: # https://docs.python.org/3/library/platform.html#platform.architecture
            python=config['Python']['path64bit']
        else:
            python=config['Python']['path32bit']
        python=join(python,'python.exe')
    else:
        from sys import executable
        python=executable
    from subprocess import run
    run([python,'-m','pip','install','--no-warn-script-location','--progress-bar=off','--upgrade','--target='+target,*args],shell=True)

def start_server(static_dir=join(get_data_dir(),'static')):
    pathFunctions={} # Dict{requestlineregex:function}
    class RegexRequestHandler(SimpleHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,format,*args):
            print(format % args)
        def translate_path(self,path):
            path=normpath(join(static_dir,path))
            if path.startswith(static_dir):
                return path
            self.send_error(403)
            return static_dir
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin','*')
            super().end_headers()
        def do_DISPATCH(self):
            from re import match
            for requestline, function in pathFunctions.items():
                if(match(requestline,self.requestline)):
                    return function(self)!=False
            return False
        def do_GET(self):
            self.do_DISPATCH() or super().do_GET()
        def do_HEAD(self):
            self.do_DISPATCH() or super().do_HEAD()
        def do_POST(self):
            self.do_DISPATCH()
        def do_PUT(self):
            self.do_DISPATCH()
        def do_DELETE(self):
            self.do_DISPATCH()
        def do_OPTIONS(self):
            self.do_DISPATCH()
    def audio(request):
        import sounddevice,numpy
        if request.path == '/audio/':
            response=json.dumps(sounddevice.query_devices(kind='input'))
            if response.startswith('{'):
                response="["+response+"]"
            response+="\n"
            request.send_response(200)
            request.send_header('Content-Type','text/json')
            request.send_header('Content-Length',str(len(response)))
            request.end_headers()
            request.wfile.write(response.encode())
            return
        device=urllib.parse.unquote(request.path[len('/audio/'):]) or None
        try:
            sounddevice.check_input_settings(device=device)
            request.send_response(200)
            request.send_header('Content-Type','text/event-stream')
            request.end_headers()
        except Exception as e:
            request.send_error(500,explain=str(e))
        def audioCallback(indata, frames, time, status):
            try:
                volume=numpy.linalg.norm(indata)*10
                message='data: '+str(volume)+'\n\n'
                request.wfile.write(message.encode())
                request.wfile.flush()
            except:
                print_exc()
        with sounddevice.InputStream(device=device,callback=audioCallback):
            while not request.wfile.closed:
                sounddevice.sleep(16)
    pathFunctions['GET /audio']=audio
    sseClients={} # dict[path]=list[bytesio]
    def sseSend(path:str,message:str,event:str=None,id:str=None):
        if(path not in sseClients):
            return False
        if(len(sseClients[path])==0):
            return False
        sent=False
        for wfile in sseClients[path]:
            if wfile.closed:
                continue
            if id:
                wfile.write(('id: '+id+'\n').encode())
            if event:
                wfile.write(('event: '+event+'\n').encode())
            for part in message.split('\n'):
                wfile.write(('data: '+part+'\n').encode())
            wfile.write('\n'.encode())
            wfile.flush()
            sent=True
        return sent
    def sseGet(request:RegexRequestHandler):
        if request.path not in sseClients:
            sseClients[request.path]=[]
        sseClients[request.path].append(request.wfile)
        request.send_response(200)
        request.send_header('Content-Type','text/event-stream')
        request.end_headers()
        sseSend('/sse',request.path)
    def ssePost(request:RegexRequestHandler):
        message=request.rfile.read(int(request.headers['Content-Length'])).decode()
        event=request.headers['event']
        id=request.headers['id']
        if not sseSend(request.path,message,event,id):
            request.send_error(404)
        else:
            request.send_response(204)
        request.end_headers()
    def sseOptions(request:RegexRequestHandler):
        request.send_response(204)
        request.send_header('Access-Control-Allow-Headers', 'event,id')
        request.end_headers()
    pathFunctions['GET /sse']=sseGet
    pathFunctions['POST /sse/']=ssePost
    pathFunctions['OPTIONS /sse/']=sseOptions
    
    global server
    server=ThreadingHTTPServer(('localhost',5000), RegexRequestHandler)
    Thread(target=server.serve_forever,name='sugoiobs.py HTTPServer').start()

def open_data_dir(*args):
    if platform=='win32':
        command='explorer /e,"'
    elif platform=='darwin':
        command='open "'
    else:
        command='xdg-open "'
    command+=get_data_dir()+'"'
    Popen(command)

def update():
    if('--no-update' in sys.argv):
        print('skipping self update')
        return
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
            sys.stderr.write("update downloaded, please restart the program\n")
            return True
        f.close()
    except:
        print('The auto-updater encountered an issue')
        print_exc()
        print('The script will continue with the current version')
    return False

def init():
    update()
    pip_install('sounddevice','numpy')
    start_server()

def script_load(settings):
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
    init()
    input('Press enter to stop\n')
    script_unload()