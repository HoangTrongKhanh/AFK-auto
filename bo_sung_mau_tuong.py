#!/usr/bin/env python3
"""Chọn mẫu đa dạng từ các nhóm đã đặt tên; không dùng tên do bộ đọc danh sách tự đoán."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import thong_ke_tuong as T


def chon_mau(ds, toi_da=6):
    """Giữ mẫu nét đầu tiên, rồi thêm mẫu khác nhất; loại gần trùng để giới hạn chi phí so ảnh."""
    if toi_da < 1:
        raise ValueError('Số mẫu mỗi nhóm phải >= 1')
    ds = sorted(ds, key=lambda x: x[0])
    if not ds:
        return []
    selected = [max(ds, key=lambda x: cv2.Laplacian(cv2.cvtColor(x[1], cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())]
    scores = {key: T.giong(face, selected[0][1]) for key, face in ds}
    for _ in range(toi_da - 1):
        candidates = [(scores[key], key, face) for key, face in ds if scores[key] < .985]
        if not candidates:
            break
        _, key, face = min(candidates, key=lambda x: (x[0], x[1]))
        selected.append((key, face))
        for k, m in ds:
            scores[k] = max(scores[k], T.giong(m, face))
    return selected


def tao_bo_sung(nguon, ra, toi_da=6, mat_da_xac_nhan=None):
    nguon, ra = Path(nguon), Path(ra)
    groups = json.loads((nguon/'nhom.json').read_text())
    names = json.loads((nguon/'ten_tuong.json').read_text())
    bygroup = defaultdict(list)
    with (nguon/'ban_ghi.csv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row['anh']:
                continue
            # Chỉ giải mã bản ghi có nhóm đã đặt tên, không đọc lại dữ liệu chưa có nhãn.
            keys = [f"{row['luot']}|{row['vi_tri']}|{i}" for i in range(5)]
            if not any(str(groups.get(key)) in names for key in keys):
                continue
            img = cv2.imread(str(nguon/row['anh']))
            if img is None:
                raise ValueError(f"Thiếu ảnh nguồn {row['anh']}")
            cards = T.tach_the(img)
            if cards is None:
                raise ValueError(f"Không tách được ảnh nguồn {row['anh']}")
            for key, (face, _) in zip(keys, cards):
                group = str(groups.get(key))
                if group in names:
                    bygroup[group].append((key, cv2.resize(face, (48, 48), interpolation=cv2.INTER_AREA)))
    faces, labels, keys, gids = [], [], [], []
    for group in sorted(bygroup, key=int):
        for key, face in chon_mau(bygroup[group], toi_da):
            faces.append(face); labels.append(names[group]); keys.append(key); gids.append(group)
    confirmed = Path(mat_da_xac_nhan) if mat_da_xac_nhan is not None else nguon/'mat_xac_nhan'
    if (confirmed/'nhan.json').exists():
        index = json.loads((confirmed/'nhan.json').read_text())
        files = [(name, confirmed/o['mat']) for name, o in index.items()]
    else:
        files = [(f.stem.split('~')[0], f) for f in sorted(confirmed.glob('*.png'))]
    for name, f in files:
        face = cv2.imread(str(f))
        if face is None or face.shape != (48,48,3):
            raise ValueError(f'Mẫu đã xác nhận không đúng khổ 48x48: {f}')
        faces.append(face); labels.append(name); keys.append(f'xac_nhan|{f.resolve()}'); gids.append('xac_nhan')
    if not faces:
        raise ValueError('Không có nhóm đã đặt tên để bổ sung')
    ra.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ra, mat=np.stack(faces), ten=np.array(labels), khoa=np.array(keys), nhom=np.array(gids))
    info = dict(so_mat=len(faces), so_ten=len(set(labels)), so_nhom=len(bygroup), so_mat_da_xac_nhan=len(files),
                nguon=str(nguon.resolve()), luu_y='Tên nhóm do người gán; thành viên nhóm do bộ gom ảnh xác định, cần kiểm chứng độc lập.')
    ra.with_suffix('.json').write_text(json.dumps(info, ensure_ascii=False, indent=2))
    return info


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nguon', type=Path, default=Path(__file__).parent/'thu_thap_tuong')
    p.add_argument('--ra', type=Path, required=True)
    p.add_argument('--moi-nhom', type=int, default=6)
    p.add_argument('--mat-da-xac-nhan', type=Path, help='Thư mục mặt 48x48 đã xác nhận, có thể kèm nhan.json')
    a = p.parse_args()
    print(json.dumps(tao_bo_sung(a.nguon, a.ra, a.moi_nhom, a.mat_da_xac_nhan), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
