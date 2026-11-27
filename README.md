# 白蚁空房复查路由

松苔房屋养护队的空房观察与钥匙复约工作席。工作人员区分实见零与无法观察的窗口，估计再访时的活动记录，并核对房主权限和照片回执。

## 现场工作与联系人

模拟客户为松苔房屋养护队。房室活动观察、上次复查间隔、滞后回归、钥匙交接复约；房主拒入的空白窗口不能记零观测。

- 空房与授权簿 `vacant_rooms`，字段为 `building`（业主单位）、`room`（空房门牌）、`contact_ref`（归档联系人）、`key_tag`（钥匙牌）、`permit_ref`（书面授权）、`permit_until`（授权截止）、`status`（授权状态）。模型约束位于 `backend/domain/vacant_rooms_model.py`，规则位于 `vacant_rooms_service.py`。
- 观察窗口与拒入 `visit_windows`，字段为 `room_code`（空房）、`visit_day`（预约日期）、`activity_count`（实见活动数）、`status`（观察状态）、`photo_receipt`（照片回执）、`desk_note`（观察或拒入记录）。模型约束位于 `backend/domain/visit_windows_model.py`，规则位于 `visit_windows_service.py`。
- 复访估计申请单 `fit_requests`，字段为 `fit_id`（申请号）、`room_code`（空房）、`target_day`（拟复访日期）、`status`（待算/排队中/已计算/计算被拒绝）、`snapshot`（收单时固化的实见样本与拒入计数）、`result`（算成后固化的估计值与留出误差）、`skipped_refusals`（跳过的拒入窗口数）、`token`（后台评估凭证）、`detail`（退回原因）。工作台收单即留存当时的实见样本，排队未送出也能凭申请号查到待算；后台中断恢复后按原样本续算，补登的实见只进入新单。模型约束位于 `backend/domain/fit_requests_model.py`，规则位于 `return_forecasts_service.py`。
- 复访间隔簿 `return_forecasts`，字段为 `code`（签认编号）、`fit_id`（来源申请号）、`room_code`（空房）、`target_day`（拟复访日期）、`prediction`（估计实见活动数）、`lag_count`（最近一次实见值）、`gap_days`（距最近实见天数）、`holdout_mae`（末段留出 MAE）、`skipped_refusals`（跳过的拒入窗口数）、`token`（后台评估凭证）。估计由申请单签认生成，一个申请号至多签认一份。模型约束位于 `backend/domain/return_forecasts_model.py`，规则位于 `return_forecasts_service.py`。
- 再授权与钥匙交接 `key_handoffs`，字段为 `room_code`（空房）、`forecast`（复查签认）、`proof_visit`（照片来源观察）、`permit_snapshot`（本次书面授权快照）、`visit_date`（拟交接日期）、`key_tag`（钥匙交接牌）、`team_member`（带钥负责人）、`status`（交接状态）、`receipt`（钥匙回单）。模型约束位于 `backend/domain/key_handoffs_model.py`，规则位于 `key_handoffs_service.py`。

团队为模拟的8 人房屋养护班，安排空房复查及房东授权。

养护员用钥匙簿和图片群消息管理复查。拒入日期容易被写成无活动，旧授权继续被引用，钥匙借出与归还难核对。

房东许可和房室观察记录进入复约，下游领钥人使用最新授权快照并签归还。

### 一天的业务操作

1. 08:40 核对榉园东院 ROOM-17 与钥匙柜 KEY-017。
2. 09:10 为 2090-03-22 的零观察登记 PHOTO-QA-ZERO，确认进房许可。
3. 10:05 2090-03-24 的约窗被房主拒绝，记入 V-REFUSE-QA，空房权限挂起。
4. 11:00 凭申请号 FIT-17-QA 提交 2090-04-05 的复访估计，工作台收单即留存当时实见样本；后台算成后由负责人按申请号签认，继续保留三次拒入记录。同号重试不新增估计单，房间或拟访日对不上会退回。
5. 13:10 收到 AUTH-NEW-17 房主重新授权，复核拒入记录不能成为照片凭证。
6. 13:45 以 PHOTO-QA-ZERO 复约，房主授权变更后撤销旧复约，重新核对 KEY-017 后签出钥匙。
7. 16:00 柜台核对 KEYRET-017 并归还钥匙。

