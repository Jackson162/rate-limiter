from time import time
from operator import itemgetter

import redis
redis_client = redis.Redis()


class RateLimiter:
    # time_span(in second)
    upper_time_span_in_second = 60
    upper_request_allowance = 5
    lower_time_span_in_second = 1
    lower_request_allowance = 3

    def activate(self, argument_dict):
        identifier = itemgetter('identifier')(argument_dict)

        cur_time_in_second = int(time())

        if redis_client.exists(identifier) == 0:
            self.redis_set_prop_expire_dict(
                name=identifier,
                prop=cur_time_in_second,
                value=1,
                expire_time=self.upper_time_span_in_second,
                mapping=None
            )
        else:
            # get existing history
            timestamps_redis = redis_client.hgetall(name=identifier)
            timestamps: dict[int, int] = {}

            for key_bytes, val_bytes in timestamps_redis.items():
                key_str = key_bytes.decode(encoding="utf-8")
                key_int = int(key_str)

                val_str = val_bytes.decode(encoding="utf-8")
                val_int = int(val_str)
                timestamps[key_int] = val_int

            # enumerate timestamps:
            #   1. remove the expired one (cur_time - timestamp > upper_time_span)
            #   2. select largest timestamp
            #   3. cal total not expired request
            latest_timestamp_in_second = 0
            current_request_number = 0
            for prev_timestamp_in_second, count in timestamps.copy().items():

                diff_second = cur_time_in_second - prev_timestamp_in_second
                if diff_second > self.upper_time_span_in_second:
                    del timestamps[prev_timestamp_in_second]
                else:
                    latest_timestamp_in_second = max(
                        latest_timestamp_in_second,
                        prev_timestamp_in_second
                    )
                    current_request_number += count

            # check whether current_request_number is bigger(inclusive) than self.upper_request_allowance:
            #   if false: reject request
            if current_request_number >= self.upper_request_allowance:
                return False
            #   if true:
            #      cal new timestamp_boundary, get counter from timestamp_counters if exist(init one if not), check count of the boundary
            #      if count is less than self.lower_request_allowance, add one to it, update upper_request_number
            #      else: reject
            diff_second = cur_time_in_second - latest_timestamp_in_second
            mod = diff_second % self.lower_time_span_in_second
            time_boundary = cur_time_in_second - mod

            if time_boundary in timestamps:
                cur_count = timestamps[time_boundary]
                if cur_count >= self.lower_request_allowance:
                    return False

                timestamps[time_boundary] += 1
            else:
                timestamps[time_boundary] = 1

            self.redis_set_prop_expire_dict(
                name=identifier,
                mapping=timestamps,
                expire_time=self.upper_time_span_in_second,
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
            raise Exception(
                "A prop/value pair or a mapping should be provided!")

        redis_client.expire(name=name, time=expire_time)
