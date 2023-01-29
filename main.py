from time import time
import logging
import operator

import redis
from fastapi import FastAPI, Request

from utils.serialization import Serialization

app = FastAPI()
redis_client = redis.Redis()


async def rate_limit(argument_dict):
    identifier = operator.itemgetter('identifier')(argument_dict)

    # time_span(in second)
    upper_time_span_in_second = 60
    upper_request_allowance = 100

    lower_time_span_in_second = 1
    lower_request_allowance = 3

    cur_time_in_second = int(time())

    if redis_client.exists(identifier) == 0:
        redis_set_prop_expire_dict(
            name=identifier,
            prop=cur_time_in_second,
            value=1,
            expire_time=upper_time_span_in_second,
            mapping=None
        )
    else:
        # get existing history
        timestamps = redis_client.hgetall(name=identifier)
        # enumerate timestamps:
        #   1. remove the expired one (cur_time - timestamp > upper_time_span)
        #   2. select largest timestamp
        #   3. cal total not expired request
        latest_timestamp_in_second = 0
        current_request_number = 0
        for prev_timestamp_in_second, count in timestamps.items():
            diff_second = cur_time_in_second - prev_timestamp_in_second
            if diff_second > upper_time_span_in_second:
                del timestamps[prev_timestamp_in_second]
            else:
                latest_timestamp_in_second = max(
                    latest_timestamp_in_second,
                    prev_timestamp_in_second
                )
                current_request_number += count

        # check whether current_request_number is bigger(inclusive) than upper_request_allowance:
        #   if false: reject request
        if current_request_number >= upper_request_allowance:
            return False
        #   if true:
        #      cal new timestamp_boundary, get counter from timestamp_counters if exist(init one if not), check count of the boundary
        #      if count is less than lower_request_allowance, add one to it, update upper_request_number
        #      else: reject
        diff_second = cur_time_in_second - latest_timestamp_in_second
        mod = diff_second % lower_time_span_in_second
        time_boundary = cur_time_in_second - mod

        if time_boundary in timestamps:
            cur_count = timestamps[time_boundary]
            if cur_count >= lower_request_allowance:
                return False

            timestamps[time_boundary] += 1
        else:
            timestamps[time_boundary] = 1

        redis_set_prop_expire_dict(
            name=identifier,
            mapping=timestamps,
            expire_time=upper_time_span_in_second,
            prop=None,
            value=None
        )
        return True


def redis_set_prop_expire_dict(name, prop, value, mapping, expire_time):
    if prop and value:
        redis_client.hset(name=name, key=prop, value=value)
    elif mapping:
        redis_client.delete(name)
        redis_client.hset(name=name, mapping=mapping)
    else:
        raise Exception("A prop/value pair or a mapping should be provided!")

    redis_client.expire(name=name, time=expire_time)


@app.get('/')
async def index(request: Request):
    ip_address = request.client.host
    request_is_accepted = False

    try:
        request_is_accepted = await Serialization.put_queue_by_tag(
            tag=ip_address,
            async_func=rate_limit
        )(identifier=ip_address)

    except Exception as e:

        logging.exception(e)
        request_is_accepted = False

    if request_is_accepted:
        return "This is a valid response!"
    else:
        return "Your request is rejected!"
