import signal
import os
import os.path
import time
from typing import Optional
from multiprocessing import Process, Pipe

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

import glob
from watchdog.events import FileCreatedEvent

import fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .api import api, content_manager
from .observe import CustomObserver, ContentsHandler

host = ""

contents_dir = os.path.normpath(os.path.join(__file__, "../../contents"))
print("contents dir:", contents_dir)

try:
    os.mkdir(contents_dir)
except FileExistsError:
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pipe for fastapi and observer to communicate with each other
    (conn_fastapi, conn_observer) = Pipe(duplex=True)

    content_manager.set_connection(conn_fastapi)

    ftp_process = Process(target=start_ftpserver)
    obs_process = Process(target=start_observer, args=(conn_observer,))

    ftp_process.start()
    obs_process.start()
    
    yield

    conn_fastapi.close()
    conn_observer.close()

    ftp_process.kill()
    obs_process.kill()

    ftp_process.join(3)
    ftp_process.terminate()
    obs_process.join(3)
    obs_process.terminate()

app = FastAPI(lifespan=lifespan)

app.include_router(api)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def start_observer(conn: Pipe):
    target_dir = os.path.normpath(os.path.join(contents_dir, "../testsrc"))
    print("start observe for", target_dir)
    handler = ContentsHandler(contents_dir, conn)
    handler.set_delay(0)
    observer = CustomObserver()
    observer.schedule(handler, target_dir, recursive=False)

    def on_exit(signum, frame):
        observer.stop()

    signal.signal(signal.SIGTERM, on_exit)
    signal.signal(signal.SIGINT, on_exit)

    for path in glob.glob(os.path.join(target_dir, "*.zip")):
        print(path)
        ev = FileCreatedEvent(path)
        for emitter in observer.emitters:
            emitter.queue_event(ev)

    observer.start()
    try:
        time.sleep(3)
        handler.set_delay(3)
        observer.join()
        print("obs stop")
    finally:
        observer.stop()

def create_ftpserver():
    # https://pyftpdlib.readthedocs.io/en/latest/tutorial.html#a-base-ftp-server

    # Instantiate a dummy authorizer for managing 'virtual' users
    authorizer = DummyAuthorizer()

    # Define a read-only anonymous user
    authorizer.add_anonymous(contents_dir)

    # Instantiate FTP handler class
    handler = FTPHandler
    handler.authorizer = authorizer

    # Define a customized banner (string returned when client connects)
    handler.banner = "pyftpdlib based FTP server ready."

    # Specify a masquerade address and the range of ports to use for
    # passive connections.  Decomment in case you're behind a NAT.
    #handler.masquerade_address = '151.25.42.11'
    #handler.passive_ports = range(60000, 65535)

    # Instantiate FTP server class and listen on all interfaces, port 21
    address = (host, 2121)
    server = FTPServer(address, handler)

    # set a limit for connections
    server.max_cons = 256
    server.max_cons_per_ip = 5

    return server

def start_ftpserver():
    server = create_ftpserver()

    def on_exit(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, on_exit)
    signal.signal(signal.SIGINT, on_exit)

    server.serve_forever(handle_exit=True)
    print("ftp stop")
