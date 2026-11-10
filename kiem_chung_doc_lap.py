"""Bộ kiểm tra tài khoản khác: cố định ảnh/dự đoán trước, nhận nhãn người dùng sau."""
import argparse
from datetime import datetime, timezone
from html import escape
import inspect
import json
from pathlib import Path
import random
import shutil

import cv2
import numpy as np
import can_khung_tuong as C
import hoi_truong as H
import khung_can_python as K
import doc_tuong_cua_toi as D
import thong_ke_tuong as T
from quan_ly_mau import KhoMau, MAC_DINH, canonical, ghi_json, pixel_sha, sha


def check_freeze(folder,runtime=True):
    protocol=json.loads((folder/'protocol.json').read_text())
    functions={'danh_gia_khung':D.ThuVien.danh_gia_khung,'can_khung':C.can_khung,
               'cat_the_hoi_truong':H.cat_the_hoi_truong,'hang_du_phong':H._hang_tu_bien,
               'dac_trung':K.dac_trung,'du_doan':K.MauKhungCan.du_doan}
    if sha((folder/'model.npz').read_bytes())!=protocol['model_sha256']:raise ValueError('Mô hình đã đổi sau khi cố định')
    if not runtime:return protocol  # Chấm nhãn trên dự đoán niêm phong không chạy lại bộ đọc mới.
    if protocol.get('inference_policy')=='v2':
        from bang_chung_khung import bang_chung,quyet_dinh_v2
        functions.update(bang_chung_v2=bang_chung,quyet_dinh_v2=quyet_dinh_v2)
    for name,digest in protocol['function_sha256'].items():
        if sha(inspect.getsource(functions[name]).encode())!=digest:raise ValueError('Logic đã đổi sau khi cố định: '+name)
    for path,digest in protocol['dependencies'].items():
        if sha(Path(path).read_bytes())!=digest:raise ValueError('Mẫu nền đã đổi: '+path)
    return protocol


def seal_check(folder):
    seal=json.loads((folder/'seal.json').read_text())
    for name,digest in seal['files'].items():
        path=(folder/name).resolve();path.relative_to(folder.resolve())
        if sha(path.read_bytes())!=digest:raise ValueError('Bộ kiểm tra đã đổi: '+name)
    if 'test-'+sha(canonical(seal['files']))[:16]!=seal['dataset_id']:raise ValueError('Mã bộ kiểm tra không khớp')
    return seal


def freeze(folder,model,account,device,inference_policy='v1'):
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'protocol.json').exists():raise ValueError('Protocol đã tồn tại')
    shutil.copyfile(model,folder/'model.npz')
    funcs={'danh_gia_khung':D.ThuVien.danh_gia_khung,'can_khung':C.can_khung,'cat_the_hoi_truong':H.cat_the_hoi_truong,
           'hang_du_phong':H._hang_tu_bien,'dac_trung':K.dac_trung,'du_doan':K.MauKhungCan.du_doan}
    if inference_policy=='v2':
        from bang_chung_khung import bang_chung,quyet_dinh_v2
        funcs.update(bang_chung_v2=bang_chung,quyet_dinh_v2=quyet_dinh_v2)
    deps=[D.THU_VIEN/'vien.bin',D.THU_VIEN/'vien_nhan.bin',*(D.TPL_DIR/name for name in T.MAU_SAO),D.TPL_DIR/'ht_cap.png',D.TPL_DIR/'ht_dau.png']
    ghi_json(folder/'protocol.json',dict(schema=1,inference_policy=inference_policy,scope='canonical_frame_classification',account=account,device=device,
        model_sha256=sha((folder/'model.npz').read_bytes()),function_sha256={n:sha(inspect.getsource(f).encode()) for n,f in funcs.items()},
        dependencies={str(p):sha(p.read_bytes()) for p in deps},selection_seed=20261108,
        label_policy='nguoi_dung_gan_nhan_sau_khi_dong_bang_du_doan',heldout_rule='khong_them_anh_phien_nay_vao_mau_hoc'))


