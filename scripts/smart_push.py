#!/usr/bin/env python3
"""求职 Skill 工具箱 · 主动推进扫描：读状态文件里的到期项，生成结构化提醒。

用法：
  python3 scripts/smart_push.py                     # 扫描默认状态文件 .qiuzhi/state.json
  python3 scripts/smart_push.py --state <path>      # 指定状态文件
  python3 scripts/smart_push.py --dry-run           # 只输出，不写扫描记录

状态文件示例：skills/qiuzhi-dispatch/assets/state.example.json（复制后按自己的线索填写）。

输出：
  - 有到期项 → JSON：每条提醒含线索 id / 公司 / 该做什么 / 截止日 / 逾期天数 / 是否需要本人决定
  - 无到期项 → {"status": "NO_ACTION_NEEDED"}

边界：
  - 脚本只读状态文件并追加一条扫描记录（--dry-run 时连记录也不写），不做任何其他事。
  - 涉及对外发送、薪资承诺、买票动身、offer 取舍的动作只做提醒标记（human_checkpoint=true），
    发送与决定始终由本人执行。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def parse_date(s):
    """解析 YYYY-MM-DD 格式日期"""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def scan_overdue(state_data, today):
    """扫描到期项：due <= today"""
    tracks = state_data.get("tracks", [])
    overdue = []
    for t in tracks:
        next_action = t.get("next", {})
        due_str = next_action.get("due")
        if not due_str:
            continue
        due_date = parse_date(due_str)
        if due_date and due_date <= today:
            overdue.append({
                "track_id": t.get("id"),
                "company": t.get("company"),
                "action": next_action.get("action"),
                "owner": next_action.get("owner"),
                "due": due_str,
                "days_overdue": (today - due_date).days
            })
    return overdue


def generate_reminder(item):
    """生成可执行提醒（结构化）"""
    action = item["action"] or ""
    # 人工检查点关键词：这些动作的产出会离开本人的账号，脚本只提醒、不代做
    human_checkpoint_keywords = ["对外", "发送", "买票", "动身", "offer", "薪资", "承诺", "启停"]
    is_human = any(k in action for k in human_checkpoint_keywords)

    return {
        "track_id": item["track_id"],
        "company": item["company"],
        "due": item["due"],
        "days_overdue": item["days_overdue"],
        "action": action,
        "owner": item["owner"],
        "human_checkpoint": is_human,
        "prompt_suggestion": f"【{item['company']}】{action}"
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=".qiuzhi/state.json")
    ap.add_argument("--dry-run", action="store_true", help="只输出，不写扫描记录")
    args = ap.parse_args()

    state_path = Path(args.state)
    if not state_path.is_file():
        print(f"ERROR: 状态文件不存在：{state_path}\n"
              f"      可先复制示例：cp skills/qiuzhi-dispatch/assets/state.example.json .qiuzhi/state.json",
              file=sys.stderr)
        return 1

    try:
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON 解析失败：{e}", file=sys.stderr)
        return 1

    today = datetime.now().date()
    overdue_items = scan_overdue(state_data, today)

    if not overdue_items:
        print(json.dumps({"status": "NO_ACTION_NEEDED", "scanned_at": str(today)}, ensure_ascii=False, indent=2))
        return 0

    # 按逾期天数倒序：最急的排最前
    overdue_items.sort(key=lambda x: x["days_overdue"], reverse=True)
    reminders = [generate_reminder(item) for item in overdue_items]
    output = {
        "status": "ACTION_NEEDED",
        "scanned_at": str(today),
        "count": len(reminders),
        "reminders": reminders
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))

    # 追加扫描记录（非 dry-run）
    if not args.dry_run:
        log_entry = {
            "date": str(today),
            "event": "smart_push_scan",
            "note": f"扫描到 {len(reminders)} 项到期：" + "、".join(str(r["track_id"]) for r in reminders)
        }
        state_data.setdefault("log", []).append(log_entry)
        state_data["updated_at"] = datetime.now().isoformat()
        state_path.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n✓ 已追加扫描记录：{log_entry['note']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
