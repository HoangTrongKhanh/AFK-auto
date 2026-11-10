#!/usr/bin/env python3
"""Nhập tên người dùng vào đúng snapshot thẻ, chỉ bổ sung mẫu mặt; không học khung."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unicodedata
import cv2
from doc_tuong_cua_toi import MAT_XAC_NHAN, mat


def doc_ten(text):
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        try:
            so, name = line.split('=', 1)
            so = int(so)
        except ValueError as e:
            raise ValueError(f'Dòng không đúng SO=TEN: {line}') from e
        if so in out:
            raise ValueError(f'Trùng số thẻ {so}')
        name = unicodedata.normalize('NFC', ' '.join(name.split()))
        if not name or name == '?':
            out[so] = None
            continue
        if any(c in name for c in '/\\~\x00') or name in ('.', '..'):
            raise ValueError(f'Tên không hợp lệ ở thẻ {so}')
        out[so] = name
    return out


def nhap_ten(thu_muc, text, ra=MAT_XAC_NHAN):
    folder, ra = Path(thu_muc), Path(ra)
    manifest = json.loads((folder/'danh_sach.json').read_text())
    snapshot = (folder/'snapshot.json').read_bytes()
    phien = hashlib.sha256(snapshot).hexdigest()[:16]
    if phien != manifest['phien']:
        raise ValueError('Snapshot đã đổi; không thể đối chiếu số thẻ')
    rows = {x['so_the']: x for x in manifest['can_bo_sung']}
    labels = doc_ten(text)
    extra = set(labels) - rows.keys()
    if extra:
        raise ValueError(f'Số thẻ không thuộc danh sách cần xác nhận: {sorted(extra)}')
    planned = []
    # Kiểm tra mọi ảnh/tên trước khi ghi bất kỳ mẫu nào.
    for so, name in labels.items():
        if name is None:
            continue
        image_path = (folder/rows[so]['anh']).resolve()
        image_path.relative_to(folder.resolve())
        image = cv2.imread(str(image_path))
        if image is None or image.shape != (205,130,3):
            raise ValueError(f'Ảnh thẻ {so} thiếu hoặc sai kích thước')
        ok, encoded = cv2.imencode('.png', mat(image))
        if not ok:
            raise OSError(f'Không mã hóa được mẫu mặt thẻ {so}')
        filename = f'{name}~{phien}_{so:03d}.png'
        planned.append((so, filename, encoded.tobytes(), dict(so_the=so, ten=name, phien=phien,
                       anh=rows[so]['anh'], sha256_anh=hashlib.sha256(image_path.read_bytes()).hexdigest(),
                       mau_mat=filename, nguon_nhan='nguoi_dung_xac_nhan_ten')))
    ra.mkdir(parents=True, exist_ok=True)
    report_path = folder/'ten_da_xac_nhan.json'
    previous = json.loads(report_path.read_text()) if report_path.exists() else []
    records = {x['so_the']: x for x in previous}
    with tempfile.TemporaryDirectory(prefix='.nhap-ten-', dir=ra) as tmp:
        for so, filename, data, record in planned:
            (Path(tmp)/filename).write_bytes(data)
        for so, filename, data, record in planned:
            os.replace(Path(tmp)/filename, ra/filename)
            # Sửa tên cùng một thẻ không để mẫu cũ mang nhãn khác cùng tồn tại.
            for old in ra.glob(f'*~{phien}_{so:03d}.png'):
                if old.name != filename:
                    old.unlink()
            records[so] = record
    report_path.write_text(json.dumps(list(sorted(records.values(),key=lambda x:x['so_the'])),ensure_ascii=False,indent=2))
    staged=[]
    if ra.resolve()==Path(MAT_XAC_NHAN).resolve():
        from quan_ly_mau import KhoMau
        repo=KhoMau()
        if repo.hien_tai():
            for so,filename,data,record in planned:
                sid=repo.them(cv2.imread(str(ra/filename)),'face',record['ten'],dict(session=phien,
                    label_source='user_confirmed',source_sha256=record['sha256_anh'],
                    label_evidence_sha256=hashlib.sha256(snapshot).hexdigest(),hero_id=so,group='face:'+record['ten']))
                staged.append(sid)
    return dict(phien=phien,da_nhap=len(planned),cho_duyet_kho_mau=staged,con_thieu=sorted(set(rows)-records.keys()),
                so_ten_khac_nhau=len({r['ten'] for r in records.values()}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--danh-sach',type=Path,required=True)
    p.add_argument('--ten',type=Path,required=True)
    p.add_argument('--ra',type=Path,default=MAT_XAC_NHAN)
    a=p.parse_args()
    print(json.dumps(nhap_ten(a.danh_sach,a.ten.read_text(),a.ra),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