def exclude_previous(folder,previous):
    """Cố định mặt của các nhóm đã kiểm tra để vòng mới không chọn lại cùng nhóm."""
    seal=seal_check(previous);data=json.loads((previous/'dataset.json').read_text());cache={};faces=[]
    for item in data['items']:
        page=item['source_image']
        if page not in cache:cache[page]=H.cat_the_hoi_truong(cv2.imread(str(previous/'anh_goc'/page)),kem_chat_luong=True)
        q=item['quality'];match=next((x for x in cache[page] if abs(x[2]['tam_x']-q['tam_x'])<1 and abs(x[2]['tam_y']-q['tam_y'])<1),None)
        if match is None:raise ValueError('Không đối chiếu được nhóm loại trừ')
        faces.append(D.mat(match[3]))
    np.savez_compressed(folder/'excluded_faces.npz',faces=np.stack(faces))
    protocol=json.loads((folder/'protocol.json').read_text())
    protocol.update(excluded_dataset=seal['dataset_id'],excluded_faces_sha256=sha((folder/'excluded_faces.npz').read_bytes()))
    ghi_json(folder/'protocol.json',protocol)


def prepare(folder,count=50,repo_path=MAC_DINH):
    folder=Path(folder).resolve();protocol=check_freeze(folder)
    if count<1:raise ValueError('Số thẻ kiểm tra phải lớn hơn 0')
    if (folder/'seal.json').exists():raise ValueError('Bộ kiểm tra đã cố định; không chọn lại ảnh')
    pages=sorted((folder/'anh_goc').glob('[0-9][0-9].png'))
    if not pages:raise ValueError('Chưa có ảnh gốc mới')
    excluded=[];excluded_count=0
    if protocol.get('excluded_faces_sha256'):
        if sha((folder/'excluded_faces.npz').read_bytes())!=protocol['excluded_faces_sha256']:raise ValueError('Bộ loại trừ đã đổi')
        with np.load(folder/'excluded_faces.npz',allow_pickle=False) as z:excluded=list(z['faces'])
    groups=[]
    for page in pages:
        for j,(card,y,q,legacy) in enumerate(H.cat_the_hoi_truong(cv2.imread(str(page)),kem_chat_luong=True),1):
            face=D.mat(legacy)
            if any(T.giong(face,f)>=.85 for f in excluded):
                excluded_count+=1;continue
            scores=sorted([(T.giong(face,g['face']),i) for i,g in enumerate(groups)],reverse=True)
            if scores and scores[0][0]>=.85 and (len(scores)==1 or scores[0][0]-scores[1][0]>=.02):
                group=groups[scores[0][1]]
            else:
                group=dict(face=face,observations=[]);groups.append(group)
            group['observations'].append(dict(card=card,quality=q,page=page.name,position=j,
                sharp=float(cv2.Laplacian(face,cv2.CV_64F).var())))
        print('Nhóm ảnh',page.name,flush=True)
    picked=random.Random(protocol['selection_seed']).sample(range(len(groups)),min(count,len(groups)))
    model=D.ThuVien(mau_khung_can=folder/'model.npz',quy_tac_khung=protocol.get('inference_policy','v1'))
    assets=folder/'the';assets.mkdir(exist_ok=True);items=[];predictions=[];cards=[]
    for n,index in enumerate(sorted(picked),1):
        obs=groups[index]['observations']
        best=max(obs,key=lambda x:(x['quality']['day_du'],-abs(x['quality']['tam_y']-1400),x['sharp']))
        card,q=best['card'],best['quality'];cv2.imwrite(str(assets/f'{n:03d}.png'),card)
        raw=cv2.imread(str(folder/'anh_goc'/best['page']))
        if q.get('bien'):a,b,c,d=q['bien']
        else:a,b,c,d=map(int,(q['tam_x']-120,q['tam_y']-190,q['tam_x']+140,q['tam_y']+165))
        context=raw[max(0,b-22):min(raw.shape[0],d+22),max(0,a-22):min(raw.shape[1],c+22)]
        cv2.imwrite(str(assets/f'{n:03d}_nguon.png'),context)
        item=dict(id=n,image=f'the/{n:03d}.png',pixel_sha256=pixel_sha(card),quality=q,
                  source_image=best['page'],source_sha256=sha((folder/'anh_goc'/best['page']).read_bytes()),
                  observations=[dict(page=o['page'],position=o['position']) for o in obs])
        items.append(item);predictions.append(dict(id=n,**model.danh_gia_khung(card,q)))
        cards.append(f'''<article><h2>Thẻ kiểm tra #{n:03d}</h2><div class="pics"><img src="the/{n:03d}.png" alt="Thẻ {n}"><img class="context" src="the/{n:03d}_nguon.png" alt="Ảnh gốc có vùng lân cận"></div><p>{len(obs)} lượt ảnh được gom cùng nhóm; kiểm tra ảnh nguồn nếu nghi ghép nhầm.</p><a href="anh_goc/{best['page']}" target="_blank">Mở ảnh gốc {best['page']}</a><label>Xác nhận khung <select data-id="{n}"><option value="">Chưa chọn</option><option value="1">1 — Có khung</option><option value="0">0 — Không khung</option><option value="?">? — Chưa rõ</option></select></label></article>''')
    manifest=dict(schema=1,account=protocol['account'],device=protocol['device'],seed=protocol['selection_seed'],
        selection='random_appearance_groups_before_predictions',group_count=len(groups),sample_count=len(items),items=items,excluded_observations=excluded_count,
        limits='Nhóm ảnh mặt tự gom, cần người gán nhãn kiểm tra. Chỉ đánh giá các thẻ bộ cắt đề xuất; không đo độ phủ toàn bộ danh sách.')
    ghi_json(folder/'dataset.json',manifest);ghi_json(folder/'predictions_sealed.json',predictions)
    paths=[folder/'protocol.json',folder/'model.npz',folder/'dataset.json',folder/'predictions_sealed.json',*pages,*assets.glob('*.png')]
    if (folder/'excluded_faces.npz').exists():paths.append(folder/'excluded_faces.npz')
    files={p.relative_to(folder).as_posix():sha(p.read_bytes()) for p in sorted(paths)}
    dataset_id='test-'+sha(canonical(files))[:16]
    repo=KhoMau(repo_path)
    repo.bao_ve_tap_kiem_tra(dataset_id,[x['pixel_sha256'] for x in items],
                            [sha(p.read_bytes()) for p in [*pages,*assets.glob('*.png')]],protocol['account'])
    ghi_json(folder/'seal.json',dict(dataset_id=dataset_id,files=files,created_at=datetime.now(timezone.utc).isoformat()))
    page=HTML.replace('__ID__',dataset_id).replace('__N__',str(len(items))).replace('__CARDS__',''.join(cards))
    (folder/'gan_nhan.html').write_text(page)
    (folder/'mau_tra_loi.txt').write_text(f'BO_KIEM_TRA={dataset_id}\n'+''.join(f'{x["id"]}=?\n' for x in items))
    return dict(dataset_id=dataset_id,so_anh=len(pages),so_nhom=len(groups),so_the_cho_nhan=len(items))


