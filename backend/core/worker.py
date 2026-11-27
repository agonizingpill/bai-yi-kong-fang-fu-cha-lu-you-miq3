import json
from pathlib import Path
from traceback import print_exc

from core import callbacks
from core.db import transaction
from core.queueing import PROCESSING, QUEUE, broker, resume
from domain.learning import calculate

pulse = Path('/tmp/compute-heartbeat')


def _persist(job, status):
    name = job.get('on_ready')
    fit_id = job.get('fit_id')
    callback = callbacks.get(name) if name else None
    if callback is None or fit_id is None:
        return
    with transaction() as conn:
        callback(conn, fit_id, status)


def serve():
    while True:
        broker.ping()
        pulse.touch()
        item = broker.blmove(QUEUE, PROCESSING, timeout=2, src='LEFT', dest='RIGHT')
        if item is None:
            continue
        job = json.loads(item)
        status = {'owner': job['owner'], 'input': job['input']}
        if job.get('fit_id'):
            status['fit_id'] = job['fit_id']
        try:
            status.update(status='ready', result=calculate(job['input']))
        except ValueError as exc:
            status.update(status='rejected', detail=str(exc))
        except Exception:
            print_exc()
            status.update(status='rejected', detail='计算失败，请检查输入和 worker 日志')
        try:
            _persist(job, status)
        except Exception:
            print_exc()
            # 回写失败则把任务放回队列待恢复，避免丢失原样本
            with broker.pipeline() as pipe:
                pipe.lpush(QUEUE, item)
                pipe.lrem(PROCESSING, 1, item)
                pipe.execute()
            continue
        with broker.pipeline() as pipe:
            # 申请单任务持久保留（不设 TTL）；其余临时凭证沿用 24 小时
            pipe.set(f'compute:{job["token"]}', json.dumps(status, allow_nan=False),
                     ex=None if job.get('fit_id') else 86400)
            pipe.lrem(PROCESSING, 1, item)
            pipe.execute()
        pulse.touch()

if __name__ == '__main__':
    # 显式导入领域服务，登记计算完成回写回调
    from domain import return_forecasts_service  # noqa: F401
    print(f'recovered {resume()} interrupted compute jobs')
    serve()
