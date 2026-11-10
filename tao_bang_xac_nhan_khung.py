"""Xuất bảng đối chiếu bằng mắt; chỉ thu nhãn khi người dùng tự chọn trong bảng.

Không sửa kết quả máy, thư viện mặt hay mẫu khung. Nhận xét của trợ lý và
xác nhận của người dùng được giữ ở hai trường riêng biệt.
"""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path

import cv2


def chu(value):
    return {None: "Chưa rõ", 0: "Không khung", 1: "Có khung"}[value]


def tao_bang(bao_cao, anh_goc, danh_gia, ra):
    raw_json = (bao_cao / "tuong_cua_toi.json").read_bytes()
    rows = json.loads(raw_json)
    review = json.loads(danh_gia.read_text())
    digest = hashlib.sha256(raw_json).hexdigest()
    if digest != review["sha256_json_goc"]:
        raise ValueError("Báo cáo nguồn đã đổi; cần đối chiếu lại nhận xét trước khi xuất bảng.")
    for filename, expected in review.get("sha256_anh_goc", {}).items():
        if hashlib.sha256((anh_goc / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Ảnh nguồn {filename} đã đổi; cần kiểm tra bằng mắt lại.")
    audit = review["chi_tiet"]
    if len(rows) != len(audit):
        raise ValueError("Số thẻ không khớp bản kiểm tra bằng mắt.")
    for n, (row, item) in enumerate(zip(rows, audit), 1):
        if (n, row["ten"], row["khung"]) != (item["so_the"], item["ten"], item["sau"]):
            raise ValueError(f"Số/tên/kết quả thẻ #{n} đã đổi.")
    ra.mkdir(parents=True, exist_ok=True)
    assets = ra / "anh"
    assets.mkdir(exist_ok=True)
    articles = []
    manifest = []
    for row, item in zip(rows, audit):
        n = item["so_the"]
        quality = row["chat_luong_cat"]
        obs = next(o for o in row["khung_chi_tiet"] if o["cat_the"] == quality)
        source_path = anh_goc / obs["anh"]
        source = cv2.imread(str(source_path))
        if source is None:
            raise ValueError(f"Không đọc được ảnh gốc: {source_path}")
        h, w = source.shape[:2]
        if quality.get("bien"):
            left, top, right, bottom = quality["bien"]
            proposed_boundary = True
        else:
            # Chỉ là vùng ngữ cảnh, không được coi là biên đã xác minh.
            cx, cy = quality["tam_x"], quality["tam_y"]
            left, top, right, bottom = map(int, (cx-115, cy-175, cx+130, cy+155))
            proposed_boundary = False
        a, b = max(0, left-20), max(0, top-20)
        c, d = min(w, right+20), min(h, bottom+20)
        context = source[b:d, a:c]
        marked = context.copy()
        if proposed_boundary:
            cv2.rectangle(marked, (left-a, top-b), (right-a-1, bottom-b-1), (35, 150, 30), 2)
        pictures = {
            "truoc": cv2.imread(str(bao_cao / f"cu_{n:03d}.png")),
            "sau": cv2.imread(str(bao_cao / row["anh"])),
            "nguon": context,
            "bien": marked,
            "vung_sao": source[max(0, top-12):min(h, top+105), a:c],
        }
        for label, im in pictures.items():
            if im is None or not im.size:
                raise ValueError(f"Ảnh rỗng ở thẻ #{n}: {label}")
            if not cv2.imwrite(str(assets / f"{n:03d}_{label}.png"), im):
                raise OSError(f"Không ghi được ảnh #{n}: {label}")
        manual = item["can_xac_nhan"]
        state = "Có sao nhìn thấy" if item["sao_khung_nhin_thay"] else "Không thấy hàng sao khung"
        warning = "<strong class='warn'>Bổ sung: nghi máy nhận nhầm tóc thành sao</strong>" if n == 95 else ""
        source_link = source_path.resolve().as_uri()
        name = escape(row["ten"])
        controls = (
            f'<label class="answer">Bạn xác nhận #{n}: '
            f'<select class="decision" data-id="{n}" aria-label="Xác nhận khung thẻ {n} {name}">'
            '<option value="">Chưa chọn</option><option value="1">1 — Có khung</option>'
            '<option value="0">0 — Không khung</option><option value="?">? — Chưa rõ / cần ảnh khác</option>'
            '</select></label>'
        ) if manual else ""
        articles.append(f'''<article id="the-{n}" data-id="{n}" data-unknown="{int(row['khung'] is None)}"
            data-needs="{int(manual)}" data-changed="{int(item['doi_ket_qua'])}"
            data-star="{int(item['sao_khung_nhin_thay'])}" data-search="{escape(f'{n} {row['ten']}'.casefold())}">
          <h2>#{n:03d} {name}</h2>{warning}
          <p class="machine">Máy: {chu(item['truoc'])} → {chu(item['sau'])}</p>
          <div class="pair"><figure><a href="anh/{n:03d}_truoc.png" target="_blank"><img loading="lazy" src="anh/{n:03d}_truoc.png" alt="Thẻ {n} trước căn"></a><figcaption>Trước</figcaption></figure>
          <figure><a href="anh/{n:03d}_sau.png" target="_blank"><img loading="lazy" src="anh/{n:03d}_sau.png" alt="Thẻ {n} sau căn"></a><figcaption>{'Sau căn' if quality['day_du'] else 'Ảnh tạm — máy chưa tìm được biên'}</figcaption></figure></div>
          <p><b>Quan sát của trợ lý:</b> {state}.</p><p class="note">{escape(item['nhan_xet'])}</p>
          <details><summary>Ảnh nguồn và vùng sao · {escape(obs['anh'])}</summary>
          <figure><img class="context" loading="lazy" src="anh/{n:03d}_nguon.png" alt="Ảnh nguồn thẻ {n}, có vùng lân cận"><figcaption>Ảnh nguồn có ngữ cảnh; có thể thấy một phần hàng kế bên</figcaption></figure>
          <figure><img class="context" loading="lazy" src="anh/{n:03d}_vung_sao.png" alt="Vùng trên thẻ {n}"><figcaption>Vùng phía trên để đối chiếu sao, tóc và mũ</figcaption></figure>
          <figure><img class="context" loading="lazy" src="anh/{n:03d}_bien.png" alt="Biên máy đề xuất cho thẻ {n}"><figcaption>{'Đường xanh là biên máy đã chọn' if proposed_boundary else 'Vùng ngữ cảnh; máy chưa tìm được biên'}</figcaption></figure>
          <a href="{escape(source_link)}" target="_blank">Mở toàn ảnh gốc {escape(obs['anh'])}</a></details>{controls}</article>''')
        manifest.append(dict(**item, anh_nguon=str(source_path.resolve()), so_luot=len(row["khung_chi_tiet"])))
    unknown = [x for x in manifest if x["sau"] is None]
    needs = [dict(so_the=x["so_the"], ten=x["ten"], bo_sung=x["so_the"] in review["bo_sung_nghi_doc_sai"]) for x in manifest if x["can_xac_nhan"]]
    data = dict(ngay_kiem_tra=review["ngay"], sha256_json_goc=digest, chi_tiet=manifest,
                so_chua_ro=len(unknown), so_bo_sung=len(review["bo_sung_nghi_doc_sai"]))
    (ra / "kiem_tra_bang_mat.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
    (ra / "mau_tra_loi.txt").write_text("# 1=có khung, 0=không khung, ?=chưa rõ. Giữ nguyên số thẻ.\n"+"".join(f"{x['so_the']}=? # {x['ten']}{' (bổ sung nghi đọc sai)' if x['bo_sung'] else ''}\n" for x in needs))
    payload = json.dumps(dict(sha256=digest, the=needs), ensure_ascii=False).replace("<", "\\u003c")
    page = HTML.replace("__CARDS__", "\n".join(articles)).replace("__DATA__", payload)
    (ra / "xac_nhan_khung.html").write_text(page)
    lines = ["# Kiểm tra ảnh khung ngày 07/11/2026", "", "Đã xem 117 cặp ảnh trước/sau và ảnh nguồn; phóng to riêng 26 thẻ đổi kết luận.",
             "Nhận xét dưới đây của trợ lý chưa phải nhãn do người dùng xác nhận. Kết quả máy và thư viện mẫu được giữ nguyên.", "",
             "- 13/42 thẻ chưa rõ nhìn thấy sao khung; 29/42 không thấy hàng sao khung.",
             "- #95 Indris được máy báo có khung, nhưng các vị trí khớp mẫu nằm trên tóc trắng. Đã thêm thẻ này vào bảng để xác nhận riêng.",
             "- #86 Carolina và #88 Vala có thân thẻ/viền trong ảnh nguồn đủ để đối chiếu bằng mắt; máy thất bại tìm biên. Ảnh sau của hai thẻ là ảnh tạm, không được coi là đã căn đúng biên.",
             "- Với 115 ảnh đã căn, đối chiếu bằng mắt thấy sao/viền của chính thẻ vẫn nằm trong ảnh. Một số thẻ có vệt bóng hàng trên gần chóp khung; việc có nền đệm sạch không tự chứng minh toàn bộ vùng bên trong sạch.",
             "- 26 thay đổi gồm 4 thẻ chuyển sang có khung và nhìn thấy sao, 1 trường hợp nghi nhận nhầm (#95), 7 thẻ về chưa rõ dù vẫn thấy sao và 14 thẻ về chưa rõ không thấy sao.", "",
             "## 42 thẻ chờ xác nhận", "", "| Số | Tên | Quan sát của trợ lý |", "|---:|---|---|"]
    lines += [f"| {x['so_the']} | {x['ten']} | {'Thấy sao khung' if x['sao_khung_nhin_thay'] else 'Không thấy hàng sao khung'} |" for x in unknown]
    lines += ["", "Bổ sung: **#95 Indris** — nghi nhận nhầm tóc thành sao.", "", "## 26 thẻ đổi kết luận", "", "| Số | Tên | Trước → sau (máy) | Nhận xét |", "|---:|---|---|---|"]
    lines += [f"| {x['so_the']} | {x['ten']} | {chu(x['truoc'])} → {chu(x['sau'])} | {x['nhan_xet']} |" for x in manifest if x["doi_ket_qua"]]
    (ra / "ket_qua_kiem_tra.md").write_text("\n".join(lines)+"\n")
    return data


HTML = r'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xác nhận khung · 42 thẻ + Indris</title><style>
*{box-sizing:border-box}body{margin:0;background:#f0f3f7;color:#172332;font:16px/1.5 system-ui,sans-serif}header,main{max-width:1280px;margin:auto;padding:20px}h1{font-size:28px;margin:4px 0 12px}h2{font-size:20px;margin:0 0 8px}p{margin:8px 0}a{color:#1652a1}button,select,input,textarea{font:inherit}button{cursor:pointer;padding:9px 13px;border:1px solid #8192a4;border-radius:7px;background:white;color:#172332}button:hover{background:#e5eefc}select,input{max-width:100%;padding:8px;border:1px solid #8192a4;border-radius:6px;background:white;color:#172332}.intro,.toolbar{background:white;border:1px solid #cdd6e0;border-radius:10px;padding:16px}.toolbar{margin-top:16px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}.controls{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}article{background:white;border:1px solid #cdd6e0;border-radius:10px;padding:16px;min-width:0}article[hidden]{display:none}article.done{border-color:#218354;box-shadow:inset 0 3px #218354}.pair{display:flex;gap:14px;justify-content:center;align-items:flex-start}.pair img{width:130px;height:205px;display:block;object-fit:contain}figure{margin:8px 0;min-width:0}figcaption{font-size:13px;color:#425770;max-width:145px}.context{display:block;max-width:100%;max-height:470px;object-fit:contain}.note{font-size:14px;color:#3a4c61}.machine{font-size:14px;color:#425770}.warn{display:block;color:#934218;background:#fff0df;padding:8px;border-radius:5px}summary{cursor:pointer;color:#1652a1;padding:8px 0}.answer{display:block;margin-top:12px;padding-top:12px;border-top:1px solid #d5dee8}.answer select{display:block;width:100%;margin-top:6px}textarea{display:block;width:100%;height:230px;margin-top:12px;padding:10px}#progress{font-weight:650}#message{min-height:24px;font-size:14px}.legend{font-size:14px}.counts{font-weight:600}footer{padding:20px;color:#425770}@media(max-width:380px){header,main{padding:10px}.grid{grid-template-columns:1fr}.pair{gap:8px}.pair img{width:120px;height:auto}}
</style></head><body><header><h1>Xác nhận khung tướng</h1><div class="intro">
<p><b>42 thẻ máy chưa rõ + #95 Indris cần kiểm tra thêm.</b> Giữ nguyên số và tên từ phiên 15 ảnh ngày 30/10/2026. Kiểm tra bằng mắt ngày 07/11/2026.</p>
<p>Đã đối chiếu 117 cặp ảnh, ưu tiên phóng to 26 thẻ đổi kết luận. Trong 42 thẻ chưa rõ, <b>13 thẻ thấy sao</b>, <b>29 thẻ không thấy hàng sao khung</b>. Các nhận xét là quan sát của trợ lý; mọi ô xác nhận ban đầu đều trống.</p>
<p class="warn"><b>#95 Indris:</b> máy báo có khung nhưng mẫu khớp trên tóc trắng. Thẻ này được thêm riêng ngoài danh sách 42. Carolina #86 và Vala #88 có ảnh nguồn xem được; máy chưa tìm được biên nên ảnh sau vẫn là ảnh tạm.</p>
<p class="legend">Chọn <b>1 — Có khung</b>, <b>0 — Không khung</b> hoặc <b>? — Chưa rõ</b>. Mở “Ảnh nguồn và vùng sao” để kiểm tra khi cần. Sao trên mũ/đầu nhân vật (ví dụ Scarlita) có thể khác sao khung.</p>
<div class="controls"><a href="ket_qua_kiem_tra.md">Biên bản kiểm tra và danh sách 26 thay đổi</a><a href="mau_tra_loi.txt">Mẫu trả lời bằng văn bản</a></div>
<p>Chọn xong, dùng “Lấy câu trả lời” rồi gửi phần văn bản bên dưới vào chat. Bạn có thể gửi từng nhóm. Bảng không tự gửi dữ liệu và không thay kết quả máy.</p>
<div class="controls"><button id="answers" type="button">Lấy câu trả lời</button><button id="txt" type="button">Tải câu trả lời .txt</button><button id="json" type="button">Tải xác nhận .json</button></div>
<p id="progress" aria-live="polite"></p><p id="message" aria-live="polite"></p><textarea id="output" style="display:none" aria-label="Văn bản trả lời để gửi vào chat" placeholder="Câu trả lời của bạn sẽ hiện ở đây khi bấm Lấy câu trả lời."></textarea>
</div><div class="toolbar"><label>Hiển thị <select id="filter"><option value="needs">42 chưa rõ + Indris (43)</option><option value="unknown">42 thẻ chưa rõ</option><option value="stars">13 thẻ chưa rõ có sao nhìn thấy</option><option value="plain">29 thẻ chưa rõ không thấy hàng sao</option><option value="changed">26 thẻ đổi kết luận</option><option value="all">Tất cả 117 thẻ đã kiểm tra</option></select></label><label>Tìm <input id="search" placeholder="Số thẻ hoặc tên" type="search"></label><span id="visible"></span></div></header>
<main><div class="grid">__CARDS__</div></main><footer>Nhận xét bằng mắt và nhãn người dùng được lưu riêng. Bản HTML này chỉ lưu lựa chọn trên trình duyệt khi được hỗ trợ; tải tệp hoặc gửi văn bản vào chat để chuyển kết quả.</footer>
<script type="application/json" id="dataset">__DATA__</script><script>
'use strict';
const data=JSON.parse(document.getElementById('dataset').textContent);
const key='afk-xac-nhan-khung-'+data.sha256;
const decisions=Array.from(document.querySelectorAll('.decision'));
const cards=Array.from(document.querySelectorAll('article'));
const message=document.getElementById('message');
let storageOK=true;
function values(){return Object.fromEntries(decisions.map(el=>[el.dataset.id,el.value]));}
function progress(){const selected=decisions.filter(el=>el.value!=='');const known=selected.filter(el=>el.value!=='?');document.getElementById('progress').textContent=`Đã chọn ${selected.length}/43; xác nhận có/không ${known.length}; chưa rõ ${selected.length-known.length}.`;decisions.forEach(el=>el.closest('article').classList.toggle('done',el.value!==''));}
try{const saved=JSON.parse(localStorage.getItem(key)||'{}');decisions.forEach(el=>{if(['1','0','?'].includes(saved[el.dataset.id]))el.value=saved[el.dataset.id];});}catch(e){storageOK=false;}
message.textContent=storageOK?'Lựa chọn được giữ trên trình duyệt này. Bạn vẫn cần gửi văn bản hoặc tệp vào chat.':'Trình duyệt không lưu được lựa chọn lâu dài. Hãy tải tệp hoặc sao chép câu trả lời trước khi đóng bảng.';
decisions.forEach(el=>el.addEventListener('change',()=>{try{localStorage.setItem(key,JSON.stringify(values()));}catch(e){storageOK=false;message.textContent='Không lưu được lựa chọn trên trình duyệt; hãy lấy câu trả lời và gửi vào chat.';}progress();}));
function filter(){const mode=document.getElementById('filter').value,q=document.getElementById('search').value.trim().toLocaleLowerCase('vi');let count=0;cards.forEach(el=>{const d=el.dataset;const group=mode==='all'||mode==='needs'&&d.needs==='1'||mode==='unknown'&&d.unknown==='1'||mode==='stars'&&d.unknown==='1'&&d.star==='1'||mode==='plain'&&d.unknown==='1'&&d.star==='0'||mode==='changed'&&d.changed==='1';el.hidden=!(group&&d.search.includes(q));if(!el.hidden)count++;});document.getElementById('visible').textContent=`${count} thẻ`;}
document.getElementById('filter').addEventListener('change',filter);document.getElementById('search').addEventListener('input',filter);
function textAnswers(){const v=values();return data.the.filter(t=>v[t.so_the]!=='').map(t=>`${t.so_the}=${v[t.so_the]} # ${t.ten}`).join('\n');}
function exportData(){const v=values();return {loai:'xac_nhan_khung_nguoi_dung',sha256_json_goc:data.sha256,thoi_diem_xuat:new Date().toISOString(),chi_tiet:data.the.filter(t=>v[t.so_the]!=='').map(t=>({so_the:t.so_the,ten:t.ten,khung:v[t.so_the]==='?'?null:Number(v[t.so_the]),tra_loi:v[t.so_the]}))};}
function download(name,text,type){const link=document.createElement('a');const url=URL.createObjectURL(new Blob([text],{type}));link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
document.getElementById('answers').addEventListener('click',()=>{const text=textAnswers(),out=document.getElementById('output');out.value=text;out.style.display='block';out.focus();out.select();message.textContent=text?'Câu trả lời đã hiện trong ô. Sao chép và gửi vào chat.':'Chưa có lựa chọn; hãy xác nhận ít nhất một thẻ.';});
document.getElementById('txt').addEventListener('click',()=>{if(!textAnswers()){message.textContent='Chưa có lựa chọn để tải.';return;}download('xac_nhan_khung.txt',textAnswers()+'\n','text/plain;charset=utf-8');});
document.getElementById('json').addEventListener('click',()=>{if(!exportData().chi_tiet.length){message.textContent='Chưa có lựa chọn để tải.';return;}download('xac_nhan_khung.json',JSON.stringify(exportData(),null,2)+'\n','application/json');});
progress();filter();
</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bao-cao", type=Path, required=True)
    parser.add_argument("--anh-goc", type=Path, required=True)
    parser.add_argument("--danh-gia", type=Path, required=True)
    parser.add_argument("--ra", type=Path, required=True)
    args = parser.parse_args()
    data = tao_bang(args.bao_cao, args.anh_goc, args.danh_gia, args.ra)
    print(f"Đã xuất {len(data['chi_tiet'])} thẻ kiểm tra; {data['so_chua_ro']} chưa rõ + {data['so_bo_sung']} bổ sung.")


if __name__ == "__main__":
    main()
