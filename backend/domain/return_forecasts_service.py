from sqlalchemy import select

from core.callbacks import on_ready
from core.queueing import submit
from core.records import get, insert, need, scan, update
from domain.fit_requests_model import fit_requests
from domain.vacant_rooms_model import vacant_rooms
from domain.visit_windows_model import visit_windows
from domain.return_forecasts_model import return_forecasts

# 申请状态到原计算凭证状态的映射，前端沿用同一套状态词
_STATUS = {'排队中': 'queued', '待算': 'queued', '已计算': 'ready', '计算被拒绝': 'rejected'}


def _gather(conn, room_code, day):
    """收单时采集当时的实见样本与拒入窗口，形成不可变快照。"""
    windows = [row for row in scan(conn, visit_windows)
               if row['room_code'] == room_code and row['visit_day'] < day]
    observations = [row for row in windows if row['status'] == '已观测']
    need(len(observations) >= 12, '同房间前序实见少于 12 次，复查估计尚不可用')
    return observations, len(windows) - len(observations)


def _public(row):
    """申请单对外视图：排队未送出也能查到待算，ready 时带估计值与留出误差。"""
    data = {k: row[k] for k in row if k != 'snapshot'}
    data['status'] = _STATUS.get(row['status'], row['status'])
    return data


def list_fits(conn):
    return [_public(row) for row in scan(conn, fit_requests)]


def get_fit(conn, fit_id):
    return _public(get(conn, fit_requests, fit_id))


def fit_return(conn, user, data):
    """养护员凭申请号提交复访估计；同号重试不新增估计单。"""
    from domain.visit_rules import calendar_day
    day = calendar_day(data.target_day)
    room = get(conn, vacant_rooms, data.room_code)
    existing = conn.execute(
        select(fit_requests).where(fit_requests.c.fit_id == data.fit_id)).mappings().first()
    if existing is not None:
        # 拿原号重试：房间或拟访日对不上就退回，一致则原样返回，不新增估计单
        need(existing['room_code'] == room['code'] and existing['target_day'] == day,
             '申请号已用于其他空房或拟访日期，请更换申请号')
        return _public(dict(existing))

    observations, skipped = _gather(conn, room['code'], day)
    # 工作台收单即留住当时的实见样本；排队没送出去也能查到待算
    snapshot = {'observations': observations, 'skipped_refusals': skipped}
    insert(conn, fit_requests, fit_id=data.fit_id, room_code=room['code'], target_day=day,
           status='排队中', snapshot=snapshot, result=None, skipped_refusals=skipped,
           submitted_by=user['sub'], token=None, detail=None)
    payload = {'fit_id': data.fit_id, 'room_code': room['code'], 'target_day': day,
               'observations': observations, 'skipped_refusals': skipped}
    queued = submit(user, payload, fit_id=data.fit_id, on_ready='return_forecasts.fit_ready')
    update(conn, fit_requests, data.fit_id, token=queued['token'])
    return _public(get(conn, fit_requests, data.fit_id))


@on_ready('return_forecasts.fit_ready')
def fit_ready(conn, fit_id, status):
    """后台中断恢复后按原样本算出结果，回写申请单；补登的实见留给新单。"""
    row = get(conn, fit_requests, fit_id, lock=True)
    if row['status'] == '已计算':
        # 估计存下后若还没报完工，恢复时认已存的那份，不重复覆盖
        return
    if status['status'] == 'ready':
        # 估计值与留出误差固化进申请单，临时凭证过期后仍凭原号查得到
        update(conn, fit_requests, fit_id, status='已计算', result=status['result'],
               detail=None, token=row['token'] or status.get('token'))
    else:
        update(conn, fit_requests, fit_id, status='计算被拒绝',
               detail=status.get('detail', '计算被拒绝'))


def sign_return(conn, user, data):
    """复核员签认：认申请单里按原样本存下的估计，房间或拟访日对不上在提交时已退回。"""
    fit = get(conn, fit_requests, data.fit_id, lock=True)
    need(fit['status'] == '已计算', '该申请单尚无可签认的估计值')
    duplicated = conn.execute(
        select(return_forecasts.c.code).where(return_forecasts.c.fit_id == data.fit_id)).first()
    need(duplicated is None, '该申请号的估计已签认，不能重复报完工')
    room = get(conn, vacant_rooms, fit['room_code'], lock=True)

    # 临时凭证可能已过期：估计值与留出误差已固化在申请单里，凭原号即可取，不依赖 Redis 凭证
    metrics = fit['result']
    need(metrics is not None, '后台估计结果缺失，请凭原申请号重新提交计算')

    snapshot = fit['snapshot']
    observations = snapshot['observations']
    # 补登的实见留给新单：签认只认收单快照，不把后补观察并入本单
    need(snapshot['skipped_refusals'] == fit['skipped_refusals'], '申请单快照与拒入计数不一致')
    newest = max(observations, key=lambda r: (r['visit_day'], r['code']))
    from domain.learning import gap
    need(metrics['lag_count'] == newest['activity_count']
         and metrics['gap_days'] == gap(fit['target_day'], newest['visit_day'])
         and metrics['skipped_refusals'] == fit['skipped_refusals'],
         '估计值与留存样本对不上，请凭原申请号重新提交计算')

    return insert(conn, return_forecasts, code=data.code, fit_id=fit['fit_id'],
                  room_code=room['code'], target_day=fit['target_day'], token=fit['token'],
                  **{k: metrics[k] for k in
                     ('prediction', 'lag_count', 'gap_days', 'holdout_mae', 'skipped_refusals')})