def parse_labels(text,dataset_id,ids):
    labels={};token=None
    for raw in text.splitlines():
        line=raw.partition('#')[0].strip()
        if not line:continue
        if line.startswith('BO_KIEM_TRA='):
            if token is not None:raise ValueError('Trùng mã bộ kiểm tra')
            token=line.split('=',1)[1].strip();continue
        try:n,value=line.split('=',1);n=int(n);value=value.strip()
        except ValueError as exc:raise ValueError('Dòng nhãn không đúng SO=1|0|?') from exc
        if n in labels or n not in ids or value not in ('0','1','?'):raise ValueError('Nhãn trùng/ngoài bảng/không hợp lệ')
        labels[n]=None if value=='?' else int(value)
    if token!=dataset_id:raise ValueError('Thiếu hoặc sai mã bộ kiểm tra; không dùng số thẻ của báo cáo cũ')
    if not labels:raise ValueError('Chưa có nhãn')
    return labels


def score(folder,text):
    folder=Path(folder);seal=seal_check(folder);protocol=check_freeze(folder,runtime=False)
    dataset=json.loads((folder/'dataset.json').read_text());ids={x['id'] for x in dataset['items']}
    incoming=parse_labels(text,seal['dataset_id'],ids)
    path=folder/'labels_user.json'
    previous=json.loads(path.read_text()) if path.exists() else dict(dataset_id=seal['dataset_id'],labels={})
    if previous['dataset_id']!=seal['dataset_id']:raise ValueError('Nhãn thuộc bộ khác')
    labels={int(k):v for k,v in previous['labels'].items()};labels.update(incoming)
    predictions={x['id']:x['khung'] for x in json.loads((folder/'predictions_sealed.json').read_text())}
    rows=[dict(id=n,reference=labels[n],prediction=predictions[n]) for n in sorted(labels) if labels[n] is not None]
    correct=sum(r['reference']==r['prediction'] for r in rows)
    wrong=sum(r['prediction'] is not None and r['prediction']!=r['reference'] for r in rows)
    unknown=sum(r['prediction'] is None for r in rows)
    label_record=dict(dataset_id=seal['dataset_id'],labels={str(n):v for n,v in labels.items()},source='user',
                      input_sha256=sha(text.encode()),updated_at=datetime.now(timezone.utc).isoformat())
    if previous.get('labels')==label_record['labels'] and previous.get('source')=='user':
        label_record=previous  # Chấm lại cùng nhãn không tạo một lần sửa nhãn giả.
    label_digest=sha(canonical(label_record))
    if path.exists():
        old=json.loads(path.read_text());ghi_json(folder/'labels_history'/f'{sha(canonical(old))}.json',old)
    ghi_json(folder/'labels_history'/f'{label_digest}.json',label_record)
    result=dict(dataset_id=seal['dataset_id'],inference_policy=protocol.get('inference_policy','v1'),model_sha256=protocol['model_sha256'],protocol_sha256=sha((folder/'protocol.json').read_bytes()),
        nguon_nhan='nguoi_dung_xac_nhan_tap_doc_lap',reference_labels_sha256=label_digest,
        so_the=len(ids),so_tra_loi=len(labels),so_nhan_ro=len(rows),chua_gan_nhan=len(ids-set(labels)),
        nhan_nguoi_dung_chua_ro=sum(v is None for v in labels.values()),dung=correct,sai=wrong,chua_ro=unknown,
        false_positive=sum(r['reference']==0 and r['prediction']==1 for r in rows),
        false_negative=sum(r['reference']==1 and r['prediction']==0 for r in rows),
        coverage=(correct+wrong)/len(rows) if rows else None,
        selective_accuracy=correct/(correct+wrong) if correct+wrong else None,
        complete=len(labels)==len(ids) and all(v is not None for v in labels.values()),chi_tiet=rows,
        gioi_han=dataset['limits'])
    ghi_json(path,label_record)
    ghi_json(folder/'ket_qua.json',result)
    (folder/'ket_qua.md').write_text(f"# Kiểm chứng độc lập\n\nBộ: {seal['dataset_id']}\n\nNhãn rõ: {len(rows)}/{len(ids)}. Đúng {correct}, sai {wrong}, máy chưa rõ {unknown}.\n\n{dataset['limits']}\n")
    return result


