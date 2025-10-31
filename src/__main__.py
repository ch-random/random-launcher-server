import argparse
import uvicorn
import multiprocessing

from . import app

if __name__ == "__main__":
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser()

    parser.add_argument("--host")
    parser.add_argument("target_dir") 

    args = parser.parse_args()

    host = args.host if args.host else "127.0.0.1"

    uvicorn.run(app, host=host, port=8080)
