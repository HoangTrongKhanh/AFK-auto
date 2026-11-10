"""Giải thích tên chưa rõ; không biến ứng viên yếu thành tên xác nhận."""

def danh_gia_ten(scores,assigned,*,trong_doi=False,hon_nhi=.04):
    if not scores:return dict(trang_thai='chua_ro',ly_do='khong_co_mau',ung_vien_tham_khao=[])
    d1,t1=scores[0];d2=scores[1][0] if len(scores)>1 else 0.
    if assigned is not None:reason='mat_da_khop_mau';state='da_nhan'
    elif trong_doi:reason='the_phu_xanh_chua_du_bang_chung';state='chua_ro'
    elif d1<.85:reason='can_mau_dien_mao_da_xac_nhan';state='chua_ro'
    elif d1-d2<hon_nhi:reason='hai_ten_qua_gan_nhau';state='chua_ro'
    else:reason='ten_da_gan_cho_the_khac';state='chua_ro'
    return dict(trang_thai=state,ly_do=reason,diem_cao_nhat=float(d1),chenh_lech=float(d1-d2),
                ung_vien_tham_khao=[dict(ten=t,diem=float(d)) for d,t in scores[:3]])


def giai_thich_ten(detail):
    return {'can_mau_dien_mao_da_xac_nhan':'Ảnh mặt chưa khớp đủ chắc. Cần bổ sung mẫu diện mạo đã xác nhận; các tên bên cạnh chỉ để đối chiếu.',
            'hai_ten_qua_gan_nhau':'Hai tên có điểm quá gần nhau; cần xác nhận trực tiếp.',
            'ten_da_gan_cho_the_khac':'Tên ứng viên đã được gán cho thẻ khác; cần kiểm tra gộp thẻ hoặc diện mạo.',
            'the_phu_xanh_chua_du_bang_chung':'Thẻ bị phủ xanh; chưa đủ bằng chứng nhận tên.',
            'khong_co_mau':'Chưa có mẫu tên để đối chiếu.',
            'mat_da_khop_mau':'Ảnh mặt khớp mẫu tên.'}.get((detail or {}).get('ly_do'),'')
