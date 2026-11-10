#!/usr/bin/env python3
"""Thu phiên Hội Trường qua ADB, kiểm tra nối trang, rồi xuất báo cáo riêng khi đạt điều kiện."""
import argparse
import json
import time
from pathlib import Path
from adb import Adb, DEFAULT_ADB
from nhan_dien import NhanDien
from hoi_truong import chup_hoi_truong, kiem_tra_do_phu
import doc_tuong_cua_toi as D


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial')
    p.add_argument('--adb',default=DEFAULT_ADB)
    p.add_argument('--ra',type=Path,required=True)
    p.add_argument('--thu-vien-mat',type=Path)
    p.add_argument('--so-tuong-du-kien',type=int,help='Số tướng duy nhất đã đối chiếu trong danh sách hiện tại, kể cả nhóm cố định')
    a=p.parse_args()
    root=a.ra.resolve();root.mkdir(parents=True,exist_ok=True)
    if (root/'phien.json').exists():
        p.error('Thư mục đã có phiên kiểm tra; chọn thư mục mới để giữ bằng chứng cũ')
    result=dict(hoan_tat=False,nguon='ADB',bat_dau=time.time())
    try:
        adb=Adb(a.adb,a.serial)
        if not adb.connected():
            raise RuntimeError('Chưa có kết nối ADB')
        proof={}
        images=chup_hoi_truong(adb,NhanDien(),root,so_tuong_du_kien=a.so_tuong_du_kien,bang_chung_phien=proof)
        audit=kiem_tra_do_phu(images)
        (root/'do_phu.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
        if any(item['can_kiem_tra'] for item in audit['noi_trang']):
            raise RuntimeError('Có trang thiếu chồng lấp trong lưới; giữ ảnh để kiểm tra, chưa xác nhận thu đủ')
        library=D.ThuVien(a.thu_vien_mat)
        cards=D.doc(images,library,hoi_truong=True)
        if a.so_tuong_du_kien is not None and len(cards)!=a.so_tuong_du_kien:
            raise RuntimeError(f'Sau gộp có {len(cards)} thẻ, khác {a.so_tuong_du_kien} tướng nguồn; chưa xuất kết quả')
        D.THU_MUC=root;D.ANH=root/'tuong_cua_toi';D.KET_QUA=root/'tuong_cua_toi.json'
        D.xuat(cards,library)
        result.update(hoan_tat=True,so_anh=len(images),so_the=len(cards),
                      so_ten=sum(c['ten'] is not None for c in cards),
                      xac_minh_cuoi=proof,
                      thu_vien_mat=str(a.thu_vien_mat) if a.thu_vien_mat else None)
    except Exception as e:
        result['loi']=str(e)
        raise
    finally:
        result['giay']=time.time()-result['bat_dau']
        (root/'phien.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
