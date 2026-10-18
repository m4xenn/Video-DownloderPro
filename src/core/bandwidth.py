"""One cancellable bandwidth budget shared by every native yt-dlp response."""
import threading
import time


class DownloadPaused(Exception):
    pass


class BandwidthBudget:
    def __init__(self, rate=0, clock=time.monotonic):
        self.condition = threading.Condition()
        self.clock = clock
        self.rate = rate
        self.tokens = 0.0
        self.updated = clock()

    def configure(self, rate):
        if not isinstance(rate, int) or isinstance(rate, bool) or rate < 0:
            raise ValueError('Geçersiz toplam hız sınırı.')
        with self.condition:
            self.rate = rate
            self.tokens = 0
            self.updated = self.clock()
            self.condition.notify_all()

    def chunk_size(self):
        with self.condition:
            return min(16384, max(1, self.rate // 10)) if self.rate else 65536

    def acquire(self, count, cancelled=lambda: False):
        remaining = count
        with self.condition:
            while remaining:
                if cancelled():
                    raise DownloadPaused('DOWNLOAD_PAUSED')
                if not self.rate:
                    return
                now = self.clock()
                capacity = min(16384, max(1, self.rate / 10))
                self.tokens = min(capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                used = min(remaining, int(self.tokens))
                remaining -= used
                self.tokens -= used
                if remaining:
                    self.condition.wait(min(0.1, max(0.001, min(remaining, capacity) / self.rate)))


class BudgetReader:
    def __init__(self, response, budget, cancelled, record):
        self.response, self.budget = response, budget
        self.cancelled, self.record = cancelled, record

    def __getattr__(self, name):
        return getattr(self.response, name)

    def read(self, amount=None):
        if amount == 0:
            return b''
        if amount is None or amount < 0:
            chunks = []
            while True:
                chunk = self.read(self.budget.chunk_size())
                if not chunk:
                    return b''.join(chunks)
                chunks.append(chunk)
        if self.cancelled():
            raise DownloadPaused('DOWNLOAD_PAUSED')
        size = min(amount, self.budget.chunk_size())
        self.budget.acquire(size, self.cancelled)
        chunk = self.response.read(size)
        if chunk:
            self.record(len(chunk))
        return chunk


def attach_budget(ydl, budget, cancelled, record):
    from yt_dlp.networking.common import Response
    original = ydl.urlopen

    def urlopen(request):
        if cancelled():
            raise DownloadPaused('DOWNLOAD_PAUSED')
        response = original(request)
        return Response(BudgetReader(response, budget, cancelled, record), response.url,
                        response.headers, response.status, response.reason, response.extensions)

    ydl.urlopen = urlopen
