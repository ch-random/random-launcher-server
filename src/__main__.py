import asyncio
import os
import os.path
from typing import Optional
from multiprocessing import Process

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

import fastapi
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .api import api

host = ""

contents_dir = os.path.normpath(os.path.join(__file__, "../contents"))
print("contents dir:", contents_dir)

try:
    os.mkdir(contents_dir)
except FileExistsError:
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    ftp_process = Process(target=start_ftpserver)

    ftp_process.start()
    
    yield

    ftp_process.kill()

    for i in range(100):
        if not ftp_process.is_alive():
            break
        await asyncio.sleep(0.1)

    ftp_process.terminate()

app = FastAPI(lifespan=lifespan)

app.include_router(api)

ftp_process = None

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
    server.serve_forever()

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()

    parser.add_argument("--host")

    args = parser.parse_args()

    host = args.host if args.host else "127.0.0.1"

    uvicorn.run(app, host=host, port=8000)
