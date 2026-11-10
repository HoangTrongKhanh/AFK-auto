"""Xuất thẻ chưa rõ tên và giữ nguyên đáp án cũ để kiểm tra sau bổ sung mẫu."""
import argparse
import html
import json
from pathlib import Path

import cv2
import numpy as np

import doc_tuong_cua_toi as D
from cat_the_bo_sung import cat_day_du
from quan_ly_mau import ghi_json, pixel_sha, sha


def export(session, output):
    session, output = Path(session), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    evidence = json.loads((session / 'session.json').read_text())
    tv = D.ThuVien()
    if evidence['version'] != tv.phien_ban_mau:
        raise ValueError('Xuất bảng bằng đúng bản mẫu của phiên trước')
    paths = [session / name for name in evidence['pages']]
    images = [cv2.imread(str(p)) for p in paths]
    heroes = D.doc(images, tv, hoi_truong=True)
    native = json.loads((session / 'result.json').read_text())
    assert len(heroes) == len(native) == evidence['count']
    assert all(x['ten'] == y.get('ten') and x['khung'] == y['khung'] for x, y in zip(heroes, native))
    provenance = {}
    for path, image in zip(paths, images):
        for j, card in enumerate(cat_day_du(image, kem_chat_luong=True), 1):
            provenance[(pixel_sha(D.mat(card[3])), pixel_sha(card[0]))] = dict(
                source_image=str(path.resolve()), source_sha256=sha(path.read_bytes()), source_position=j,
                quality=card[2])
    records, articles = [], []
    for i, hero in enumerate(heroes, 1):
        stem = f'{i:03d}'
        assert cv2.imwrite(str(output / f'{stem}_the.png'), hero['the'])
        assert cv2.imwrite(str(output / f'{stem}_mat.png'), hero['mat'])
        source = provenance[(pixel_sha(hero['mat']), pixel_sha(hero['the']))]
        record = dict(id=i, ten=hero['ten'], goi_y=hero['goi_y'], khung=hero['khung'],
                      reason=hero['ten_chi_tiet']['ly_do'], scores=hero['ds_diem'][:3],
                      face=f'{stem}_mat.png', card=f'{stem}_the.png', **source)
        records.append(record)
        if hero['ten'] is None:
            top = ''.join(f'<li>{html.escape(t)}: {s:.4f}</li>' for s, t in record['scores'])
            articles.append(f'<article><h2>Thẻ {len(articles)+1} · nhóm #{i}</h2>'
                            f'<img src="{stem}_the.png" width="195" height="307">'
                            f'<p>{html.escape(record["reason"])}</p><ul>{top}</ul>'
                            f'<p>Nguồn: {html.escape(Path(source["source_image"]).name)}, '
                            f'vị trí {source["source_position"]}</p></article>')
    baseline = dict(version=tv.phien_ban_mau, source_session=str(session.resolve()),
                    source_files={str(p.resolve()):sha(p.read_bytes()) for p in paths},
                    count=len(heroes), known=sum(x['ten'] is not None for x in heroes),
                    unknown=[x['id'] for x in records if x['ten'] is None], records=records)
    ghi_json(output / 'baseline.json', baseline)
    np.savez_compressed(output / 'baseline.npz', mat=np.array([x['mat'] for x in heroes]),
                        the=np.array([x['the'] for x in heroes]))
    (output / f'{len(articles)}_the_chua_ro.html').write_text('''<!doctype html><html lang="vi"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Thẻ chưa rõ tên</title>
<style>body{font:17px/1.5 system-ui;background:#edf2f6;color:#193041;margin:24px}main{max-width:1100px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:18px}article{background:white;border-radius:12px;padding:18px}img{object-fit:contain}h2{font-size:22px}</style>
<main><h1>Thẻ cần xác nhận tên</h1><p>Ảnh đã căn đủ biên. Các tên bên dưới chỉ là ứng viên để đối chiếu; chưa được dùng làm nhãn học.</p><div class="grid">'''
        + ''.join(articles) + '</div></main></html>', encoding='utf-8')
    print(json.dumps({k:baseline[k] for k in ('version','count','known','unknown')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phien', type=Path, required=True)
    p.add_argument('--ra', type=Path, required=True)
    a = p.parse_args()
    export(a.phien, a.ra)
