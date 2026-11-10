"""Xuất đáp án Python cố định; không thay đổi mô hình hay các bộ kiểm tra đã niêm phong."""
import sys,json,hashlib
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import doc_tuong_cua_toi as D
from cat_the_bo_sung import cat_day_du
from khung_can_python import dac_trung
from quan_ly_mau import sha,ghi_json
OUT=ROOT/'debug/vision-fixtures'

def run(output=None):
 tv=D.ThuVien();out=Path(output) if output else OUT/tv.phien_ban_mau
 if (out/'expected.json').exists():raise ValueError('Bảng đối chiếu phiên bản này đã cố định; chọn --output khác để không ghi đè')
 out.mkdir(parents=True,exist_ok=True);cards=[];pages=[];groups=[]
 for folder in ['kiem-chung-doc-lap-20261108','kiem-chung-v2-20261108']:
  base=ROOT/'debug'/folder;data=json.loads((base/'dataset.json').read_text())
  for item in data['items']:
   im=cv2.imread(str(base/item['image']));q=item['quality'];dg=tv.danh_gia_khung(im,q)
   cards.append(dict(image=str((base/item['image']).relative_to(ROOT)),sha256=sha((base/item['image']).read_bytes()),quality=q,result=dg,features=dac_trung(im,q).tolist()))
 sources=[('48',ROOT/'debug/danh-sach-ngan-dien-mao-20261109/phien48'),('6',ROOT/'debug/danh-sach-ngan-dien-mao-20261109/loc_thien_6'),('121',ROOT/'debug/kiem-chung-doc-lap-20261108/anh_goc'),('71',ROOT/'debug/kiem-chung-v2-20261108/anh_goc')]
 for name,folder in sources:
  paths=sorted(p for p in folder.glob('*.png') if p.stem.isdigit());imgs=[]
  for p in paths:
   img=cv2.imread(str(p));imgs.append(img);cs=cat_day_du(img,kem_chat_luong=True)
   pages.append(dict(image=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes()),cards=[dict(quality=c[2],result=tv.danh_gia_khung(c[0],c[2])) for c in cs]))
  ds=D.doc(imgs,tv,hoi_truong=True)
  groups.append(dict(name=name,pages=[str(p.relative_to(ROOT)) for p in paths],heroes=[dict(name=x['ten'],suggestion=x['goi_y'],frame=x['khung'],quality=x['chat_luong_cat'],name_reason=x['ten_chi_tiet']['ly_do']) for x in ds]));print(name,len(paths),len(ds),flush=True)
 manifest=json.loads((ROOT/'android/app/src/main/assets/vision-v2/manifest.json').read_text())
 if manifest['version']!=tv.phien_ban_mau:raise ValueError('Cần xuất cùng phiên bản mẫu Android trước khi tạo bảng đối chiếu')
 ghi_json(out/'expected.json',dict(schema=1,version=tv.phien_ban_mau,bundle_sha256=sha((ROOT/'android/app/src/main/assets/vision-v2/manifest.json').read_bytes()),opencv=cv2.__version__,cards=cards,pages=pages,groups=groups));print(len(cards),'cards',len(pages),'pages',out)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args();run(a.output)
