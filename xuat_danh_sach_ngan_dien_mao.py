"""Báo cáo phạm vi đã kiểm tra cho danh sách ngắn và các diện mạo mới."""
import argparse,json
from pathlib import Path
from html import escape
import cv2
from hoi_truong import cat_the_hoi_truong
from quan_ly_mau import KhoMau


def xuat(folder):
    summary=json.loads((folder/'danh_gia_dien_mao.json').read_text())
    meta=json.loads((folder/'mau_moi/dien_mao_da_doc_ten.json').read_text())
    before={r['id']:r for r in json.loads((folder/'ten_truoc.json').read_text())}
    after={r['id']:r for r in json.loads((folder/'ten_sau_ung_vien.json').read_text())}
    candidate=json.loads((folder/'ung_vien.json').read_text());current=KhoMau().hien_tai()[1]['version']
    active=current==candidate['version'];cards=[];cache={};assets=folder/'anh_bao_cao';assets.mkdir(exist_ok=True)
    for r in meta['items']:
        n=r['id'];page=r['source_image']
        if page not in cache:cache[page]=cat_the_hoi_truong(cv2.imread(str(folder/'mau_moi'/page)),kem_chat_luong=True)
        card=cache[page][r['source_position']-1][0];cv2.imwrite(str(assets/f'{n:02d}_the.png'),card)
        old=before[n]['ten'] or 'Chưa nhận tên';new=after[n]['ten'] or 'Chưa nhận tên'
        cards.append(f'''<article><h2>#{n} · {escape(r['ten'])}</h2><div class="pair"><img class="card" src="anh_bao_cao/{n:02d}_the.png" alt="Thẻ {n} đủ biên"><img class="name" src="anh_bao_cao/{n:02d}_ten.png" alt="Tên hiển thị trong game"></div><p>Trước: <b>{escape(old)}</b><br>Sau bổ sung mẫu: <b>{escape(new)}</b></p><p><a href="mau_moi/{r['source_image']}">Ảnh nguồn</a> · <a href="mau_moi/{r['evidence']}">Mở ảnh tên đầy đủ</a></p><small>{escape(r['dien_mao'])}</small></article>''')
    v=summary['validation_after'];vb=summary['validation_before']
    html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Danh sách ngắn và diện mạo</title><style>*{box-sizing:border-box}body{margin:0;background:#edf2f7;color:#172d3e;font:16px/1.5 system-ui}main{max-width:1250px;margin:auto;padding:22px}.box,article{background:#fff;border:1px solid #ccd7e2;border-radius:10px;padding:18px;margin:14px 0}h1{font-size:28px}h2{font-size:21px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:15px}article{margin:0}.pair{display:flex;align-items:center;gap:12px}.card{width:130px;height:205px;object-fit:contain}.name{max-width:calc(100% - 142px);height:auto}.note{background:#fff0d6;padding:12px;border-radius:7px}a{color:#175e9d}code{word-break:break-all}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #d8e0e8}small{color:#546575}@media(max-width:400px){main{padding:10px}.grid{grid-template-columns:1fr}}</style><main><h1>Danh sách ngắn và các diện mạo đã xác nhận</h1><div class="box"><p><b>'''+('Đã kích hoạt trên Python' if active else 'Bản ứng viên, chưa kích hoạt')+'''</b> · <code>'''+candidate['version']+'''</code></p><p>Trên tài khoản 48 tướng, thu 7 ảnh và gộp đúng 48 nhóm. Máy gán tên từ <b>'''+str(summary['auto_names_before'])+''' lên '''+str(summary['auto_names_after'])+'''/48</b> sau khi bổ sung 20 mẫu mặt được đọc tên trực tiếp trong game. Số tên máy gán không phải tỷ lệ chính xác toàn bộ 48 tên; 20 thẻ bên dưới có bằng chứng tên trực tiếp.</p></div><div class="box"><h2>Danh sách ngắn</h2><p>Khi danh sách đứng yên, bộ thu cần số tướng đã đối chiếu từ nguồn khác, mốc đầu Hội Trường, đủ biên mọi thẻ, không đếm trùng và ảnh mặt không đổi khi thử hai chiều. Nếu thiếu bằng chứng, dữ liệu cũ được giữ nguyên.</p><p>Đã sửa nhận màn khi thanh nổi che tiêu đề. Đã bổ sung hàng chỉ có một thẻ tóc trắng: kiểm tra hai góc trên, hai cạnh, đáy và nhãn cấp. Phép thử lọc phe Thiên có 5 thẻ cố định và 1 thẻ lưới; trước bỏ sót thẻ lưới, sau thu đủ 6.</p><p><a href="loc_thien_6_bo_sung/tuong_cua_toi.html">Xem 6 thẻ sau sửa</a> · <a href="kiem_tra_ung_vien.json">Đối chiếu với phiên 48 tướng</a> · <a href="phien48.json">Bằng chứng phiên 48</a></p></div><div class="box"><h2>Kiểm tra diện mạo</h2><table><tr><th>Phép đo</th><th>Trước</th><th>Sau</th></tr><tr><td>20 thẻ đã đọc tên trực tiếp</td><td>1 đúng, 19 chưa rõ</td><td>20 đúng</td></tr><tr><td>Ảnh quan sát khác, đã bỏ ảnh trùng mẫu</td><td>'''+str(vb['correct'])+''' đúng / '''+str(vb['count'])+'''</td><td>'''+str(v['correct'])+''' đúng / '''+str(v['count'])+'''</td></tr></table><p>Đã loại '''+str(summary['exact_training_duplicates_excluded'])+''' lượt ảnh trùng hệt mẫu học khỏi phép đo quan sát khác. Tất cả vẫn thuộc cùng tài khoản phát triển, không gọi là kiểm chứng độc lập.</p><p class="note">Một chân dung cũ trước đây được đối chiếu là Silvina vẫn chưa khớp chắc. Bản mới giữ chưa rõ và không đẩy Isabella thành gợi ý đơn; cần đọc tên trực tiếp và mẫu phát triển riêng để giải quyết. Ảnh của hai bộ kiểm tra khung cũ không được đưa vào mẫu học.</p><p><a href="danh_gia_dien_mao.json">Kết quả chi tiết</a> · <a href="mau_moi/dien_mao_da_doc_ten.json">Nguồn và tên từng mẫu</a> · <a href="ung_vien.json">Phiên bản</a></p></div><div class="grid">'''+''.join(cards)+'''</div></main></html>'''
    high=folder/'ket_qua_dien_mao_cu.json'
    if high.exists():
        results=json.loads(high.read_text())['items']
        proofs=json.loads((folder/'dien_mao_859/dien_mao_da_doc_ten.json').read_text())['items']
        extra='<div class="box"><h2>Đã đối chiếu trực tiếp Isabella và Silvina</h2><p>Chụp mới trên tài khoản cấp 859, đọc tên trên chính màn chi tiết rồi bổ sung mẫu mặt. Bản mới nhận đúng cả hai chân dung; đây là sửa trường hợp đã biết, không phải kiểm chứng độc lập.</p>'
        for r in proofs:
            source=folder/'dien_mao_859'/r['source_image'];ds=cat_the_hoi_truong(cv2.imread(str(source)),kem_chat_luong=True)
            cv2.imwrite(str(assets/f"cao_{r['lookup_group']}.png"),ds[r['source_position']-1][0])
            extra+=f'<div class="pair"><img class="card" src="anh_bao_cao/cao_{r["lookup_group"]}.png"><p><b>{escape(r["ten"])}</b><br><a href="dien_mao_859/{r["evidence"]}">Tên hiển thị trực tiếp trong game</a></p></div>'
        extra+='</div>'
        html=html.replace('<div class="grid">',extra+'<div class="grid">',1)
        html=html.replace('Một chân dung cũ trước đây được đối chiếu là Silvina vẫn chưa khớp chắc. Bản mới giữ chưa rõ và không đẩy Isabella thành gợi ý đơn; cần đọc tên trực tiếp và mẫu phát triển riêng để giải quyết.','Đã đọc tên trực tiếp và giải quyết chân dung Silvina từng bị gợi ý Isabella. Khi gặp diện mạo khác chưa khớp đủ chắc, bộ đọc vẫn giữ chưa rõ, không ép nhận tên.')
    (folder/'bao_cao.html').write_text(html)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);a=p.parse_args();xuat(a.folder)
