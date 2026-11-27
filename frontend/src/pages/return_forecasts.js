        import {workspace} from '../workspace.js';

        const page = {
  "title": "时间留出与复查间隔",
  "module": "复访间隔簿",
  "caption": "复访间隔簿",
  "detail": "已签认的复查估计台账。估计提交、样本快照与中断恢复在“复访估计申请单”页按申请号办理。",
  "path": "/return_forecasts",
  "columns": [
    {"name": "code", "label": "编号"},
    {"name": "fit_id", "label": "来源申请号"},
    {"name": "room_code", "label": "空房"},
    {"name": "target_day", "label": "拟复访日期"},
    {"name": "prediction", "label": "估计实见活动数"},
    {"name": "lag_count", "label": "最近一次实见值"},
    {"name": "gap_days", "label": "距最近实见天数"},
    {"name": "holdout_mae", "label": "末段留出 MAE"},
    {"name": "skipped_refusals", "label": "跳过的拒入窗口数"},
    {"name": "token", "label": "后台评估凭证"}
  ],
  "layout": "split",
  "view": "grid",
  "actions": []
};

        export const {title} = page;
        export const key = "return_forecasts";
        export async function render(root, role) {
          await workspace(root, role, page);

        }
