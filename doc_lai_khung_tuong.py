#!/usr/bin/env python3
import sys,json,cv2,time
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import doc_tuong_cua_toi as D
import thong_ke_tuong as T
from hoi_truong import cat_the_hoi_truong
import argparse
parser=argparse.ArgumentParser(description='Căn lại biên và đọc khung từ ảnh gốc, giữ số thẻ/tên theo báo cáo tham chiếu.')
parser.add_argument('--anh-goc',type=Path,required=True)
parser.add_argument('--tham-chieu',type=Path,required=True,help='Thư mục chứa tuong_cua_toi.json đã được đặt tên')
parser.add_argument('--ra',type=Path,required=True)
parser.add_argument('--thu-vien-mat',type=Path)
args=parser.parse_args()
base=Path(__file__).resolve().parent;source=args.anh_goc.resolve()
oldroot=args.tham_chieu.resolve();old=json.loads((oldroot/'tuong_cua_toi.json').read_text())
refs=[cv2.imread(str(oldroot/x['mat'])) if x.get('mat') else D.mat(cv2.imread(str(oldroot/x['anh']))) for x in old]
model=D.ThuVien(args.thu_vien_mat);out=args.ra.resolve();(out/'nguon').mkdir(parents=True,exist_ok=True)
observations=[[] for _ in old];chosen={};unmatched=[];quality_counts=Counter()
for p in sorted(source.glob('[0-9][0-9].png')):
 image=cv2.imread(str(p));annot=image.copy()
 for j,(aligned,y,quality,legacy) in enumerate(cat_the_hoi_truong(image,kem_chat_luong=True),1):
  m=D.mat(legacy);sim=sorted([(T.giong(m,r),i) for i,r in enumerate(refs)],reverse=True)
  score,i=sim[0]
  if score<.85 or score-sim[1][0]<.02:
   unmatched.append(dict(anh=p.name,vi_tri=j,diem=float(score)));continue
  quality_counts[quality['ly_do']]+=1
  result=model.danh_gia_khung(aligned,chat_luong_cat=quality)
  observations[i].append(dict(anh=p.name,vi_tri=j,giong_tham_chieu=float(score),**result))
  rank=(bool(quality['day_du']),sum(quality.get('ho_tro_vien',[])),score)
  if i not in chosen or rank>chosen[i][0]:chosen[i]=(rank,aligned,quality,m)
  box=quality.get('bien')
  if box:
   a,b,c,d=box;color=(50,190,50) if quality['day_du'] else (0,100,255)
   cv2.rectangle(annot,(a,b),(c,d),color,2);cv2.putText(annot,f'#{i+1}',(a,max(25,b-4)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
 cv2.imwrite(str(out/'nguon'/p.name),annot)
 print('PAGE',p.name,flush=True)
rows=[];comparisons=[]
for i,previous in enumerate(old):
 obs=observations[i];accepted={x['khung'] for x in obs if x['khung'] is not None}
 k=next(iter(accepted)) if len(accepted)==1 else None
 if i in chosen:_,image,quality,m=chosen[i]
 else:image=cv2.imread(str(oldroot/previous['anh']));quality=dict(day_du=False,ly_do='chua_gan_duoc_anh_goc');m=refs[i]
 row=dict(the=image,mat=m,ten=previous['ten'],goi_y=None,diem=previous['diem'],trong_doi=False,khung=k,khung_chi_tiet=obs,ten_nguoi_dung=previous.get('ten_nguoi_dung'),chat_luong_cat=quality)
 rows.append(row)
 comparisons.append(dict(so_the=i+1,ten=previous['ten'],truoc=previous['khung'],sau=k,so_lan_thay=len(obs),so_lan_du_bien=sum(bool(x.get('cat_the',{}).get('day_du')) for x in obs),can_kiem_tra=len(accepted)>1))
with patch.multiple(D,THU_MUC=out,ANH=out/'tuong_cua_toi',KET_QUA=out/'tuong_cua_toi.json'):D.xuat(rows,model)
summary=dict(so_anh=len(list(source.glob('[0-9][0-9].png'))),so_the=len(rows),tong_luot_quan_sat=sum(map(len,observations)),chat_luong_cat=dict(quality_counts),khong_gan_duoc=unmatched,thieu_tham_chieu=[i+1 for i,o in enumerate(observations) if not o],
 truoc=dict(Counter(str(x['khung']) for x in old)),sau=dict(Counter(str(x['khung']) for x in rows)),so_the_doi_ket_qua=sum(x['truoc']!=x['sau'] for x in comparisons),so_the_co_anh_du_bien=sum(x['so_lan_du_bien']>0 for x in comparisons),chi_tiet=comparisons)
(out/'truoc_sau.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
# Standalone comparison with frozen IDs and names.
from html import escape
html=[]
for i,(before,after,c) in enumerate(zip(old,rows,comparisons),1):
 oldpic=out/f'cu_{i:03d}.png';newpic=out/f'moi_{i:03d}.png';cv2.imwrite(str(oldpic),cv2.imread(str(oldroot/before['anh'])));cv2.imwrite(str(newpic),after['the'])
 html.append(f'<article><b>#{i:03d} {escape(before["ten"] or "?")}</b><p>{D.chu_khung(before["khung"])} → {D.chu_khung(after["khung"])}</p><div><figure><img src="{oldpic.name}"><figcaption>Trước</figcaption></figure><figure><img src="{newpic.name}"><figcaption>Sau · {"đủ biên" if after["chat_luong_cat"]["day_du"] else "chưa xác minh biên"}</figcaption></figure></div><small>{c["so_lan_du_bien"]}/{c["so_lan_thay"]} lượt ảnh đủ biên</small></article>')
(out/'so_sanh.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#121c26;color:#edf3f8;font:16px system-ui;padding:20px}section{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}article{background:#243342;padding:14px;border-radius:8px}article>div{display:flex;gap:12px}figure{margin:0}img{width:130px;height:205px}figcaption,small{font-size:12px}</style><h1>Đối chiếu căn khung · 15 ảnh gốc</h1><p>Giữ nguyên số thẻ/tên từ báo cáo tham chiếu. Trường hợp không xác minh được biên vẫn hiển thị ảnh tạm để đối chiếu, nhưng không được dùng để kết luận khung.</p><section>'+''.join(html)+'</section></html>')
print('SUMMARY',json.dumps({k:v for k,v in summary.items() if k!='chi_tiet'},ensure_ascii=False),flush=True)
