import logging

from utils import Serialization, RateLimiter

from fastapi import FastAPI, Request

app = FastAPI()


@app.get('/')
async def index(request: Request):
    ip_address = request.client.host
    request_is_accepted = False

    try:
        request_is_accepted = await Serialization.put_queue_by_tag(
            tag=ip_address,
            async_func=RateLimiter.activate
        )(identifier=ip_address)

    except Exception as e:

        logging.exception(e)
        request_is_accepted = False

    if request_is_accepted:
        response = f"To {ip_address}: This is a valid response!"
    else:
        response = f"To {ip_address}: Your request is rejected!"

    print(response)
    return response
