from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


fit_requests = Table('fit_requests', metadata,
    Column('fit_id', String(64), primary_key=True),
    Column('room_code', String(160), ForeignKey('vacant_rooms.code'), nullable=False),
    Column('target_day', String(160), nullable=False),
    Column('status', String(160), nullable=False),
    # 工作台收单时固化的实见样本与拒入计数，后台中断恢复后仍按这份样本计算
    Column('snapshot', JSON, nullable=False),
    # 算成后固化的估计值与留出误差；临时凭证过期后仍凭申请号查得到
    Column('result', JSON, nullable=True),
    Column('skipped_refusals', Integer, nullable=False),
    Column('submitted_by', String(160), nullable=False),
    Column('token', String(64), nullable=True, unique=True),
    Column('detail', String(160), nullable=True),
    CheckConstraint("status IN ('待算','排队中','已计算','计算被拒绝')"),
    CheckConstraint('skipped_refusals >= 0'),
)
