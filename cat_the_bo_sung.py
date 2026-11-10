"""Bổ sung hàng lưới chỉ có một thẻ khi bộ cắt dựa chữ Cấp chưa tìm được hàng."""
import cv2
import numpy as np
import hoi_truong as H
from nhan_dien import REF_W,TPL_DIR


def cat_day_du(img,*,can_bien=True,kem_chat_luong=False):
    base=H.cat_the_hoi_truong(img,kem_chat_luong=True)
    def output(ds):
        if kem_chat_luong:return ds
        if not can_bien:return [(c[3],c[1]) for c in ds]
        return [(c[0],c[1]) for c in ds if c[2].get('day_du')]
    # Chỉ bổ sung khi có đủ 5 thẻ cố định và chưa có thẻ lưới nào, không suy ra cả hàng 6 ô.
    if len(base)!=5:return output(base)
    if any(abs(c[2]['tam_x']-(249+268.5*i))>8 for i,c in enumerate(base)):return output(base)
    scale=REF_W/img.shape[1];ref=cv2.resize(img,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale!=1 else img
    h,w=ref.shape[:2];top=int(max(c[2]['tam_y']+145*1.15 for c in base)+150);bottom=h-490
    if bottom-top<260:return output(base)
    candidates=[];tpl=cv2.imread(str(TPL_DIR/'ht_cap.png'),cv2.IMREAD_GRAYSCALE)
    for col in range(6):
        cx=250+218.5*col;xa,xb=round(cx-109),round(cx+109)
        roi=ref[top:bottom,xa:xb];hsv=cv2.cvtColor(roi,cv2.COLOR_BGR2HSV)
        mask=((hsv[:,:,1]>65)|(hsv[:,:,2]<180)|((hsv[:,:,0]>=120)&(hsv[:,:,0]<=175)&(hsv[:,:,1]>=25))).astype(np.uint8)
        # Tóc trắng có thể ngắt phần thân khỏi hai góc trên. Ghép trong từng ô, không nối sang cột bên cạnh.
        padded=cv2.copyMakeBorder(mask,32,32,32,32,cv2.BORDER_CONSTANT,value=0)
        joined=cv2.morphologyEx(padded,cv2.MORPH_CLOSE,np.ones((31,31),np.uint8))[32:-32,32:-32]
        _,_,stats,_=cv2.connectedComponentsWithStats(joined,8)
        for x,y,bw,bh,area in stats[1:]:
            if not(160<=bw<=210 and 240<=bh<=365):continue
            if x<=1 or x+bw>=roi.shape[1]-1 or y<15 or y+bh>roi.shape[0]-15:continue
            body=mask[y:y+bh,x:x+bw];side=max(4,round(bw*.06));mid=body[round(bh*.25):round(bh*.85)]
            support=[float(mid[:,:side].any(1).mean()),float(mid[:,-side:].any(1).mean())]
            if min(support)<.2 or min(body[:24,:36].mean(),body[:24,-36:].mean())<.1 or body[-24:].mean()<.25:continue
            gray=cv2.cvtColor(roi[y+int(bh*.65):y+bh,x:x+bw],cv2.COLOR_BGR2GRAY)
            best=(-1,None)
            for size in (.95,1.):
                t=cv2.resize(tpl,None,fx=size,fy=size,interpolation=cv2.INTER_LINEAR)
                r=cv2.matchTemplate(gray,t,cv2.TM_CCOEFF_NORMED);_,score,_,pos=cv2.minMaxLoc(r)
                if score>best[0]:best=(score,y+int(bh*.65)+pos[1]+top)
            if best[0]<.55:continue
            left,upper,right,lower=int(xa+x),int(top+y),int(xa+x+bw),int(top+y+bh)
            k=min(122/bw,189/bh);tw,th=round(bw*k),round(bh*k);ox,oy=(130-tw)//2,(205-th)//2
            bg=roi[(hsv[:,:,1]<60)&(hsv[:,:,2]>200)]
            aligned=np.empty((205,130,3),np.uint8);aligned[:]=np.median(bg,axis=0).astype(np.uint8) if len(bg) else (220,234,243)
            aligned[oy:oy+th,ox:ox+tw]=cv2.resize(ref[upper:lower,left:right],(tw,th),interpolation=cv2.INTER_AREA)
            row_top=best[1]-234;k_old=130/218;small=cv2.resize(ref,None,fx=k_old,fy=k_old,interpolation=cv2.INTER_AREA)
            xx,yy=int(cx*k_old),int(row_top*k_old)-15;legacy=small[yy:yy+205,xx-65:xx+65]
            if legacy.shape!=(205,130,3) or cv2.cvtColor(legacy[55:140,21:109],cv2.COLOR_BGR2GRAY).std()<12:continue
            q=dict(day_du=True,ly_do='bien_day_du_mot_the_tach_manh',bien=[left,upper,right,lower],
                bien_chuan=[ox,oy,ox+tw,oy+th],ho_tro_vien=support,vung_sao_day_du=True,vien_day_du=True,
                khe_hang_tach=True,khe_cot_tach=True,ty_le=float(k),tam_x=float(cx),tam_y=float(row_top+145),
                diem_nhan_cap=float(best[0]),bo_cat='single_column_v1')
            candidates.append((aligned,float(row_top+145),q,legacy.copy()))
    # Nhiều ứng viên không được tự coi là một danh sách một-thẻ.
    return output(base+candidates) if len(candidates)==1 else output(base)
