        import {request} from '../api.js';
        import {actionForm} from '../controls.js';
        import {el} from '../dom.js';
        import {dataView, status, titleBlock} from '../widgets.js';
        import {COMPUTE_STATES} from '../store.js';

        const page = {
  "title": "复访估计申请单 · 快照与恢复",
  "module": "复访估计申请",
  "caption": "估计申请单",
  "detail": "工作台收单即留住当时的实见样本。同号重试不新增估计单，房间或拟访日对不上退回；后台中断后按原样本续算，补登实见留给新单。",
  "path": "/fit_requests",
  "columns": [
    {"name": "fit_id", "label": "申请号"},
    {"name": "room_code", "label": "空房"},
    {"name": "target_day", "label": "拟复访日期"},
    {"name": "status", "label": "状态"},
    {"name": "prediction", "label": "估计实见活动数"},
    {"name": "holdout_mae", "label": "末段留出 MAE"},
    {"name": "skipped_refusals", "label": "跳过的拒入窗口数"},
    {"name": "token", "label": "后台评估凭证"},
    {"name": "detail", "label": "退回原因"}
  ],
  "layout": "stack",
  "view": "table",
  "actions": [
    {
      "name": "fit_return",
      "label": "凭申请号提交复访估计",
      "path": "/return_forecasts/fit-return",
      "fields": [
        {"name": "fit_id", "label": "申请号", "kind": "text", "initial": "FIT-17-QA"},
        {"name": "room_code", "label": "空房编号", "kind": "text", "initial": "ROOM-17"},
        {"name": "target_day", "label": "拟复访日期", "kind": "text", "initial": "2090-04-05"}
      ],
      "help": "收单即固化实见样本。排队未送出也可凭申请号查待算；同号重试不新增估计单，房间或拟访日对不上会退回。",
      "roles": ["operator", "reviewer"],
      "success": "已登记申请单"
    },
    {
      "name": "sign_return",
      "label": "按申请号签认估计",
      "path": "/return_forecasts/sign-return",
      "fields": [
        {"name": "code", "label": "签认凭证", "kind": "text", "initial": "FC-QA"},
        {"name": "fit_id", "label": "申请号", "kind": "text", "initial": "FIT-17-QA"}
      ],
      "help": "只认收单时留存的样本与已存估计。临时凭证过期仍能凭原号取估计值与留出误差；补登实见请另开新单。",
      "roles": ["reviewer"],
      "success": "估计已签认"
    }
  ]
};

        export const {title} = page;
        export const key = "fit_requests";

        export async function render(root, role) {
          const panel = el('section', {class:'ledger', 'aria-label':page.caption});
          const refresh = async () => {
            try {
              const rows = await request(page.path);
              const shown = rows.map(row => ({...row,
                status: COMPUTE_STATES[row.status] || row.status,
                prediction: row.result?.prediction ?? null,
                holdout_mae: row.result?.holdout_mae ?? null}));
              panel.replaceChildren(el('h2',{},page.caption),dataView(shown, page.columns,page.view));
            } catch (error) { panel.replaceChildren(status(error.message,'error')); }
          };
          const actions = page.actions.filter(x => x.roles.includes(role));
          root.replaceChildren(titleBlock(page.module, page.title, page.detail),
            el('div',{class:'work '+page.layout},panel,
              actions.length ? el('section',{class:'actions'},actions.map(x => actionForm(x, refresh))) : null));
          return refresh();
        }