HTML=r'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gán nhãn kiểm tra độc lập</title><style>*{box-sizing:border-box}body{font:16px/1.5 system-ui;background:#edf2f7;color:#17283b;margin:0}main{max-width:1250px;margin:auto;padding:20px}.box,article{background:white;border:1px solid #cbd6e2;border-radius:9px;padding:16px;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(345px,1fr));gap:14px}h1{font-size:27px}h2{font-size:20px;margin-top:0}.pics{display:flex;gap:10px;align-items:center}.pics img{width:130px;height:205px;object-fit:contain}.pics .context{max-width:calc(100% - 140px);width:180px;height:auto;max-height:250px}select,button,textarea{font:inherit}select{display:block;width:100%;padding:9px;margin-top:7px}label{display:block;margin-top:12px}button{padding:10px;border:1px solid #8d9eaf;background:#fff;border-radius:6px;cursor:pointer}textarea{width:100%;height:220px;display:none;margin-top:12px}a{color:#175da2}.note{background:#fff1d7;padding:10px}article{margin:0}small{color:#45617a}@media(max-width:400px){main{padding:10px}.grid{grid-template-columns:1fr}}</style><main><h1>Gán nhãn tài khoản kiểm tra độc lập</h1><div class="box"><p>Bộ <b>__ID__</b> · <b>__N__ thẻ</b>. Đây là số thẻ mới của bộ kiểm tra, khác số trong báo cáo tài khoản trước.</p><p class="note">Bảng không hiển thị dự đoán máy. Hãy chọn theo ảnh: <b>1 có khung, 0 không khung, ? chưa rõ</b>. Không suy ra khung từ tên hoặc nhãn của tài khoản cũ. Có thể mở ảnh gốc để xem đủ sao/viền.</p><p>Ảnh được chọn ngẫu nhiên theo nhóm ảnh mặt trước khi chạy dự đoán. Cùng Tab S7, tài khoản khác; kết quả này không đại diện thiết bị khác. Nếu một nhóm bị ghép nhầm hai tướng, báo số nhóm để loại/đánh dấu trường hợp đó.</p><button id="export">Lấy câu trả lời</button> <button id="download">Tải .txt</button><p id="progress"></p><p id="message"></p><textarea id="out" aria-label="Câu trả lời để gửi vào chat"></textarea></div><div class="grid">__CARDS__</div></main><script>
const dataset='__ID__',key='afk-independent-'+dataset,choices=Array.from(document.querySelectorAll('select[data-id]'));const message=document.getElementById('message');
try{const saved=JSON.parse(localStorage.getItem(key)||'{}');choices.forEach(x=>{if(['0','1','?'].includes(saved[x.dataset.id]))x.value=saved[x.dataset.id];});}catch(e){}
function update(){document.getElementById('progress').textContent=`Đã chọn ${choices.filter(x=>x.value!=='').length}/__N__`;try{localStorage.setItem(key,JSON.stringify(Object.fromEntries(choices.map(x=>[x.dataset.id,x.value]))));}catch(e){message.textContent='Không lưu được trên trình duyệt; hãy lấy văn bản trước khi đóng bảng.';}}
choices.forEach(x=>x.addEventListener('change',update));update();
function answer(){return 'BO_KIEM_TRA='+dataset+'\n'+choices.filter(x=>x.value!=='').map(x=>x.dataset.id+'='+x.value).join('\n');}
document.getElementById('export').onclick=()=>{const out=document.getElementById('out');out.style.display='block';out.value=answer();out.focus();out.select();message.textContent='Sao chép phần văn bản này và gửi vào chat; giữ dòng BO_KIEM_TRA.';};
document.getElementById('download').onclick=()=>{const url=URL.createObjectURL(new Blob([answer()],{type:'text/plain;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='nhan_'+dataset+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
</script></html>'''.replace('\n+','\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True)
    sub=p.add_subparsers(dest='cmd',required=True)
    f=sub.add_parser('freeze');f.add_argument('--model',type=Path,required=True);f.add_argument('--account',required=True);f.add_argument('--device',required=True)
    f.add_argument('--policy',choices=['v1','v2'],default='v1')
    f.add_argument('--exclude-dataset',type=Path)
    prep=sub.add_parser('prepare');prep.add_argument('--count',type=int,default=50);prep.add_argument('--kho',type=Path,default=MAC_DINH)
    sc=sub.add_parser('score');sc.add_argument('--nhan',type=Path,required=True)
    a=p.parse_args()
    if a.cmd=='freeze':
        freeze(a.folder,a.model,a.account,a.device,a.policy)
        if a.exclude_dataset:exclude_previous(a.folder,a.exclude_dataset)
        result={'frozen':True}
    elif a.cmd=='prepare':result=prepare(a.folder,a.count,a.kho)
    else:result=score(a.folder,a.nhan.read_text())
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
