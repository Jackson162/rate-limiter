import asyncio


class Serialization:
    task_queues = {}

    @classmethod
    def put_queue_by_tag(cls, tag, func):
        async def wrapper(**kwargs):
            task_queues = cls.task_queues
            if tag not in task_queues:
                task_queues[tag] = asyncio.Queue()
            else:
                task = {}
                future = asyncio.Future()
                task.unlock = future.set_result

                await future

            result = await func(kwargs=kwargs)

            if task_queues[tag].qsize() > 0:
                next_task = await task_queues[tag].get()
                next_task.unlock()
            else:
                del task_queues[tag]

            return result

        return wrapper
