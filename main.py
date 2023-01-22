from time import time

from flask import Flask, request
import redis

app = Flask(__name__)
redis_client = redis.Redis()


def rate_limit(request):
    # time_span(in second)
    upper_time_span = 60
    upper_request_allowance = 100

    lower_time_span = 1
    lower_request_allowance = 3

    ip_address = request.remote_addr

    if redis_client.exists(ip_address) == 0:
        cur_time = int(time())
        init_access_history = {
            upper_request_number: 1,
            timestamp_counters: {cur_time: 1}
        }
        redis_client.hset(ip_address, mapping=init_access_history)


@app.route('/')
def index():
    rate_limit(request=request)
