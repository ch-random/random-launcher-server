import os
import re
import shutil

import json
import datetime
import time
import uuid
from zipfile import ZipFile

import threading
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pipe, Lock, Event

from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler, RegexMatchingEventHandler

from .abc import *
from .content import Content, ContentSource, ContentList

class FileSystemNothingEvent(FileSystemEvent):
    event_type = "nothing"
    def __init__(self):
        super().__init__("")

class CustomObserver(Observer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kill_interval = Event()
        self.thread = None

    def start_interval(self):
        nothing_ev = FileSystemNothingEvent()
        while self.kill_interval.wait(timeout=1) is not True:
            for emitter in self.emitters:
                emitter.queue_event(nothing_ev)

    def on_thread_start(self):
        super().on_thread_start()
        self.thread = threading.Thread(target=self.start_interval)
        self.thread.start()

    def on_thread_end(self):
        if self.thread is not None:
            self.kill_interval.set()
            self.thread.join(10)
        super().on_thread_end()

class ContentsHandler(RegexMatchingEventHandler):
    def __init__(self, contents_dir: str, conn: Pipe, *, max_workers : int = 2):
        super().__init__(regexes=[r".*\.zip$",])

        self.contents_dir = contents_dir
        self.conn = conn
        self.lock = Lock()

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing = {}

        self.uuids = None

        self._sleep_dur = 0.0
        self._shutdown = False

    def set_delay(self, duration: float = 0.0):
        self._sleep_dur = duration

    def shutdown(self):
        self._shutdown = True
        self.executor.shutdown()

    def get_uuid(self, name):
        uuid_path = os.path.join(self.contents_dir, ".uuids.json")
        uuid_backup_path = os.path.join(self.contents_dir, ".uuids.json.backup")

        if self.uuids is None:
            # try to load
            try:
                with open(uuid_path, mode="rb") as f:
                    self.uuids = json.load(f)
            except:
                # try to load from backup
                try:
                    with open(uuid_backup_path, mode="rb") as f:
                        self.uuids = json.load(f)
                except:
                    # fallback
                    self.uuids = {}

        result = self.uuids.get(name, None)

        if result is None:
            # new content
            while result is None or result in self.uuids.values():
                # これが無限ループになる場合それは世界の法則が崩壊したときなので気にせず実装
                result = str(uuid.uuid4())

            self.uuids[name] = result

            try:
                shutil.copy(uuid_path, uuid_backup_path)
            except:
                # TODO: show warning
                pass

            try:
                with open(uuid_path, mode="w") as f:
                    json.dump(self.uuids, f, indent=2)
            except:
                # TODO: show warning
                pass

        print(result)

        return result

    def sync_content_recv(self):
        with self.lock:
            while self.conn.poll(0):
                path = self.conn.recv()
                try:
                    print("wa", path)
                    os.remove(path)
                except:
                    pass

    def sync_content(self, src, dest, modified_time):
        with self.lock:
            print("sync", src, dest)
            if dest is not None:
                try:
                    content_path = os.path.normpath(os.path.join(self.contents_dir, os.path.basename(dest)))
                    shutil.copy(dest, content_path)
                    with ZipFile(content_path) as zf:
                        if zf.getinfo("manifest.json"):
                            with zf.open("manifest.json", mode="r") as f:
                                meta = json.load(f)
                            meta["id"] = self.get_uuid(meta["name"])
                            meta["last_modified"] = modified_time.astimezone(datetime.timezone.utc)
                            content = Content.parse_obj(meta)
                        else:
                            return
                    final_path = os.path.normpath(os.path.join(self.contents_dir, f"{meta["id"]}.zip"))
                    print(content_path, final_path)
                    shutil.move(content_path, final_path)
                except Exception as e:
                    print(e)
                    return

                csrc = ContentSource(path=final_path, orig_path=content_path, content=content)

                print(csrc)

                self.conn.send(csrc)

        if src is not None and src != dest:
            prev_path = os.path.normpath(os.path.join(self.contents_dir, os.path.basename(src)))
            try:
                print("prev", prev_path)
                self.conn.send(ContentSource(path=None, orig_path=prev_path, content=None))
            except:
                pass

        self.sync_content_recv()

    def check_modify_finished(self, src, dest, timestamp):
        print("check_modify_finished", src, dest)
        delay = 0.0
        if dest is not None:
            for i in range(self._sleep_dur * 10):
                if self._shutdown:
                    return
                time.sleep(0.1)
                delay += 0.1

            if dest not in self.processing or self.processing[dest] != timestamp:
                # something changed
                return

            try:
                current = os.stat(dest).st_mtime
            except FileNotFoundError:
                return

            print(timestamp, current)

            if timestamp != current:
                # something implicitly changed
                return

        if not self._shutdown:
            tz = datetime.timezone(datetime.timedelta(seconds=time.timezone))
            self.sync_content(src, dest, datetime.datetime.fromtimestamp(timestamp, tz=tz) + datetime.timedelta(seconds=delay))

    def dispatch(self, event):
        if event.event_type == "nothing":
            self.on_nothing(event)
        else:
            super().dispatch(event)

    def on_nothing(self, event):
        # called on interval
        self.executor.submit(self.sync_content_recv)

    def on_created(self, event):
        if event.is_directory:
            return

        try:
            timestamp = os.stat(event.src_path).st_mtime
        except FileNotFoundError:
            return

        self.processing[event.src_path] = timestamp

        self.executor.submit(self.check_modify_finished, None, event.src_path, timestamp)

    def on_moved(self, event):
        if event.is_directory:
            return

        try:
            timestamp = os.stat(event.dest_path).st_mtime
        except FileNotFoundError:
            return

        self.processing[event.dest_path] = timestamp

        self.executor.submit(self.check_modify_finished, event.src_path, event.dest_path, timestamp)

    def on_deleted(self, event):
        if event.is_directory:
            return

        timestamp = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()

        self.processing[event.src_path] = timestamp

        self.executor.submit(self.check_modify_finished, event.src_path, None, timestamp)

    def on_modified(self, event):
        if event.is_directory:
            return

        try:
            timestamp = os.stat(event.src_path).st_mtime
        except FileNotFoundError:
            return

        self.processing[event.src_path] = timestamp

        self.executor.submit(self.check_modify_finished, event.src_path, event.src_path, timestamp)

