"""Học mẫu khung căn từ tập phát triển đã chia theo ID tướng, giữ tập kiểm tra riêng."""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from hoi_truong import cat_the_hoi_truong
from khung_can_python import dac_trung, hoc


def huan_luyen(bao_cao, nhan, anh_goc, chia_tap, ra):
    raw=(bao_cao/'tuong_cua_toi.json').read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    rows=json.loads(raw);labels=json.loads(nhan.read_text());split=json.loads(chia_tap.read_text())
    train=set(split['huan_luyen']);test=set(split['kiem_tra_giu_lai'])
    if train&test:raise ValueError('Tướng tập học và tập kiểm tra bị trùng')
    records={r['so_the']:r for r in labels}
    if len(records)!=len(labels) or train|test!=set(records):raise ValueError('Chia tập không khớp các nhãn')
    if any(r['sha256_json_goc']!=digest for r in labels):raise ValueError('Nhãn không thuộc báo cáo nguồn')
    cache={};samples=[];source=[]
    for n in sorted(train):
        record=records[n];row=rows[n-1]
        if record['ten']!=row['ten'] or record['khung'] not in (0,1):raise ValueError('Sai tên hoặc nhãn chưa rõ')
        obs=row['khung_chi_tiet'][0];page=obs['anh']
        if page not in cache:
            cache[page]=cat_the_hoi_truong(cv2.imread(str(anh_goc/page)),kem_chat_luong=True)
        card,y,q,_=cache[page][obs['vi_tri']-1]
        if not q['day_du']:raise ValueError(f'Thẻ {n} chưa có ảnh đủ biên để học')
        samples.append((n,record['khung'],card,q))
        source.append(dict(so_the=n,anh=page,vi_tri=obs['vi_tri'],sha256_anh=hashlib.sha256((anh_goc/page).read_bytes()).hexdigest()))
    features=np.array([dac_trung(c,q) for n,k,c,q in samples]);ys=np.array([k for n,k,c,q in samples]);ids=np.array([n for n,k,c,q in samples])
    loo=[]
    for i,(n,k,c,q) in enumerate(samples):
        mask=np.arange(len(samples))!=i
        result=hoc(features[mask],ys[mask],ids[mask]).du_doan(c,q)
        loo.append(dict(so_the=n,nhan=k,**result))
    model=hoc(features,ys,ids);model.luu(ra)
    report=dict(so_tuong_hoc=len(train),so_tuong_giu_lai=len(test),
                train_loo=dict(dung=sum(r['khung']==r['nhan'] for r in loo),sai=sum(r['khung'] is not None and r['khung']!=r['nhan'] for r in loo),chua_ro=sum(r['khung'] is None for r in loo)),
                sha256_json_nguon=digest,sha256_mo_hinh=hashlib.sha256(ra.read_bytes()).hexdigest(),
                nguon_hoc=source,loo=loo,gioi_han='Tập phát triển cùng phiên; không phải độ chính xác trên ảnh mới.')
    ra.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['bao-cao','nhan','anh-goc','chia-tap','ra']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=huan_luyen(a.bao_cao,a.nhan,a.anh_goc,a.chia_tap,a.ra)
    print(json.dumps({k:v for k,v in r.items() if k not in ['nguon_hoc','loo']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
