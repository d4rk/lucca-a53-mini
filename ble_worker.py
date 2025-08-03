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
        if not self.running:
            return
        self.running = False
        # Use put_nowait or a timeout to avoid blocking if the loop is dead
        try:
            self.cmd_queue.put_nowait(('stop', None))
        except queue.Full:
            pass  # Loop is likely already shutting down
        self.thread.join()

    def list_characteristics(self, address, poll_interval=0):
        self.cmd_queue.put(('list_characteristics', (address, self.result_queue, poll_interval)))
        return self.result_queue

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def main_loop():
            polling_task = None
            while self.running:
                try:
                    cmd, args = self.cmd_queue.get_nowait()

                    if cmd == 'stop':
                        break
                    
                    elif cmd == 'list_characteristics':
                        # If a polling task is already running, cancel it before starting a new one.
                        if polling_task and not polling_task.done():
                            polling_task.cancel()

                        coro = list_characteristics(*args)
                        task = self.loop.create_task(coro)
                        
                        # If the command is for polling, keep a reference to the task.
                        # The list_characteristics function itself handles the polling loop.
                        if args[2] > 0:  # poll_interval
                            polling_task = task

                except queue.Empty:
                    # No command in the queue, continue the async loop.
                    pass
                
                # Yield control to the event loop to allow other tasks to run.
                await asyncio.sleep(0.1)

            # Cleanup: Cancel the polling task if it's still running
            if polling_task and not polling_task.done():
                polling_task.cancel()
                # Wait for the task to acknowledge cancellation
                await asyncio.gather(polling_task, return_exceptions=True)

        try:
            self.loop.run_until_complete(main_loop())
        finally:
            self.loop.close()
