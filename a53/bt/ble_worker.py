import threading
import asyncio
import queue
from a53.bt.characteristics import list_characteristics
from bleak import BleakClient

class BLEWorker:
    def __init__(self):
        self.cmd_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.loop = None
        self.running = False
        self._client = None

    def start(self):
        self.running = True
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        try:
            self.cmd_queue.put_nowait(('stop', None))
        except queue.Full:
            pass
        self.thread.join()

    def connect_device(self, address):
        q = queue.Queue()
        self.cmd_queue.put(('connect', (address, q)))
        return q

    def disconnect_device(self):
        q = queue.Queue()
        self.cmd_queue.put(('disconnect', q))
        return q

    def read_characteristic(self, uuid):
        q = queue.Queue()
        self.cmd_queue.put(('read', (uuid, q)))
        return q

    def write_characteristic(self, uuid, value):
        q = queue.Queue()
        self.cmd_queue.put(('write', (uuid, value, q)))
        return q

    def list_characteristics(self, address, poll_interval=0):
        q = queue.Queue()
        self.cmd_queue.put(('list_characteristics', (address, q, poll_interval)))
        return q

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def main_loop():
            polling_task = None
            while self.running:
                try:
                    cmd, args = self.cmd_queue.get_nowait()

                    if cmd == 'connect':
                        address, q = args
                        try:
                            self._client = BleakClient(address)
                            await self._client.connect()
                            q.put({"success": True})
                        except Exception as e:
                            q.put({"success": False, "error": str(e)})

                    elif cmd == 'disconnect' or cmd == 'stop':
                        q = args
                        try:
                            if self._client and self._client.is_connected:
                                await self._client.disconnect()
                            q.put({"success": True})
                        except Exception as e:
                            q.put({"success": False, "error": str(e)})
                        finally:
                            self._client = None

                    elif cmd == 'read':
                        uuid, q = args
                        try:
                            if self._client and self._client.is_connected:
                                value = await self._client.read_gatt_char(uuid)
                                q.put(value)
                            else:
                                q.put({"error": "Not connected"})
                        except Exception as e:
                            q.put({"error": str(e)})

                    elif cmd == 'write':
                        uuid, value, q = args
                        try:
                            if self._client and self._client.is_connected:
                                await self._client.write_gatt_char(uuid, value)
                                q.put({"success": True})
                            else:
                                q.put({"success": False, "error": "Not connected"})
                        except Exception as e:
                            q.put({"success": False, "error": str(e)})

                    elif cmd == 'list_characteristics':
                        address, q, poll_interval = args
                        # If a polling task is already running, cancel it before starting a new one.
                        if polling_task and not polling_task.done():
                            polling_task.cancel()

                        # list_characteristics now takes the client directly for polling
                        coro = list_characteristics(self._client, q, poll_interval)
                        task = self.loop.create_task(coro)

                        if poll_interval > 0:
                            polling_task = task

                except queue.Empty:
                    pass

                await asyncio.sleep(0.1)

            if polling_task and not polling_task.done():
                polling_task.cancel()
                try:
                    await asyncio.gather(polling_task, return_exceptions=True)
                except asyncio.CancelledError:
                    pass

            # Ensure client is disconnected on worker stop
            if self._client and self._client.is_connected:
                await self._client.disconnect()
            self._client = None

        try:
            self.loop.run_until_complete(main_loop())
        finally:
            self.loop.close()