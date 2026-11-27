import json
from uuid import uuid4

from fastapi import HTTPException
from redis import Redis

from core.config import REDIS_URL

broker = Redis.from_url(REDIS_URL, decode_responses=True)
QUEUE = 'compute_requests'
PROCESSING = f'{QUEUE}:processing'

def submit(user, payload, fit_id=None, on_ready=None):
    """登记一个后台计算任务。

    fit_id 给出申请号时，任务与申请单绑定，结果与异常通过 on_ready 回写到 SQL，
    临时凭证 compute:{token} 不再设置过期，保证凭证失效后仍能凭申请号查回估计值。
    未给出 fit_id 时保留原有 24 小时临时凭证语义。
    """
    token = uuid4().hex
    record = {'owner': user['sub'], 'status': 'queued'}
    if fit_id is not None:
        record['fit_id'] = fit_id
    item = {'token': token, 'owner': user['sub'], 'input': payload}
    if fit_id is not None:
        item['fit_id'] = fit_id
    if on_ready is not None:
        item['on_ready'] = on_ready
    with broker.pipeline() as pipe:
        # 申请单任务持久保留；旧的临时计算仍按 24 小时过期
        pipe.set(f'compute:{token}', json.dumps(record), ex=None if fit_id else 86400)
        pipe.rpush(QUEUE, json.dumps(item))
        pipe.execute()
    return {'token': token, 'status': 'queued'}

def view(user, token):
    raw = broker.get(f'compute:{token}')
    if raw is None:
        raise HTTPException(404, detail='计算任务不存在或已过期')
    record = json.loads(raw)
    if record['owner'] != user['sub'] and user['role'] != 'reviewer':
        raise HTTPException(403, detail='仅提交人和复核员可查看计算')
    return {k: v for k, v in record.items() if k != 'owner'}

def result(user, token):
    data = view(user, token)
    if data['status'] != 'ready':
        raise HTTPException(409, detail='等待计算完成后再提交')
    return data

def resume():
    """后台中断恢复：把卡在 processing 列表的任务搬回队列，按原样本重新投递。"""
    recovered = 0
    for raw in broker.lrange(PROCESSING, 0, -1):
        with broker.pipeline() as pipe:
            pipe.lpush(QUEUE, raw)
            pipe.lrem(PROCESSING, 1, raw)
            pipe.execute()
        recovered += 1
    return recovered
