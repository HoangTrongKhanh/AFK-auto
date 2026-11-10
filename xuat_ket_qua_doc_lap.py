"""Xuất kết quả kiểm chứng sau khi đã có nhãn; bảng gán nhãn gốc tiếp tục ẩn dự đoán."""
import argparse
from html import escape
import json
from pathlib import Path
from kiem_chung_doc_lap import seal_check


def xuat(folder):
    seal=seal_check(folder);result=json.loads((folder/'ket_qua.json').read_text())
    protocol=json.loads((folder/'protocol.json').read_text());dataset=json.loads((folder/'dataset.json').read_text())
    refs={r['id']:r for r in dataset['items']};show={1:'Có khung',0:'Không khung',None:'Chưa rõ'}
    counts={k:{p:0 for p in (0,1,None)} for k in (0,1)};cards=[]
    for r in result['chi_tiet']:
        n=r['id'];status='unknown' if r['prediction'] is None else 'correct' if r['reference']==r['prediction'] else 'wrong'
        counts[r['reference']][r['prediction']]+=1
        word={'unknown':'Máy chưa rõ','correct':'Đúng','wrong':'SAI'}[status]
        cards.append(f'''<article class="{status}" data-status="{status}"><h3>#{n:03d} · {word}</h3><div class="pair"><img src="the/{n:03d}.png" alt="Thẻ {n}"><div><p>Bạn xác nhận:<br><b>{show[r['reference']]}</b></p><p>Máy đã dự đoán:<br><b>{show[r['prediction']]}</b></p></div></div><details><summary>Ảnh nguồn</summary><img class="context" src="the/{n:03d}_nguon.png"><a href="anh_goc/{refs[n]['source_image']}" target="_blank">Mở toàn ảnh gốc</a></details></article>''')
    decided=result['dung']+result['sai'];total=result['so_nhan_ro']
    decisions=json.loads((folder/'predictions_sealed.json').read_text())
    decisions={r['id']:r for r in decisions}
    issues=[]
    for row in result['chi_tiet']:
        if row['prediction'] is not None and row['prediction']!=row['reference']:
            d=decisions[row['id']];point=d.get('diem_sao')
            note=f" Điểm khớp sao {point:.3f}." if point is not None else ''
            issues.append(f"<p class='note'><b>Lỗi #{row['id']}:</b> bạn xác nhận {show[row['reference']]}, máy dự đoán {show[row['prediction']]}.{note} Lý do máy: {escape(d['ly_do'])}. Đây là lỗi phát hiện sau kiểm chứng; dự đoán gốc được giữ để đối chiếu.</p>")
    error_notes=''.join(issues)
    page_count=len(list((folder/'anh_goc').glob('[0-9][0-9].png')))
    coverage_text=f"{result['coverage']:.0%}" if result['coverage'] is not None else 'chưa có nhãn'
    accuracy_text=f"{result['selective_accuracy']:.1%}" if result['selective_accuracy'] is not None else 'chưa có kết luận'
    overall_text=f"{result['dung']/total:.0%}" if total else 'chưa có nhãn'
    rows=''.join(f"<tr><td>{show[k]} ({sum(counts[k].values())})</td><td>{counts[k][1]}</td><td>{counts[k][0]}</td><td>{counts[k][None]}</td></tr>" for k in (1,0))
    html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kết quả kiểm chứng độc lập</title><style>*{box-sizing:border-box}body{font:16px/1.5 system-ui;background:#edf2f7;color:#17283b;margin:0}main{max-width:1240px;margin:auto;padding:22px}h1{font-size:28px}h2{font-size:22px}.box,article{padding:18px;background:white;border:1px solid #c9d6e2;border-radius:9px;margin:14px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:15px}.grid article{margin:0}.pair{display:flex;gap:18px;align-items:center}.pair img{width:130px;height:205px;object-fit:contain}.context{display:block;max-width:100%;max-height:420px}.wrong{border-top:5px solid #bd3c3c}.unknown{border-top:5px solid #c18a22}.correct{border-top:5px solid #368258}table{border-collapse:collapse;width:100%}td,th{text-align:left;border-bottom:1px solid #d2dce8;padding:9px}a,summary{color:#175ba0}summary{cursor:pointer;padding:8px 0}select{font:inherit;padding:8px}.note{background:#fff0d6;padding:12px;border-radius:6px}code{word-break:break-all}article[hidden]{display:none}@media(max-width:400px){main{padding:10px}.grid{grid-template-columns:1fr}}</style><main><h1>Kiểm chứng trên tài khoản khác</h1><div class="box"><p><b>'''+str(result['so_nhan_ro'])+''' nhãn rõ do bạn xác nhận · '''+str(result['dung'])+''' đúng · '''+str(result['sai'])+''' sai · '''+str(result['chua_ro'])+''' máy chưa rõ.</b></p><p>Bộ ảnh: <code>'''+escape(seal['dataset_id'])+'''</code>. Thu '''+str(page_count)+''' ảnh trên tài khoản khác, cùng thiết bị '''+escape(protocol['device'])+'''. Chọn ngẫu nhiên '''+str(dataset['sample_count'])+''' nhóm ảnh mặt trước khi dự đoán; bộ cắt đề xuất '''+str(dataset['group_count'])+''' nhóm. Các nhóm vẫn cần được đối chiếu nếu nghi gom nhầm.</p><p>Mô hình và logic đã cố định trước khi chụp. Dự đoán được niêm phong trước khi bạn gán nhãn; bảng nhãn không hiển thị kết quả máy. Ảnh của bộ này được bảo vệ khỏi tập học bằng mã ảnh và mã ảnh nguồn.</p>'''+error_notes+'''<p>Độ phủ kết luận: '''+coverage_text+''' ('''+str(decided)+'/'+str(total)+'''). Trong các thẻ đã kết luận, đúng '''+accuracy_text+''' ('''+str(result['dung'])+'/'+str(decided)+'''); tính trên toàn bộ '''+str(total)+''' thẻ thì đúng '''+overall_text+'''. Chưa đánh giá thiết bị khác hoặc độ phủ toàn bộ danh sách; chỉ đo các thẻ bộ cắt đã đề xuất.</p></div><div class="box"><h2>Theo nhãn người dùng</h2><table><tr><th>Nhãn chuẩn</th><th>Máy có khung</th><th>Máy không khung</th><th>Máy chưa rõ</th></tr>'''+rows+'''</table><p><a href="ket_qua.json">Số liệu từng thẻ</a> · <a href="seal.json">Mã niêm phong</a> · <a href="protocol.json">Protocol trước khi chụp</a> · <a href="labels_user.json">Nhãn người dùng</a></p><label>Lọc <select id="filter"><option value="all">Tất cả</option><option value="wrong">Đọc sai</option><option value="unknown">Máy chưa rõ</option><option value="correct">Đúng</option></select></label></div><div class="grid">'''+''.join(cards)+'''</div><div class="box"><p>SHA-256 mô hình: <code>'''+protocol['model_sha256']+'''</code></p><p>SHA-256 nhãn tham chiếu: <code>'''+result['reference_labels_sha256']+'''</code>. Các lần sửa nhãn được giữ trong labels_history; không thay dự đoán đã niêm phong.</p></div></main><script>document.getElementById('filter').onchange=e=>document.querySelectorAll('article').forEach(x=>x.hidden=e.target.value!=='all'&&x.dataset.status!==e.target.value);</script></html>'''
    if protocol.get('excluded_dataset'):
        old=escape(protocol['excluded_dataset'])
        note=f'<p class="note">Vòng mới dùng quy tắc v2, cùng tài khoản kiểm tra trên Tab S7. Đã loại các nhóm thuộc bộ {old} trước khi chọn 40/71 nhóm còn lại. Không thêm tài khoản hoặc thiết bị mới ở vòng này.</p>'
        html=html.replace('</h1>','</h1>'+note,1)
        html=html.replace('bộ cắt đề xuất '+str(dataset['group_count'])+' nhóm','còn '+str(dataset['group_count'])+' nhóm sau loại bộ cũ')
    (folder/'ket_qua.html').write_text(html)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);a=p.parse_args();xuat(a.folder)
