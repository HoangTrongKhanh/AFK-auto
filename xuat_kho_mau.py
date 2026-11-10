"""Bảng xem mẫu đã duyệt và phiên bản; xuất yêu cầu duyệt, không tự sửa dữ liệu từ trình duyệt."""
import argparse
import base64
from html import escape
import json
from pathlib import Path
from quan_ly_mau import KhoMau,MAC_DINH


def xuat(repo,output):
    revision,data=repo.doc();current=repo.hien_tai();cards=[]
    for n,r in enumerate(data['records'].values(),1):
        png=(repo.root/'blobs'/f"{r['image_sha256']}.png").read_bytes()
        repo.anh(r)
        label=r['label'] if r['kind']=='face' else 'Có khung' if r['label']==1 else 'Không khung'
        hero=next((s.get('group','').partition(':')[2] for s in r['sources'] if s.get('group','').startswith('frame:')),'')
        title=f'{hero} · {label}' if hero else str(label)
        source=', '.join(sorted({s['session'] for s in r['sources']}))
        appearances=', '.join(sorted({s['appearance_id'] for s in r['sources'] if s.get('appearance_id')}))
        if appearances:source+=' · Diện mạo: '+appearances
        cards.append(f'''<article data-kind="{r['kind']}" data-search="{escape(title.casefold())}"><h3>M{n:03d} · {escape(title)}</h3><img src="data:image/png;base64,{base64.b64encode(png).decode()}" alt="Mẫu {n}"><p>{r['kind']} · <b>{r['status']}</b> · {r['role']}</p><p>{escape(source)}</p><small>ID: {r['id']}</small><p>{escape((r.get('review') or {}).get('reason','Chờ đối chiếu'))}</p><label>Đề nghị thay trạng thái<select data-id="{r['id']}"><option value="">Giữ nguyên</option><option value="approved">Duyệt</option><option value="rejected">Loại</option><option value="pending">Chờ đối chiếu</option></select><input data-reason="{r['id']}" placeholder="Lý do bắt buộc khi thay đổi"></label></article>''')
    versions=[]
    for path in sorted((repo.root/'versions').glob('v-*/manifest.json')):
        version=path.parent.name
        try:_,m=repo.kiem_tra_ban(version)
        except ValueError as exc:
            versions.append(f'<li>{escape(version)} · Không dùng với mã hiện tại: {escape(str(exc))}</li>')
            continue
        versions.append(f"<li><b>{version}</b>{' · ĐANG DÙNG' if current and current[1]['version']==version else ''} · {len(m['face_ids'])} mẫu tên, {len(m['training_ids'])} mẫu khung học, {len(m['reserved_ids'])} giữ lại</li>")
    protected=[]
    for path in sorted((repo.root/'test_sets').glob('*.json')):
        entry=json.loads(path.read_text())
        protected.append(f"<li>{escape(entry['dataset_id'])}: {len(entry['pixels'])} thẻ, {len(entry['sources'])} mã ảnh nguồn/dẫn xuất được chặn khỏi tập học.</li>")
    html=HTML.replace('__REV__',revision).replace('__VERSIONS__',''.join(versions)).replace('__CARDS__',''.join(cards))
    html=html.replace('__TESTSETS__',''.join(protected))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(html)


HTML=r'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Quản lý mẫu Python</title><style>*{box-sizing:border-box}body{font:16px/1.5 system-ui;background:#edf2f7;color:#17283b;margin:0}main{max-width:1250px;margin:auto;padding:20px}.box,article{background:white;border:1px solid #cad6e1;border-radius:8px;padding:15px;margin:12px 0}h1{font-size:27px}h3{font-size:18px}small{word-break:break-all}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}article{margin:0}article img{height:155px;max-width:130px;object-fit:contain}select,input,textarea,button{font:inherit;padding:8px;max-width:100%}article select,article input{display:block;width:100%;margin-top:7px}textarea{width:100%;height:220px;display:none}button{cursor:pointer;background:white;border:1px solid #8297aa;border-radius:6px}#message{color:#934818}</style><main><h1>Kho mẫu Python</h1><div class="box"><p>Mẫu tên và khung tách riêng. Nhãn người dùng/đối chiếu trực tiếp mới được duyệt; dữ liệu kiểm tra không được vào mẫu học.</p><ul>__VERSIONS__</ul><p><b>Bộ kiểm tra được bảo vệ</b></p><ul>__TESTSETS__</ul><p>Đổi trạng thái ở bảng tạo <b>yêu cầu duyệt</b>. Chỉ khi áp dụng yêu cầu, tạo bản phát hành mới và kích hoạt thì bộ đọc mới dùng thay đổi. Bản đang chạy và bản cũ được giữ cố định để khôi phục.</p><button id="export">Lấy yêu cầu duyệt</button><p id="message"></p><textarea id="out" aria-label="Yêu cầu duyệt để gửi vào chat"></textarea><p><label>Lọc <select id="filter"><option value="all">Tất cả</option><option value="face">Mẫu tên</option><option value="frame">Mẫu khung</option></select></label> <input id="search" placeholder="Tìm tên hoặc nhãn khung"></p></div><div class="grid">__CARDS__</div></main><script>
const revision='__REV__';function filter(){const k=document.getElementById('filter').value,q=document.getElementById('search').value.trim().toLocaleLowerCase('vi');document.querySelectorAll('article').forEach(x=>x.hidden=!((k==='all'||x.dataset.kind===k)&&x.dataset.search.includes(q)));}document.getElementById('filter').onchange=filter;document.getElementById('search').oninput=filter;
document.getElementById('export').onclick=()=>{const changes=[];for(const x of document.querySelectorAll('select[data-id]')){if(!x.value)continue;const reason=document.querySelector('input[data-reason="'+x.dataset.id+'"]').value.trim();if(!reason){document.getElementById('message').textContent='Cần ghi lý do cho mỗi thay đổi.';return;}changes.push({id:x.dataset.id,status:x.value,reason});}const out=document.getElementById('out');out.value=JSON.stringify({revision,changes},null,2);out.style.display='block';out.focus();out.select();document.getElementById('message').textContent='Gửi JSON này vào chat để áp dụng. Phiên bản đang dùng chưa thay đổi.';};
</script></html>'''.replace('\n+','\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kho',type=Path,default=MAC_DINH);p.add_argument('--ra',type=Path,required=True);a=p.parse_args();xuat(KhoMau(a.kho),a.ra)
