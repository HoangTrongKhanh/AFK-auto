"""Đóng gói đúng bản Python đã duyệt cho Android; không chép nhãn khung cá nhân vào APK."""
import json,sys
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from quan_ly_mau import KhoMau,sha,ghi_json
from khung_can_python import MauKhungCan

def export(out, *, version=None):
 repo=KhoMau();folder,m=repo.kiem_tra_ban(version) if version else repo.hien_tai();data=json.loads((folder/'dataset.json').read_text());out.mkdir(parents=True,exist_ok=True)
 with np.load(folder/'faces.npz',allow_pickle=False) as z:
  cv2.imwrite(str(out/'faces.png'),np.hstack(z['mat']));names=z['ten'].tolist()
 model=MauKhungCan.nap(folder/'model.npz')
 ghi_json(out/'model.json',dict(schema=1,features=model.features.tolist(),labels=model.labels.tolist(),ids=model.ids.tolist(),radius=model.radius.tolist(),ratio=model.ratio))
 ghi_json(out/'samples.json',dict(names=names,face_ids=m['face_ids'],records=data['records'],training_ids=m['training_ids'],reserved_ids=m['reserved_ids']))
 protected=[json.loads(p.read_text()) for p in (repo.root/'test_sets').glob('*.json')]
 ghi_json(out/'protected.json',dict(pixels=sorted({s for r in protected for s in r['pixels']}),sources=sorted({s for r in protected for s in r['sources']})))
 manifest=dict(schema=1,engine=1,version=m['version'],python_version=m['version'],inference_policy='v2',name_policy='v2',python_model_sha256=sha((folder/'model.npz').read_bytes()),files={n:sha((out/n).read_bytes()) for n in ['faces.png','model.json','samples.json','protected.json']})
 ghi_json(out/'manifest.json',manifest);print(m['version'],len(names),'mẫu mặt',len(model.labels),'mẫu khung')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version');p.add_argument('--output',type=Path,default=ROOT/'android/app/src/main/assets/vision-v2');a=p.parse_args();export(a.output,version=a.version)
