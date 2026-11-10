"""Kho mẫu cá nhân: duyệt mẫu, bản phát hành bất biến và kích hoạt/khôi phục nguyên tử."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import cv2
import numpy as np
from khung_can_python import MauKhungCan, dac_trung, hoc

MAC_DINH=Path(__file__).resolve().parent/'thu_thap_tuong'/'kho_mau'


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()


def sha(data):return hashlib.sha256(data).hexdigest()


def pixel_sha(image):
    return sha(str(image.shape).encode()+image.dtype.str.encode()+image.tobytes())


def policy_sha(policy):
    if policy=='v1':return 'legacy-v1'
    if policy!='v2':raise ValueError('Sai phiên bản quy tắc')
    from bang_chung_khung import bang_chung,quyet_dinh_v2
    from doc_tuong_cua_toi import ThuVien
    from can_khung_tuong import can_khung,diem_sao_da_ty_le
    from hoi_truong import cat_the_hoi_truong,_hang_tu_bien
    functions=(bang_chung,quyet_dinh_v2,ThuVien.danh_gia_khung,can_khung,
               diem_sao_da_ty_le,cat_the_hoi_truong,_hang_tu_bien,dac_trung,MauKhungCan.du_doan)
    import doc_tuong_cua_toi as D
    import thong_ke_tuong as T
    deps=[D.TPL_DIR/name for name in (*T.MAU_SAO,'ht_cap.png','ht_dau.png')]
    return sha(canonical(dict(code=''.join(inspect.getsource(f) for f in functions),
                              inputs={p.name:sha(p.read_bytes()) for p in deps})))


def name_policy_sha(policy):
    if policy=='v1':return 'legacy-names-v1'
    if policy!='v2':raise ValueError('Sai phiên bản quy tắc tên')
    from ten_dien_mao import danh_gia_ten
    from doc_tuong_cua_toi import gan_ten,ThuVien,doc
    from cat_the_bo_sung import cat_day_du
    return sha(''.join(inspect.getsource(f) for f in (danh_gia_ten,gan_ten,ThuVien.diem,doc,cat_day_du)).encode())


def ghi_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        pending=Path(f.name);f.write(canonical(value));f.flush();os.fsync(f.fileno())
    try:os.replace(pending,path)
    finally:pending.unlink(missing_ok=True)


class KhoMau:
    def __init__(self,root=MAC_DINH):self.root=Path(root)

    @contextmanager
    def lock(self):
        self.root.mkdir(parents=True,exist_ok=True)
        with (self.root/'.lock').open('a') as f:
            fcntl.flock(f,fcntl.LOCK_EX)
            try:yield
            finally:fcntl.flock(f,fcntl.LOCK_UN)

    def doc(self):
        pointer=self.root/'HEAD.json'
        if not pointer.exists():return '',dict(schema=1,records={})
        revision=json.loads(pointer.read_text())['revision']
        if not re.fullmatch('[0-9a-f]{64}',revision):raise ValueError('Sai mã bản dữ liệu')
        raw=(self.root/'revisions'/f'{revision}.json').read_bytes()
        if sha(raw)!=revision:raise ValueError('Bản dữ liệu bị thay đổi')
        return revision,json.loads(raw)

    def _commit(self,data,action):
        raw=canonical(data);revision=sha(raw);path=self.root/'revisions'/f'{revision}.json'
        if not path.exists():ghi_json(path,data)
        ghi_json(self.root/'HEAD.json',dict(revision=revision))
        # Lịch sử duyệt nằm trong các revision; nhật ký thao tác chỉ để tra cứu.
        log=self.root/'events.json';events=json.loads(log.read_text()) if log.exists() else []
        events.append(dict(action=action,revision=revision,at=datetime.now(timezone.utc).isoformat()))
        ghi_json(log,events)
        return revision

    def anh(self,record):
        digest=record['image_sha256']
        if not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Sai mã ảnh')
        raw=(self.root/'blobs'/f'{digest}.png').read_bytes()
        if sha(raw)!=digest:raise ValueError('Ảnh mẫu đã đổi')
        image=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
        if image is None or pixel_sha(image)!=record['pixel_sha256']:raise ValueError('Ảnh mẫu không khớp nội dung')
        return image

    def them(self,image,kind,label,source,*,role='train',quality=None):
        if kind not in ('face','frame') or role not in ('train','validation','test'):raise ValueError('Sai loại mẫu/vai trò')
        shape=(48,48,3) if kind=='face' else (205,130,3)
        if image is None or image.shape!=shape or image.dtype!=np.uint8:raise ValueError('Ảnh mẫu sai định dạng')
        if kind=='face' and (not isinstance(label,str) or not label.strip()):raise ValueError('Mẫu mặt cần tên đã đối chiếu')
        if kind=='frame' and (type(label) is not int or label not in (0,1)):raise ValueError('Mẫu học khung cần nhãn 0/1')
        if not source.get('session') or not source.get('label_source'):raise ValueError('Thiếu nguồn ảnh/nhãn')
        ok,encoded=cv2.imencode('.png',image)
        if not ok:raise OSError('Không mã hóa được mẫu')
        raw=encoded.tobytes();pixels=pixel_sha(image);digest=sha(raw)
        sample_id=sha(canonical(dict(kind=kind,pixel=pixels,label=label)))[:24]
        with self.lock():
            _,data=self.doc();records=data['records']
            for old in records.values():
                if old['kind']==kind and old['pixel_sha256']==pixels and old['label']!=label and old['status']!='rejected':
                    raise ValueError('Cùng ảnh đang mang nhãn khác; cần loại/đối chiếu mẫu cũ trước')
            if sample_id in records:
                old=records[sample_id]
                if old['role']!=role:raise ValueError('Mẫu đã có vai trò khác; không tự chuyển tập kiểm tra sang học')
                if source not in old['sources']:old['sources'].append(source)
            else:
                blob=self.root/'blobs'/f'{digest}.png';blob.parent.mkdir(exist_ok=True)
                if not blob.exists():blob.write_bytes(raw)
                records[sample_id]=dict(id=sample_id,kind=kind,label=label,role=role,status='pending',
                    image_sha256=digest,pixel_sha256=pixels,sources=[source],quality=quality,review=None)
            self._commit(data,'add:'+sample_id)
        return sample_id

    def duyet(self,sample_id,status,reason,by='nguoi_quan_ly',expected_revision=None):
        return self.duyet_nhieu([dict(id=sample_id,status=status,reason=reason)],by=by,expected_revision=expected_revision)

    def duyet_nhieu(self,changes,by='nguoi_quan_ly',expected_revision=None):
        if not changes or len({x['id'] for x in changes})!=len(changes):raise ValueError('Danh sách duyệt rỗng hoặc trùng mẫu')
        with self.lock():
            revision,data=self.doc()
            if expected_revision is not None and revision!=expected_revision:raise ValueError('Dữ liệu đã đổi trong khi duyệt')
            # Xét trạng thái cuối của cả lô, cho phép loại nhãn cũ và duyệt nhãn
            # sửa trong cùng thao tác mà không phụ thuộc thứ tự hiển thị.
            for change in changes:
                if change['status'] not in ('approved','rejected','pending') or not change['reason'].strip():
                    raise ValueError('Cần trạng thái/lý do duyệt rõ ràng')
                data['records'][change['id']]['status']=change['status']
            for change in changes:
                sample_id,status,reason=change['id'],change['status'],change['reason']
                if status not in ('approved','rejected','pending') or not reason.strip():raise ValueError('Cần trạng thái/lý do duyệt rõ ràng')
                record=data['records'][sample_id]
                if status=='approved':
                    self.anh(record)
                    if not all(s['label_source'] in ('user_confirmed','on_screen_name') for s in record['sources']):
                        raise ValueError('Nhãn tự đoán không được tự đưa vào tập đã duyệt')
                    if record['kind']=='frame':dac_trung(self.anh(record),record['quality'] or {})
                    if any(r['id']!=sample_id and r['kind']==record['kind'] and r['status']=='approved'
                           and r['pixel_sha256']==record['pixel_sha256'] and r['label']!=record['label'] for r in data['records'].values()):
                        raise ValueError('Xung đột nhãn ảnh đã duyệt')
                record['status']=status;record['review']=dict(by=by,reason=reason,at=datetime.now(timezone.utc).isoformat())
            return self._commit(data,'review_batch:'+str(len(changes)))

    def phat_hanh(self,model_path,training_ids,*,evidence=None,expected_revision=None,inference_policy=None,name_policy=None):
        """Tạo bộ cố định; chỉ dữ liệu đã duyệt được vào mẫu học. Chưa đổi bản đang chạy."""
        with self.lock():
            if name_policy is None or inference_policy is None:
                current=self.hien_tai()
                if name_policy is None:name_policy=current[1].get('name_policy','v1') if current else 'v1'
                if inference_policy is None:inference_policy=current[1].get('inference_policy','v1') if current else 'v1'
            name_digest=name_policy_sha(name_policy)
            revision,data=self.doc()
            if expected_revision is not None and revision!=expected_revision:raise ValueError('Dữ liệu đã đổi trước phát hành')
            model=MauKhungCan.nap(model_path)
            if evidence and evidence.get('model_sha256') and evidence['model_sha256']!=sha(Path(model_path).read_bytes()):
                raise ValueError('Bằng chứng kiểm tra thuộc mô hình khác')
            if evidence and evidence.get('inference_policy') and evidence['inference_policy']!=inference_policy:
                raise ValueError('Bằng chứng kiểm tra thuộc quy tắc khác')
            if evidence and evidence.get('name_policy') and evidence['name_policy']!=name_policy:
                raise ValueError('Bằng chứng kiểm tra thuộc quy tắc tên khác')
            if len(training_ids)!=len(set(training_ids)) or len(training_ids)!=len(model.labels):raise ValueError('Danh sách mẫu học không khớp mô hình')
            if len(set(model.ids.tolist()))!=len(model.ids):raise ValueError('Mỗi tướng chỉ lấy một mẫu trong bản học này')
            for i,sample_id in enumerate(training_ids):
                r=data['records'][sample_id]
                if r['kind']!='frame' or r['status']!='approved' or r['role']!='train':raise ValueError('Mẫu chưa duyệt/bị loại/tập kiểm tra không được vào mô hình')
                image=self.anh(r)
                if r['label']!=int(model.labels[i]) or not np.allclose(dac_trung(image,r['quality']),model.features[i],rtol=0,atol=1e-7):
                    raise ValueError('Đặc trưng/nhãn mô hình không khớp đúng ảnh nguồn')
                if not any(s.get('hero_id')==int(model.ids[i]) for s in r['sources']):raise ValueError('ID mẫu học không khớp nguồn')
            train_pixels={data['records'][x]['pixel_sha256'] for x in training_ids}
            all_training=[data['records'][x] for x in training_ids]+[
                r for r in data['records'].values() if r['kind']=='face' and r['role']=='train' and r['status']=='approved']
            for reservation in (self.root/'test_sets').glob('*.json'):
                reserved_set=json.loads(reservation.read_text())
                if ({r['pixel_sha256'] for r in all_training}&set(reserved_set['pixels'])
                        or {s.get('source_sha256') for r in all_training for s in r['sources']}&set(reserved_set['sources'])):
                    raise ValueError('Mẫu học trùng ảnh hoặc ảnh gốc của bộ kiểm tra đã bảo vệ')
            reserved=[r for r in data['records'].values() if r['kind']=='frame' and r['role']!='train']
            if train_pixels&{r['pixel_sha256'] for r in reserved}:raise ValueError('Ảnh học trùng tập giữ lại')
            train_groups={s.get('group') for x in training_ids for s in data['records'][x]['sources'] if s.get('group')}
            reserved_groups={s.get('group') for r in reserved for s in r['sources'] if s.get('group')}
            if train_groups&reserved_groups:raise ValueError('Tướng học trùng nhóm giữ lại')
            versions=self.root/'versions';versions.mkdir(exist_ok=True)
            stage=Path(tempfile.mkdtemp(prefix='.stage-',dir=versions))
            try:
                shutil.copyfile(model_path,stage/'model.npz')
                faces=[r for r in data['records'].values() if r['kind']=='face' and r['status']=='approved' and r['role']=='train']
                faces.sort(key=lambda r:r['id'])
                arrays=np.stack([self.anh(r) for r in faces]) if faces else np.empty((0,48,48,3),np.uint8)
                np.savez_compressed(stage/'faces.npz',mat=arrays,ten=np.array([r['label'] for r in faces],dtype=str))
                ghi_json(stage/'dataset.json',data)
                manifest=dict(schema=1,revision=revision,inference_policy=inference_policy,policy_sha256=policy_sha(inference_policy),
                    name_policy=name_policy,name_policy_sha256=name_digest,training_ids=list(training_ids),face_ids=[r['id'] for r in faces],
                    reserved_ids=[r['id'] for r in reserved],evidence=evidence or {},
                    files={p.name:sha(p.read_bytes()) for p in stage.iterdir()})
                version='v-'+sha(canonical(manifest))[:16]
                manifest['version']=version;ghi_json(stage/'manifest.json',manifest)
                final=versions/version
                if final.exists():self.kiem_tra_ban(version)
                else:os.replace(stage,final)
            finally:
                if stage.exists():shutil.rmtree(stage)
            return version

    def bao_ve_tap_kiem_tra(self,dataset_id,pixels,sources,account):
        if not re.fullmatch('[a-zA-Z0-9_-]{8,64}',dataset_id):raise ValueError('Sai mã bộ kiểm tra')
        entry=dict(schema=1,dataset_id=dataset_id,pixels=sorted(set(pixels)),sources=sorted(set(sources)),account=account)
        with self.lock():
            _,data=self.doc()
            for r in data['records'].values():
                if r['role']=='train' and r['status']=='approved' and (r['pixel_sha256'] in pixels or any(s.get('source_sha256') in sources for s in r['sources'])):
                    raise ValueError('Bộ kiểm tra đã trùng mẫu học; không được gọi là độc lập')
            path=self.root/'test_sets'/f'{dataset_id}.json'
            if path.exists() and json.loads(path.read_text())!=entry:raise ValueError('Không được ghi đè bộ kiểm tra đã bảo vệ')
            ghi_json(path,entry)

    def huan_luyen(self,output):
        revision,data=self.doc();groups={}
        for r in data['records'].values():
            if r['kind']!='frame' or r['status']!='approved' or r['role']!='train':continue
            key=r['sources'][0].get('group',r['id'])
            if key in groups and groups[key]['label']!=r['label']:raise ValueError('Một nhóm mẫu có nhãn khung mâu thuẫn')
            old=groups.get(key)
            rank=lambda row:float(cv2.Laplacian(self.anh(row),cv2.CV_64F).var())
            if old is None or (rank(r),r['id'])>(rank(old),old['id']):groups[key]=r
        records=sorted(groups.values(),key=lambda r:r['id'])
        for reservation in (self.root/'test_sets').glob('*.json'):
            reserved=json.loads(reservation.read_text())
            if ({r['pixel_sha256'] for r in records}&set(reserved['pixels'])
                    or {s.get('source_sha256') for r in records for s in r['sources']}&set(reserved['sources'])):
                raise ValueError('Không được học từ ảnh của bộ kiểm tra đã bảo vệ')
        features=[dac_trung(self.anh(r),r['quality']) for r in records]
        ids=[r['sources'][0]['hero_id'] for r in records]
        if len(set(ids))!=len(ids):raise ValueError('ID tướng học bị trùng; cần đối chiếu nhóm trước')
        model=hoc(features,[r['label'] for r in records],ids);model.luu(output)
        training_ids=[r['id'] for r in records]
        ghi_json(Path(output).with_suffix('.training.json'),dict(revision=revision,training_ids=training_ids))
        return dict(revision=revision,training_ids=training_ids)

    def mo_rong_bao_ve(self,dataset_id,sources):
        """Chỉ thêm mã ảnh dẫn xuất đã niêm phong, không được gỡ bảo vệ cũ."""
        if not re.fullmatch('[a-zA-Z0-9_-]{8,64}',dataset_id):raise ValueError('Sai mã bộ kiểm tra')
        with self.lock():
            path=self.root/'test_sets'/f'{dataset_id}.json';old=json.loads(path.read_text())
            _,data=self.doc()
            if any(r['status']=='approved' and r['role']=='train' and any(s.get('source_sha256') in sources for s in r['sources']) for r in data['records'].values()):
                raise ValueError('Nguồn đã dùng để học; không thể gọi là kiểm tra độc lập')
            ghi_json(self.root/'test_sets_history'/f'{dataset_id}-{sha(canonical(old))}.json',old)
            new=dict(old,sources=sorted(set(old['sources'])|set(sources)));ghi_json(path,new)

    def kiem_tra_ban(self,version):
        if not re.fullmatch('v-[0-9a-f]{16}',version):raise ValueError('Sai mã phiên bản')
        folder=self.root/'versions'/version
        manifest=json.loads((folder/'manifest.json').read_text())
        base={k:v for k,v in manifest.items() if k!='version'}
        if manifest['version']!=version or 'v-'+sha(canonical(base))[:16]!=version:raise ValueError('Manifest bị thay đổi')
        if manifest.get('policy_sha256') and manifest['policy_sha256']!=policy_sha(manifest.get('inference_policy','v1')):
            raise ValueError('Mã quy tắc không khớp phiên bản; cần dùng đúng mã hoặc phát hành bản mới')
        if manifest.get('name_policy_sha256') and manifest['name_policy_sha256']!=name_policy_sha(manifest.get('name_policy','v1')):
            raise ValueError('Mã quy tắc tên không khớp phiên bản')
        if set(manifest['files'])!={'dataset.json','model.npz','faces.npz'}:raise ValueError('Sai danh sách tệp phiên bản')
        for name,digest in manifest['files'].items():
            if sha((folder/name).read_bytes())!=digest:raise ValueError(f'Tệp phiên bản bị thay đổi: {name}')
        MauKhungCan.nap(folder/'model.npz')
        with np.load(folder/'faces.npz',allow_pickle=False) as z:
            if z['mat'].dtype!=np.uint8 or z['mat'].shape[1:]!=(48,48,3) or z['ten'].ndim!=1 or len(z['mat'])!=len(z['ten']):
                raise ValueError('Bộ mẫu mặt không đúng định dạng')
        return folder,manifest

    def hien_tai(self):
        pointer=self.root/'current.json'
        if not pointer.exists():return None
        current=json.loads(pointer.read_text());folder,manifest=self.kiem_tra_ban(current['active'])
        if sha((folder/'manifest.json').read_bytes())!=current['manifest_sha256']:raise ValueError('Con trỏ phiên bản không khớp manifest')
        return folder,manifest

    def kich_hoat(self,version):
        with self.lock():
            folder,manifest=self.kiem_tra_ban(version)
            pointer=self.root/'current.json';current=json.loads(pointer.read_text()) if pointer.exists() else dict(history=[])
            if current.get('active')==version:return version
            if current.get('active'):
                self.hien_tai()
                current['history'].append(dict(active=current['active'],manifest_sha256=current['manifest_sha256']))
            current.update(active=version,manifest_sha256=sha((folder/'manifest.json').read_bytes()))
            ghi_json(pointer,current)
            return version

    def khoi_phuc(self):
        with self.lock():
            pointer=self.root/'current.json';current=json.loads(pointer.read_text())
            if not current['history']:raise ValueError('Chưa có phiên bản trước để khôi phục')
            previous=current['history'][-1];folder,_=self.kiem_tra_ban(previous['active'])
            if sha((folder/'manifest.json').read_bytes())!=previous['manifest_sha256']:raise ValueError('Bản cần khôi phục bị thay đổi')
            ghi_json(pointer,dict(**previous,history=current['history'][:-1]))
            return previous['active']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kho',type=Path,default=MAC_DINH)
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('list');sub.add_parser('current');sub.add_parser('rollback')
    batch=sub.add_parser('apply-review');batch.add_argument('--file',type=Path,required=True)
    add=sub.add_parser('add');add.add_argument('--image',type=Path,required=True);add.add_argument('--kind',choices=['face','frame'],required=True);add.add_argument('--label',required=True);add.add_argument('--source',type=Path,required=True);add.add_argument('--role',choices=['train','validation','test'],default='train');add.add_argument('--quality',type=Path)
    train=sub.add_parser('train');train.add_argument('--output',type=Path,required=True)
    review=sub.add_parser('review');review.add_argument('id');review.add_argument('status',choices=['approved','rejected','pending']);review.add_argument('--reason',required=True)
    activate=sub.add_parser('activate');activate.add_argument('version')
    publish=sub.add_parser('publish');publish.add_argument('--model',type=Path,required=True);publish.add_argument('--training-ids',type=Path,required=True);publish.add_argument('--evidence',type=Path)
    publish.add_argument('--policy',choices=['v1','v2'])
    publish.add_argument('--name-policy',choices=['v1','v2'])
    a=p.parse_args();repo=KhoMau(a.kho)
    if a.cmd=='list':result=repo.doc()[1]
    elif a.cmd=='apply-review':
        request=json.loads(a.file.read_text());result=repo.duyet_nhieu(request['changes'],by='user_review_request',expected_revision=request['revision'])
    elif a.cmd=='add':result=repo.them(cv2.imread(str(a.image)),a.kind,int(a.label) if a.kind=='frame' else a.label,json.loads(a.source.read_text()),role=a.role,quality=json.loads(a.quality.read_text()) if a.quality else None)
    elif a.cmd=='train':result=repo.huan_luyen(a.output)
    elif a.cmd=='current':
        current=repo.hien_tai();result=current[1] if current else None
    elif a.cmd=='rollback':result=repo.khoi_phuc()
    elif a.cmd=='activate':result=repo.kich_hoat(a.version)
    elif a.cmd=='review':result=dict(revision=repo.duyet(a.id,a.status,a.reason),note='Thay đổi chờ áp dụng trong bản phát hành mới; bản đang chạy được giữ cố định.')
    else:
        training=json.loads(a.training_ids.read_text())
        ids=training['training_ids'] if isinstance(training,dict) else training
        result=repo.phat_hanh(a.model,ids,evidence=json.loads(a.evidence.read_text()) if a.evidence else None,
                            expected_revision=training.get('revision') if isinstance(training,dict) else None,inference_policy=a.policy,name_policy=a.name_policy)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
