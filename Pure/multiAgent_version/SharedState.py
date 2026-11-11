import asyncio

class SharedState:
    def __init__(self, expected_workers: int):
        self.expected_workers = expected_workers
        self.lock = asyncio.Lock()
        self.boards = {}
        self.events = {}

    async def publish_and_wait(self, round_num: int, worker_id: int, answer: str, thought: str):
        async with self.lock:
            if round_num not in self.boards:
                self.boards[round_num] = {}
                self.events[round_num] = asyncio.Event()

            self.boards[round_num][worker_id] = {"answer": answer, "thought": thought}

            if len(self.boards[round_num]) == self.expected_workers:
                self.events[round_num].set()

        await self.events[round_num].wait()

        return self.boards[round_num]