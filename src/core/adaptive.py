"""Conservative throughput probes; no claim that a fixed thread count is fastest."""
class AdaptiveConcurrency:
    def __init__(self, now):
        self.limit = 2
        self.last = now
        self.cooldown = now
        self.baseline = None
        self.previous_limit = 2
        self.last_error = now

    def error(self, now):
        self.limit = max(1, self.limit - 1)
        self.cooldown = now + 30
        self.last_error = now
        self.baseline = None
        self.last = now

    def sample(self, now, speed, active, queued, cpu, converting, rate_limit=0):
        if now - self.last < 10:
            return self.limit
        self.last = now
        if cpu >= 80 or converting:
            self.limit = max(1, self.limit - 1)
            self.baseline = None
            self.cooldown = now + 20
            return self.limit
        if now < self.cooldown or queued == 0 or active < self.limit or speed < 1024:
            return self.limit
        if self.baseline is not None:
            if speed < self.baseline * 1.08:
                self.limit = self.previous_limit
            self.baseline = None
            self.cooldown = now + 30
        elif self.limit < 4 and (not rate_limit or speed < rate_limit * 0.85):
            self.baseline = speed
            self.previous_limit = self.limit
            self.limit += 1
        return self.limit
