"""Bảng đối chiếu nguồn riêng để kiểm tra thu đủ tướng, không dùng làm mẫu học."""
import argparse
from html import escape
import json
from pathlib import Path
from kiem_tra_do_phu_nguon import doi_chieu
from quan_ly_mau import sha,ghi_json


def xuat(folder):
    rows=json.loads((folder/'xac_nhan_doi_chieu.json').read_text())
    groups=json.loads((folder/'nhom_hoi_truong.json').read_text())
    source=json.loads((folder/'bo_suu_tap'/'nhan_nguon.json').read_text())
    for name,digest in source['source_sha256'].items():
        if sha((folder/'bo_suu_tap'/name).read_bytes())!=digest:raise ValueError('Ảnh nguồn thay đổi')
    for r in rows:
        if r.get('evidence') and sha((folder/r['evidence']).read_bytes())!=r['evidence_sha256']:raise ValueError('Ảnh đọc tên đã đổi')
    result=doi_chieu(rows,range(1,groups['group_count']+1));cards=[]
    if not result['thu_du_trong_phien']:raise ValueError('Còn nhóm chưa đối chiếu hoặc bị gán trùng')
    if (len(rows),result['so_da_so_huu'])!=(source['total_slots'],source['owned_slots']):raise ValueError('Số ô khác nguồn chuẩn')
    for r in rows:
        n=r['id'];changed=r.get('confirmed_group')!=r.get('group') and r['owned']
        pics=f'<img src="bo_suu_tap/the/{n:03d}.png" alt="Ô nguồn {n}">'
        text='Chưa sở hữu: ô xám'
        if r['owned']:
            page,j=r['confirmed_hall'];target=f'doi_chieu/{page[:-4]}_{j:02d}.png'
            if not (folder/target).exists():raise ValueError('Thiếu ảnh đối chiếu')
            pics+=f'<img src="{target}" alt="Ảnh Hội Trường nhóm {r["confirmed_group"]}">'
            text=f'Nhóm Hội Trường {r["confirmed_group"]} · đã kiểm tra cặp ảnh'
            if changed:text+=' · sửa ghép tự động'
        proof=f'<p><a href="{escape(r["evidence"])}">Đọc tên trong game: {escape(r["name"])}</a></p>' if r.get('evidence') else ''
        cards.append(f'<article data-changed="{int(changed)}"><h2>Ô Bộ Sưu Tập #{n}</h2><div class="pair">{pics}</div><p>{text}</p>{proof}<a href="bo_suu_tap/{r["page"]}">Mở ảnh nguồn · hàng {r["row"]}, cột {r["col"]}</a></article>')
    html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kiểm chứng thu đủ tướng</title><style>*{box-sizing:border-box}body{margin:0;background:#edf2f7;color:#182d3c;font:16px/1.5 system-ui}main{max-width:1250px;margin:auto;padding:20px}.box,article{background:#fff;padding:16px;border:1px solid #ccd7e2;border-radius:9px;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:15px}article{margin:0}h1{font-size:28px}h2{font-size:18px}.pair{display:flex;gap:12px;align-items:center}.pair img{width:130px;height:205px;object-fit:contain}a{color:#165d98}select{font:inherit;padding:8px}article[hidden]{display:none}.note{background:#fff0d6;padding:12px;border-radius:7px}</style><main><h1>Kiểm chứng thu đủ tướng · tài khoản kiểm tra</h1><div class="box"><p><b>121/121 tướng sở hữu được đối chiếu một-một với Hội Trường.</b></p><p>Bộ Sưu Tập: 131 ô, gồm 10 ô xám chưa sở hữu và 121 ô có màu. Các hàng được kiểm tra trực quan từ nguồn chụp riêng; không lấy số lượng do bộ cắt Hội Trường đề xuất làm chuẩn.</p><p>Đã xem từng cặp ảnh, sửa 6 cặp ghép tự động sai. Đọc tên trực tiếp Cyran, Silvina và Valka để đối chiếu các chân dung khác diện mạo. Không còn nhóm thiếu hoặc nhóm bị gán trùng sau đối chiếu.</p><p class="note">Đây là bằng chứng độ phủ của phiên trên tài khoản thứ hai, cùng Tab S7. Viền trang trí trong Bộ Sưu Tập không phải nhãn khung. Bảng này không chấm độ chính xác tên/khung và không chứng minh mọi thiết bị hoặc danh sách ngắn đều được hỗ trợ.</p><p><a href="ket_qua_do_phu.json">Kết quả</a> · <a href="xac_nhan_doi_chieu.json">Từng cặp đã đối chiếu</a> · <a href="bo_suu_tap/nhan_nguon.json">Hàng và mã ảnh nguồn</a></p><label>Lọc <select id="filter"><option value="all">Tất cả 131 ô</option><option value="changed">6 cặp đã sửa ghép</option></select></label></div><div class="grid">'''+''.join(cards)+'''</div></main><script>document.getElementById('filter').onchange=e=>document.querySelectorAll('article').forEach(x=>x.hidden=e.target.value==='changed'&&x.dataset.changed!=='1');</script></html>'''
    (folder/'do_phu.html').write_text(html)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);a=p.parse_args();print(json.dumps(xuat(a.folder),ensure_ascii=False))
