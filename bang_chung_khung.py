"""Bằng chứng hình học/màu của khung, không nhận tên hoặc tra nhãn cá nhân."""
import cv2
import numpy as np


def bang_chung(the,quality):
    a,b,c,d=quality['bien_chuan']
    obj=cv2.resize(the[b:d,a:c],(96,144),interpolation=cv2.INTER_AREA)
    hsv=cv2.cvtColor(obj,cv2.COLOR_BGR2HSV)
    hue,sat,val=[hsv[:,:,i] for i in range(3)]
    gold=(hue>=10)&(hue<=38)&(sat>=100)&(val>=140)
    bg=the[0,0].astype(float)
    near_bg=np.linalg.norm(obj.astype(float)-bg,axis=2)<25
    side_gold=float(np.r_[gold[25:120,:8].ravel(),gold[25:120,-8:].ravel()].mean())
    side_bg=float(np.r_[near_bg[25:120,:4].ravel(),near_bg[25:120,-4:].ravel()].mean())
    corner_gold=float(max(gold[:22,:24].mean(),gold[:22,-24:].mean()))
    cyan=((hue[:44]>=75)&(hue[:44]<=115)&(sat[:44]>=25)&(val[:44]>=150)).astype(np.uint8)
    _,_,stats,_=cv2.connectedComponentsWithStats(cyan,8)
    pieces=[(int(x),int(y),int(w),int(h),int(area)) for x,y,w,h,area in stats[1:]
            if 3<=w<=25 and 3<=h<=25 and area>=5]
    return dict(vang_canh=side_gold,nen_canh=side_bg,vang_goc=corner_gold,
                manh_sao_xanh=len(pieces),dien_tich_sao_xanh=sum(x[4] for x in pieces),
                manh_xanh=pieces)


def quyet_dinh_v2(the,quality,star,learned):
    evidence=bang_chung(the,quality)
    blue_cap=(evidence['dien_tich_sao_xanh']>=20 and evidence['vang_goc']>=.10)
    ornate=(evidence['nen_canh']>=.25 and evidence['vang_canh']>=.20)
    plain=(evidence['nen_canh']<.20 and not blue_cap and not ornate and star['diem']<.85)
    k=learned.get('khung') if learned else None
    out=dict(khung=None,ly_do='bang_chung_v2_chua_ro',bang_chung_hinh_hoc=evidence)
    if k==1:
        if plain:out['ly_do']='mau_va_hinh_hoc_mau_thuan_v2'
        else:out.update(khung=1,ly_do='mau_can_dong_thuan_v2')
    elif k==0:
        if blue_cap and star['diem']>=.75:out['ly_do']='mau_va_sao_mau_thuan_v2'
        else:out.update(khung=0,ly_do='mau_can_dong_thuan_v2')
    elif blue_cap and star['diem']>=.62:
        out.update(khung=1,ly_do='sao_xanh_va_vien_goc_v2')
    elif plain:
        out.update(khung=0,ly_do='the_thang_khong_co_bang_chung_sao_v2')
    elif ornate and star['diem']>=.75 and star['sao_tin_cay']:
        out.update(khung=1,ly_do='sao_va_vien_trang_tri_v2')
    return out
