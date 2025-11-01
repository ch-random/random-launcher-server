import uvicorn
import multiprocessing

from . import app, settings

if __name__ == "__main__":
    multiprocessing.freeze_support()

    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