## 启动

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

打开 `http://127.0.0.1:18318`。FastAPI OpenAPI 在 `http://127.0.0.1:19318/docs`。
Compose 运行 Nginx、Python FastAPI、独立 Redis 消费进程、SQL 数据库和 Redis，SQL 与 Redis 使用命名卷。
本机开发时，在 Python 3.11 环境安装 `backend/requirements.txt` 后从 backend 目录运行 `uvicorn core.app:app`。须提供 `DATABASE_URL`、`REDIS_URL`、`JWT_SECRET`，`SEED_DEMO` 控制演示初始化。

| 演示账号 | 权限 |
|---|---|
| operator@demo.test | 提交领域记录和计算请求 |
| reviewer@demo.test | 提交记录并执行有业务约束的复核操作 |
| viewer@demo.test | 浏览业务台账 |

三个本地演示账号均使用 `DemoC0de!2026`。角色在 `backend/core/roles.py` 和 `frontend/src/store.js` 中声明。计算状态在 worker、queueing、API 和同一前端 store 中使用。

## 页面与接口

| 业务任务 | FastAPI 路由 | 页面 |
|---|---|---|
| 空房与授权簿 | `/vacant_rooms` /vacant_rooms/renew-permit | `frontend/src/pages/vacant_rooms.js` |
| 观察窗口与拒入 | `/visit_windows` /visit_windows/record-count，/visit_windows/register-refusal | `frontend/src/pages/visit_windows.js` |
| 复访估计申请单（样本快照、中断恢复、凭号查询） | `/fit_requests` /fit_requests/{fit_id}，/return_forecasts/fit-return，/return_forecasts/sign-return | `frontend/src/pages/fit_requests.js` |
| 复访间隔簿（签认后台账，只读） | `/return_forecasts` | `frontend/src/pages/return_forecasts.js` |
| 再授权与钥匙交接 | `/key_handoffs` /key_handoffs/book-revisit，/key_handoffs/release-key，/key_handoffs/return-key | `frontend/src/pages/key_handoffs.js` |

SQL 实体与约束在 `backend/domain` 下维护。前端使用原生 ES modules。核心算子为 对数线性滞后回归。在 log(1+实见值) 上对上次实见量和前次实际到访间隔进行线性回归。历史按日期切分，尾段留出，逆变换后报告 MAE。拒入窗口不上样，日期间隔跨过它，实见 0 保留。

### 申请号、快照与中断恢复

- 养护员凭申请号 `fit_id` 提交复访估计。工作台收单时把当时的实见样本与拒入计数固化进申请单 `snapshot`，任务即使还在排队未送出，也能凭申请号查到“待算”。
- 同一申请号重试不新增估计单；申请号已绑定其他空房或拟访日期时直接退回。
- 后台 worker 与队列在 `core/queueing.py`、`core/worker.py`。worker 中断后重启会把 `compute_requests:processing` 中卡住的任务搬回队列（`resume`），按申请单留存的原样本重新计算；收单之后补登的实见不会并入旧单，只进入此后新开的申请单。
- 算成的估计值与留出误差回写到申请单 `result` 并保留在复访间隔簿签认来源。估计存下后即使任务被重复投递，恢复时也认已存的那份，不覆盖。
- 申请单绑定的后台凭证 `compute:{token}` 不设过期；即便临时凭证被清理，仍能凭原申请号查到估计值与留出误差并完成签认。未绑定申请单的临时计算仍沿用 24 小时过期。

只使用模拟空房观察计数和书面授权代号。系统不读取照片本体，不接入门锁。训练预测不用于现场种群诊断或防治。拒入授权挂起后，若已发出的复约授权变化，签出会阻止。

[MIT](LICENSE)
