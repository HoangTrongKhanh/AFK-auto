"""Đọc lại đúng PNG do ứng dụng đã chụp; chỉ báo sai khác, không học hoặc sửa dữ liệu."""
import argparse,json,sys
from collections import Counter
from pathlib import Path
import cv2
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import doc_tuong_cua_toi as D

def compare(folder):
 folder=Path(folder);session=json.loads((folder/'session.json').read_text());assert session['verified'],'Phiên Android chưa xác minh hoàn tất'
 tv=D.ThuVien();assert tv.phien_ban_mau==session['version'],'Cần dùng cùng bản mẫu Python với Android'
 paths=[folder/name for name in session['pages']];assert all(p.is_file() and p.resolve().is_relative_to(folder.resolve()) for p in paths)
 native=json.loads((folder/'result.json').read_text());py=D.doc([cv2.imread(str(p)) for p in paths],tv,hoi_truong=True)
 differences=[]
 if len(native)!=len(py):differences.append(dict(field='count',android=len(native),python=len(py)))
 for i,(n,p) in enumerate(zip(native,py),1):
  for key in ['ten','goi_y','khung']:
   if n.get(key)!=p.get(key):differences.append(dict(id=i,field=key,android=n.get(key),python=p.get(key)))
  for key in ['day_du','bien','bien_chuan']:
   a=(n.get('chat_luong_cat') or {}).get(key);b=(p.get('chat_luong_cat') or {}).get(key)
   if a!=b:differences.append(dict(id=i,field=key,android=a,python=b))
  if n.get('ly_do_ten')!=p['ten_chi_tiet']['ly_do']:differences.append(dict(id=i,field='ly_do_ten',android=n.get('ly_do_ten'),python=p['ten_chi_tiet']['ly_do']))
 result=dict(version=tv.phien_ban_mau,pages=len(paths),android_count=len(native),python_count=len(py),equal=not differences,differences=differences,
  android_named=sum(bool(x.get('ten')) for x in native),python_named=sum(bool(x.get('ten')) for x in py),
  android_frames=dict(Counter(str(x['khung']) for x in native)),python_frames=dict(Counter(str(x['khung']) for x in py)),
  manual_unchanged=session.get('manual_before_sha256')==session.get('manual_after_sha256'),android_elapsed_ms=session.get('elapsed_ms'),
  heroes=[dict(id=i,ten=x['ten'],khung=x['khung'],goi_y=x['goi_y'],ly_do_ten=x['ten_chi_tiet']['ly_do']) for i,x in enumerate(py,1)])
 (folder/'python-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='heroes'},ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phien');a=p.parse_args();sys.exit(0 if compare(a.phien)['equal'] else 1)
