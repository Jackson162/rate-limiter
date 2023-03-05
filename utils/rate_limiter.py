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
        no_identifier_exists = redis_client.exists(identifier) == 0

        if no_identifier_exists:
            self.redis_set_expired_dict_props(
                name=identifier,
                prop=cur_time_in_second,
                value=1,
                expire_time=self.upper_time_span_in_second,
                mapping=None
            )
        else:
            prev_timestamps = self.get_prev_timestamps(identifier=identifier)

            # enumerate prev_timestamps:
            #   1. remove the expired timestamps
            #   2. select largest timestamp
            #   3. cal total not expired request
            latest_timestamp_in_second = 0
            current_request_number = 0

            for prev_timestamp_in_second, count in prev_timestamps.copy().items():
                diff_second = cur_time_in_second - prev_timestamp_in_second
                timestamp_expired = diff_second > self.upper_time_span_in_second

                if timestamp_expired:
                    del prev_timestamps[prev_timestamp_in_second]
                    continue

                latest_timestamp_in_second = max(
                    latest_timestamp_in_second,
                    prev_timestamp_in_second
                )
                current_request_number += count

            # check whether current_request_number is bigger(inclusive) than self.upper_request_allowance:
            #   if true: reject request
            request_number_exceeds_upper_limit = current_request_number >= self.upper_request_allowance
            if request_number_exceeds_upper_limit:
                return False

            #   cal new cur_time_boundary
            cur_time_boundary = self.cal_cur_time_boundary(
                cur_time_in_second=cur_time_in_second, latest_timestamp_in_second=latest_timestamp_in_second)

            #  get counter from prev_timestamps if exist: check count of the boundary, else: init one
            if cur_time_boundary in prev_timestamps:
                #  if count is bigger(inclusive) than self.lower_request_allowance, reject
                #  else: add one to it
                cur_count = prev_timestamps[cur_time_boundary]
                request_number_exceeds_lower_limit = cur_count >= self.lower_request_allowance
                if request_number_exceeds_lower_limit:
                    return False

                prev_timestamps[cur_time_boundary] += 1
            else:
                prev_timestamps[cur_time_boundary] = 1

            self.redis_set_expired_dict_props(
                name=identifier,
                mapping=prev_timestamps,
                expire_time=self.upper_time_span_in_second,
                prop=None,
                value=None,
                overwrite=True
            )

        return True

    def redis_set_expired_dict_props(self, name, prop, value, mapping, expire_time, overwrite=False):

        if overwrite:
            redis_client.delete(name)

        if prop and value:
            redis_client.hset(name=name, key=prop, value=value)
        elif mapping:
            redis_client.hset(name=name, mapping=mapping)
        else:
            raise Exception(
                "A prop/value pair or a mapping should be provided!")

        redis_client.expire(name=name, time=expire_time)

    def get_prev_timestamps(self, identifier):
        timestamps_redis = redis_client.hgetall(name=identifier)
        prev_timestamps: dict[int, int] = {}

        for key_bytes, val_bytes in timestamps_redis.items():
            key_str = key_bytes.decode(encoding="utf-8")
            key_int = int(key_str)

            val_str = val_bytes.decode(encoding="utf-8")
            val_int = int(val_str)
            prev_timestamps[key_int] = val_int

        return prev_timestamps

    def cal_cur_time_boundary(self, cur_time_in_second, latest_timestamp_in_second):
        diff_second = cur_time_in_second - latest_timestamp_in_second
        mod = diff_second % self.lower_time_span_in_second
        cur_time_boundary = cur_time_in_second - mod

        return cur_time_boundary
