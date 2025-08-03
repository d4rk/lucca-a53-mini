import threading
import asyncio
import queue
from characteristics import list_characteristics

class BLEWorker:
    def __init__(self):
        self.cmd_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.loop = None
        self.running = False

    def start(self):
        self.running = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.cmd_queue.put(('stop', None))
        self.thread.join()

    def list_characteristics(self, address, poll_interval=0):
        self.cmd_queue.put(('list_characteristics', (address, poll_interval)))
        return self.result_queue

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        while self.running:
            try:
                cmd, args = self.cmd_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if cmd == 'stop':
                break
            elif cmd == 'list_characteristics':
                address, poll_interval = args
                coro = list_characteristics(address, poll_interval)
                result = self.loop.run_until_complete(coro)
                self.result_queue.put(result)
        self.loop.close()
