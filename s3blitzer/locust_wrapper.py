import time
from locust import events


def func_wrapper(request_meta: dict = None):
    def _func_wrapper(func):
        def wrapper(*args, **kwargs):
            __request_meta = {
                "request_type": "",
                "name": "",
                "start_time": time.time(),
                "response_length": 0,
                "response": None,
                "context": {},
                "exception": None,
            }
            if request_meta:
                __request_meta.update(request_meta)

            start_perf_counter = time.perf_counter()

            try:
                func(*args, **kwargs)
            except Exception as e:
                __request_meta['exception'] = e

            __request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
            events.request.fire(**__request_meta)

        return wrapper
    return _func_wrapper


def method_wrapper(request_meta: dict = None):
    def _method_wrapper(func):
        def wrapper(self, *args, **kwargs):  # self object to wrap around class method
            __request_meta = {
                "request_type": "",
                "name": "",
                "start_time": time.time(),
                "response_length": 0,
                "response": None,
                "context": {},
                "exception": None,
            }
            if request_meta:
                __request_meta.update(request_meta)

            start_perf_counter = time.perf_counter()

            try:
                func(self, *args, **kwargs)
            except Exception as e:
                __request_meta['exception'] = e

            __request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
            events.request.fire(**__request_meta)

        return wrapper
    return _method_wrapper
