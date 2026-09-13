class Trace:
    def __init__(self):
        self.enabled = True

    def __call__(self, fn):
        def wrap(*args, **kwargs):
            if self.enabled:
                print('Calling {}'.format(fn))
            return fn(*args, **kwargs)

        return wrap


tracer = Trace()
