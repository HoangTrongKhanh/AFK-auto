#!/usr/bin/env python3
"""Nhập SO=1|0|? # TÊN vào đúng báo cáo đã kiểm tra, giữ bằng chứng tự đọc."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import cv2
import doc_tuong_cua_toi as D


def doc_nhan(text):
    labels = {}
    for line in text.splitlines():
        body, _, name = line.partition('#')
        if not body.strip():
            continue
        try:
            number, value = body.split('=', 1)
            number, value = int(number.strip()), value.strip()
        except ValueError as exc:
            raise ValueError(f'Dòng không đúng SO=1|0|?: {line}') from exc
        if number in labels:
            raise ValueError(f'Trùng số thẻ {number}')
        if value not in ('0', '1', '?'):
            raise ValueError(f'Giá trị khung không hợp lệ ở thẻ {number}')
        labels[number] = (None if value == '?' else int(value), name.strip())
    if not labels:
        raise ValueError('Không có xác nhận nào để nhập')
    return labels


def chuan_bi(rows, review, text, digest):
    if digest != review['sha256_json_goc']:
        raise ValueError('Báo cáo đã đổi; không thể áp số thẻ của bảng cũ')
    audit = review['chi_tiet']
    if len(rows) != len(audit):
        raise ValueError('Số thẻ không khớp bản kiểm tra')
    for n, (row, record) in enumerate(zip(rows, audit), 1):
        if (n, row['ten'], row['khung']) != (record['so_the'], record['ten'], record['sau']):
            raise ValueError(f'Số/tên/kết quả thẻ {n} đã đổi')
    labels = doc_nhan(text)
    allowed = {r['so_the'] for r in audit if r['can_xac_nhan']}
    if set(labels) - allowed:
        raise ValueError(f'Thẻ không thuộc bảng xác nhận: {sorted(set(labels)-allowed)}')
    timestamp = datetime.now(timezone.utc).isoformat()
    records = []
    for n, (value, name) in sorted(labels.items()):
        row = rows[n-1]
        if name and name != row['ten']:
            raise ValueError(f'Tên thẻ {n} không khớp: {name} / {row["ten"]}')
        records.append(dict(so_the=n, ten=row['ten'], khung=value,
                            tra_loi='?' if value is None else str(value),
                            nguon_nhan='nguoi_dung_xac_nhan_khung',
                            sha256_json_goc=digest, luc_nhap=timestamp))
    return records


def ghi_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as tmp:
        pending = Path(tmp.name)
        json.dump(value, tmp, ensure_ascii=False, indent=2)
        tmp.write('\n');tmp.flush();os.fsync(tmp.fileno())
    try:
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def nhap_khung(bao_cao, danh_gia, text, ra, khung_tay=None):
    bao_cao, ra = Path(bao_cao).resolve(), Path(ra).resolve()
    if ra == bao_cao:
        raise ValueError('Xuất vào thư mục mới để giữ báo cáo máy làm tham chiếu')
    raw = (bao_cao/'tuong_cua_toi.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    rows = json.loads(raw)
    review = json.loads(Path(danh_gia).read_text())
    records = chuan_bi(rows, review, text, digest)
    ledger_path = ra/'khung_da_xac_nhan.json'
    previous = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    if any(x['sha256_json_goc'] != digest for x in previous):
        raise ValueError('Thư mục kết quả đang chứa nhãn của phiên khác')
    combined = {x['so_the']: x for x in previous}
    for record in records:
        combined[record['so_the']] = record
    # Đọc/kiểm tra toàn bộ ảnh trước khi ghi báo cáo hay lựa chọn tay.
    prepared = []
    for n, row in enumerate(rows, 1):
        image_path = (bao_cao/row['anh']).resolve()
        image_path.relative_to(bao_cao)
        image = cv2.imread(str(image_path))
        face_path = (bao_cao/row['mat']).resolve() if row.get('mat') else None
        if face_path:
            face_path.relative_to(bao_cao)
        face = cv2.imread(str(face_path)) if face_path else D.mat(image) if image is not None else None
        if image is None or image.shape != (205, 130, 3) or face is None:
            raise ValueError(f'Ảnh thẻ/mặt {n} thiếu hoặc sai kích thước')
        updated = dict(row, the=image, mat=face)
        if n in combined:
            record = dict(combined[n], anh_goc=row['anh'],
                          sha256_anh=hashlib.sha256(image_path.read_bytes()).hexdigest())
            combined[n] = record
            updated.update(khung=record['khung'], khung_tu_doc=row['khung'], khung_nguoi_dung=record)
        prepared.append(updated)
    manual = None
    if khung_tay is not None:
        khung_tay = Path(khung_tay)
        manual = json.loads(khung_tay.read_text()) if khung_tay.exists() else {}
        for record in combined.values():
            if record['khung'] is None:
                manual.pop(record['ten'], None)  # '?' không phải không khung hoặc chưa sở hữu.
            else:
                manual[record['ten']] = record['khung']
    ra.mkdir(parents=True, exist_ok=True)
    with patch.multiple(D, THU_MUC=ra, ANH=ra/'tuong_cua_toi', KET_QUA=ra/'tuong_cua_toi.json'):
        D.xuat(prepared, D.ThuVien())
    ghi_json(ledger_path, [combined[n] for n in sorted(combined)])
    (ra/'tra_loi_nguoi_dung.txt').write_text(text)
    summary = dict(so_the=len(rows), so_tra_loi=len(combined),
                   nhan_da_xac_nhan=sum(x['khung'] is not None for x in combined.values()),
                   nhan_tu_doc=len(rows)-len(combined),
                   sau=dict(Counter(str(x['khung']) for x in prepared)),
                   sha256_json_nguon=digest)
    ghi_json(ra/'tong_ket.json', summary)
    if manual is not None:
        ghi_json(khung_tay, manual)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bao-cao', type=Path, required=True)
    p.add_argument('--danh-gia', type=Path, required=True)
    p.add_argument('--nhan', type=Path, required=True)
    p.add_argument('--ra', type=Path, required=True)
    p.add_argument('--khung-tay', type=Path, help='Lưu nhãn người dùng vào lựa chọn tay Python')
    a = p.parse_args()
    print(json.dumps(nhap_khung(a.bao_cao, a.danh_gia, a.nhan.read_text(), a.ra, a.khung_tay), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
