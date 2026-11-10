"""Đối chiếu một-một với danh sách chuẩn từ màn hình khác, tách khỏi bộ đọc khung."""
from collections import Counter


def doi_chieu(records,observed_groups):
    owned=[r for r in records if r['owned']]
    if len({r['id'] for r in records})!=len(records):raise ValueError('Trùng ô nguồn')
    assigned=[r['confirmed_group'] for r in owned if r.get('confirmed_group') is not None]
    counts=Counter(assigned);observed=set(observed_groups)
    missing=observed-set(assigned);outside=set(assigned)-observed
    duplicate={n:c for n,c in counts.items() if c>1}
    unresolved=[r['id'] for r in owned if r.get('confirmed_group') is None]
    complete=not (missing or outside or duplicate or unresolved) and len(owned)==len(observed)
    return dict(so_o_nguon=len(records),so_chua_so_huu=len(records)-len(owned),so_da_so_huu=len(owned),
                so_nhom_hoi_truong=len(observed),so_doi_chieu_mot_mot=len(counts),
                chua_doi_chieu=unresolved,nhom_chua_co_nguon=sorted(missing),nhom_ngoai_phien=sorted(outside),
                nhom_bi_gan_trung=duplicate,thu_du_trong_phien=complete,
                gioi_han='Đúng cho tài khoản, thời điểm và ảnh nguồn đã đối chiếu; không suy rộng thiết bị hoặc danh sách ngắn chưa kiểm tra.')
