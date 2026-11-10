"""Bổ sung diện mạo từ thẻ Hội Trường và ảnh đọc tên trực tiếp; chỉ tạo mẫu mặt chờ duyệt."""
import argparse
import json
from pathlib import Path
import cv2
from hoi_truong import cat_the_hoi_truong
from doc_tuong_cua_toi import mat
from quan_ly_mau import KhoMau,MAC_DINH,pixel_sha,sha,ghi_json

# Tên rút gọn/chính tả người dùng đã dùng trong thư viện hiện hành.
TEN_HIEN_THI={'Smokey & Meerky':'Smokey','Lily May':'Lili May','Elijah & Lailah':'SS'}


def nhap(manifest_path,repo):
    manifest_path=Path(manifest_path).resolve();folder=manifest_path.parent
    data=json.loads(manifest_path.read_text());planned=[];cache={};identities=set();batch_labels={}
    protected_pixels=set();protected_sources=set()
    for f in (repo.root/'test_sets').glob('*.json'):
        r=json.loads(f.read_text());protected_pixels.update(r['pixels']);protected_sources.update(r['sources'])
    for r in data['items']:
        name=r['ten'].strip();variant=r['dien_mao'].strip()
        if not name or not variant or any(c in name+variant for c in '/\\\x00'):
            raise ValueError('Cần tên và mã diện mạo hợp lệ')
        display=r.get('ten_doc_tren_man')
        if TEN_HIEN_THI.get(display,display)!=name:raise ValueError('Tên không khớp phần đã đọc trên màn hình')
        source=(folder/r['source_image']).resolve();proof=(folder/r['evidence']).resolve()
        source.relative_to(folder);proof.relative_to(folder)
        source_sha=sha(source.read_bytes());proof_sha=sha(proof.read_bytes())
        if source_sha!=r['source_sha256'] or proof_sha!=r['evidence_sha256']:
            raise ValueError('Ảnh nguồn hoặc bằng chứng đã đổi sau đối chiếu')
        if cv2.imread(str(proof)) is None:raise ValueError('Bằng chứng tên không phải ảnh đọc được')
        if source not in cache:
            image=cv2.imread(str(source))
            if image is None:raise ValueError('Không đọc được ảnh nguồn')
            cache[source]=cat_the_hoi_truong(image,kem_chat_luong=True)
        index=r['source_position']
        if type(index) is not int or not 1<=index<=len(cache[source]):raise ValueError('Vị trí thẻ không có trong ảnh nguồn')
        card=cache[source][index-1]
        if not card[2].get('day_du'):raise ValueError('Thẻ chưa được xác minh đủ biên')
        face=mat(card[3]);pixels=pixel_sha(face)
        if pixels in protected_pixels or {source_sha,proof_sha}&protected_sources:
            raise ValueError('Ảnh thuộc bộ kiểm tra đã bảo vệ; cần nguồn phát triển khác')
        if (name,pixels) in identities:raise ValueError('Trùng mẫu diện mạo trong cùng đợt nhập')
        if pixels in batch_labels and batch_labels[pixels]!=name:raise ValueError('Cùng ảnh có hai tên trong đợt nhập')
        batch_labels[pixels]=name
        identities.add((name,pixels))
        planned.append((face,name,dict(session=data['session'],label_source='on_screen_name',appearance_id=variant,
            source_sha256=source_sha,source_image=r['source_image'],source_position=index,
            label_evidence_sha256=proof_sha,label_evidence_image=r['evidence'],
            displayed_name=display,
            review_manifest_sha256=sha(manifest_path.read_bytes()),group='face:'+name)))
    if not planned:raise ValueError('Không có diện mạo đã xác nhận')
    # Đối chiếu xung đột cả lô trước khi tạo mẫu chờ duyệt.
    _,snapshot=repo.doc()
    for face,name,_ in planned:
        if any(r['kind']=='face' and r['status']!='rejected' and r['pixel_sha256']==pixel_sha(face) and r['label']!=name
               for r in snapshot['records'].values()):raise ValueError('Mẫu đang mang tên khác; cần đối chiếu trước')
    ids=[repo.them(face,'face',name,source) for face,name,source in planned]
    result=dict(sample_ids=ids,so_mau=len(ids),trang_thai='pending',note='Giữ các diện mạo cũ. Duyệt và phát hành phiên bản mới trước khi áp dụng.')
    ghi_json(folder/'ket_qua_nhap_dien_mao.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--kho',type=Path,default=MAC_DINH);a=p.parse_args()
    print(json.dumps(nhap(a.manifest,KhoMau(a.kho)),ensure_ascii=False))
