#!/usr/bin/env python3
"""Read-only CSV resume-version gate; Python 3 standard library only."""
import argparse
import csv
import json
import sys
from pathlib import Path

FIELDS = ['id', 'date', 'company', 'role', 'resume_version', 'version_verified',
          'greeting_version', 'status', 'stage', 'next_action', 'notes']
STATUSES = ('contacted', 'read_no_reply', 'replied', 'resume_sent', 'interview',
            'offer', 'closed')


def inspect_ledger(path, current_versions):
    groups = {name: {'ids': [], 'count': 0,
                     'status_counts': {status: 0 for status in (*STATUSES, 'unknown')}}
              for name in ('clean', 'contaminated', 'unknown')}
    seen = set()
    with Path(path).open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader, None)
        if header != FIELDS:
            raise ValueError('表头必须按顺序为：' + ','.join(FIELDS))
        for cells in reader:
            if len(cells) != len(FIELDS):
                raise ValueError(f'第 {reader.line_num} 行字段数应为 {len(FIELDS)}，实际为 {len(cells)}')
            row = dict(zip(FIELDS, cells))
            row_id = row['id']
            if not row_id.strip() or row_id != row_id.strip():
                raise ValueError(f'第 {reader.line_num} 行 id 必须非空且无首尾空格')
            if row_id in seen:
                raise ValueError(f'重复 id：{row_id}')
            seen.add(row_id)
            if row['status'] not in (*STATUSES, ''):
                raise ValueError(f'id {row_id} 的 status 无效：{row["status"]!r}')
            if row['version_verified'] not in ('true', 'false', ''):
                raise ValueError(f'id {row_id} 的 version_verified 只能为 true、false 或空')
            version = row['resume_version']
            if (not current_versions or row['version_verified'] != 'true'
                    or not version.strip()):
                group = 'unknown'
            elif version in current_versions:
                group = 'clean'
            else:
                group = 'contaminated'
            groups[group]['ids'].append(row_id)
            groups[group]['count'] += 1
            groups[group]['status_counts'][row['status'] or 'unknown'] += 1
    return {'current_versions': list(dict.fromkeys(current_versions)),
            'total_rows': len(seen), 'groups': groups,
            'insufficient_clean_samples': groups['clean']['count'] == 0,
            'notice': '状态计数不是漏斗转化率；未知不视为失败；各阶段分母须另核对。'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True, help='UTF-8 / UTF-8-SIG CSV path')
    parser.add_argument('--current-version', action='append', default=[],
                        help='Exact verified current version; repeat to allow several')
    parser.add_argument('--json', action='store_true', help='Emit JSON')
    args = parser.parse_args(argv)
    try:
        if any(not value.strip() for value in args.current_version):
            raise ValueError('--current-version 不得为空或全空格')
        result = inspect_ledger(args.ledger, args.current_version)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f'错误：{exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f'总记录：{result["total_rows"]}')
        for name, label in [('clean', '干净'), ('contaminated', '污染'), ('unknown', '未知')]:
            group = result['groups'][name]
            print(f'{label}：{group["count"]}；ID：{json.dumps(group["ids"], ensure_ascii=False)}')
            print('  状态计数：' + json.dumps(group['status_counts'], ensure_ascii=False))
        if result['insufficient_clean_samples']:
            print('干净样本不足：不能据此判断当前简历效果。')
        print(result['notice'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
