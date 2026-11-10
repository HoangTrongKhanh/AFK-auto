"""Di chuyển các nhãn đã xác nhận vào kho phiên bản; không đưa nhãn máy vào mẫu học."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from quan_ly_mau import KhoMau, MAC_DINH, sha
from hoi_truong import cat_the_hoi_truong


def chuyen(root,repo):
    names=root/'debug/can-bo-sung-ten-20261030/ten_da_xac_nhan.json'
    face_dir=root/'thu_thap_tuong/mat_xac_nhan'
    for r in json.loads(names.read_text()):
        image=cv2.imread(str(face_dir/r['mau_mat']))
        sid=repo.them(image,'face',r['ten'],dict(session=r['phien'],label_source='user_confirmed',
            label_evidence_sha256=sha(names.read_bytes()),hero_id=r['so_the'],group='face:'+r['ten']))
        repo.duyet(sid,'approved','Đối chiếu nhãn tên người dùng và mã snapshot gốc',by='migration_verified_labels')
    direct=root/'tests/fixtures/tuong_da_xac_nhan'
    for name,r in json.loads((direct/'nhan.json').read_text()).items():
        sid=repo.them(cv2.imread(str(direct/r['mat'])),'face',name,dict(session='ten_truc_tiep_20261030',
            label_source='on_screen_name',label_evidence_sha256=sha((direct/r['bang_chung']).read_bytes()),group='face:'+name))
        repo.duyet(sid,'approved','Tên hiển thị trực tiếp đã được kiểm tra trên game',by='migration_verified_labels')
    # Damian đã được đối chiếu trực tiếp trước đợt bổ sung 97 tên.
    for f in face_dir.glob('Damian~*.png'):
        sid=repo.them(cv2.imread(str(f)),'face','Damian',dict(session='xac_nhan_damian_cu',label_source='on_screen_name',
            label_evidence_sha256=sha(f.read_bytes()),group='face:Damian'))
        repo.duyet(sid,'approved','Giữ mẫu Damian đã xác nhận ở bước trước',by='migration_verified_labels')
    original=root/'debug/can-lai-khung-20261030'
    raw=(original/'tuong_cua_toi.json').read_bytes();rows=json.loads(raw)
    labels_path=root/'debug/da-xac-nhan-khung-20261107/khung_da_xac_nhan.json';labels=json.loads(labels_path.read_text())
    split=json.loads((root/'debug/cai-thien-khung-20261107/chia_tap.json').read_text())
    train=set(split['huan_luyen']);by_hero={};cache={}
    for r in labels:
        n=r['so_the'];row=rows[n-1]
        if r['sha256_json_goc']!=sha(raw) or row['ten']!=r['ten']:raise ValueError('Nhãn khung không khớp snapshot')
        obs=row['khung_chi_tiet'][0];page=obs['anh']
        if page not in cache:
            cache[page]=cat_the_hoi_truong(cv2.imread(str(root/'debug/hoi-truong-buoc-nho-20261030'/page)),kem_chat_luong=True)
        card,_,q,_=cache[page][obs['vi_tri']-1]
        sid=repo.them(card,'frame',r['khung'],dict(session='hoi_truong_20261030',label_source='user_confirmed',
            label_evidence_sha256=sha(labels_path.read_bytes()),hero_id=n,group='frame:'+r['ten'],
            source_sha256=sha((root/'debug/hoi-truong-buoc-nho-20261030'/page).read_bytes()),
            source_image=page,source_position=obs['vi_tri']),role='train' if n in train else 'validation',quality=q)
        repo.duyet(sid,'approved','Nhãn khung người dùng; giữ nguyên tách 29 học/14 kiểm tra',by='migration_verified_labels')
        by_hero[n]=sid
    model=root/'thu_thap_tuong/khung_can_python.npz'
    with np.load(model,allow_pickle=False) as z:training=[by_hero[int(n)] for n in z['ids']]
    return model,training


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kho',type=Path,default=MAC_DINH);p.add_argument('--activate',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parent;repo=KhoMau(a.kho);model,training=chuyen(root,repo)
    a.kho.mkdir(parents=True,exist_ok=True);(a.kho/'training_ids.json').write_text(json.dumps(training,indent=2))
    version=repo.phat_hanh(model,training,evidence=dict(type='migration_existing_confirmed_labels'))
    if a.activate:repo.kich_hoat(version)
    revision,data=repo.doc();print(json.dumps(dict(version=version,revision=revision,so_mau=len(data['records']),
        faces=sum(r['kind']=='face' for r in data['records'].values()),frames=sum(r['kind']=='frame' for r in data['records'].values())),indent=2))


if __name__=='__main__':main()
