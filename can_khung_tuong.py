"""Căn thẻ theo miền ảnh có biên thực tế; trả chất lượng hình học trước khi đọc sao/viền."""
import cv2
import numpy as np


def diem_sao_da_ty_le(the, templates):
    """Điểm sao và bằng chứng hàng sao, tránh cực đại đơn trên tóc/mũ."""
    gray=cv2.cvtColor(the[5:70],cv2.COLOR_BGR2GRAY)
    peaks=[];best=(-1.,1.)
    for scale in (.75,.8,.85,.9,.95,1.,1.05,1.1):
        for template in templates:
            t=cv2.resize(template,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_LINEAR)
            r=cv2.matchTemplate(gray,t,cv2.TM_CCOEFF_NORMED)
            best=max(best,(float(r.max()),scale))
            for _ in range(8):
                _,score,_,(x,y)=cv2.minMaxLoc(r)
                if score<.68:break
                peaks.append((score,x+t.shape[1]/2,y+t.shape[0]/2,t.shape[1]))
                r[max(0,y-6):y+7,max(0,x-6):x+7]=0
    kept=[]
    for peak in sorted(peaks,reverse=True):
        if not any(abs(peak[1]-p[1])<7 and abs(peak[2]-p[2])<7 for p in kept):kept.append(peak)
    pair=any(abs(p[2]-q[2])<=4 and .75*min(p[3],q[3])<=abs(p[1]-q[1])<=1.6*max(p[3],q[3])
             and max(p[0],q[0])>=.75 for i,p in enumerate(kept) for q in kept[i+1:])
    return dict(diem=best[0],ty_le=best[1],co_hang_sao=bool(pair),sao_tin_cay=bool(best[0]>=.82 or pair))


def can_khung(ref, cx, top, size, visible_top, visible_bottom):
    h,w=ref.shape[:2]
    xa,xb=int(cx-142*size),int(cx+142*size)
    ya,yb=int(top-50*size),int(top+350*size)
    xa,xb=max(0,xa),min(w,xb);ya,yb=max(0,ya),min(h,yb)
    info=dict(day_du=False,ly_do='khong_tim_duoc_bien',bien=None)
    if xb<=xa or yb<=ya:return None,info
    roi=ref[ya:yb,xa:xb]
    hsv=cv2.cvtColor(roi,cv2.COLOR_BGR2HSV)
    # Viền tím nhạt có độ bão hòa thấp và sáng gần nền kem. Giữ dải tím
    # riêng thay vì hạ ngưỡng S chung (sẽ nối cả nền giữa hai thẻ).
    pale_rim=(hsv[:,:,0]>=120)&(hsv[:,:,0]<=175)&(hsv[:,:,1]>=25)
    mask=((hsv[:,:,1]>65)|(hsv[:,:,2]<180)|pale_rim).astype(np.uint8)
    yy,xx=np.indices(mask.shape)
    # Nút mũi tên nâng cấp nằm ngoài góc trên phải, không phải biên tướng.
    upgrade=(hsv[:,:,0]>=35)&(hsv[:,:,0]<=85)&(hsv[:,:,1]>70)&(yy+ya<top+25*size)&(xx+xa>cx+45*size)
    mask[upgrade]=0
    # Chóp khung ở hai cột cũng có thể chạm nhau. Tìm khe dọc theo phần thân thẻ,
    # không để một component dính sang thẻ bên cạnh làm lệch tâm.
    body=mask[max(0,int(top+65*size)-ya):min(mask.shape[0],int(top+245*size)-ya)]
    column_profile=body.mean(axis=0)
    column_cuts=[];columns_ok=True
    for lo,hi,ideal in [(-125,-75,-98),(100,141,123)]:
        xs=list(range(max(0,int(cx+lo*size)-xa),min(len(column_profile),int(cx+hi*size)-xa)))
        cut=min(xs,key=lambda x:(float(column_profile[x]),abs(x+xa-(cx+ideal*size))))
        column_cuts.append(cut)
        columns_ok=columns_ok and column_profile[cut]<.15
    mask[:,:column_cuts[0]]=0
    mask[:,column_cuts[1]:]=0
    split_ok = True
    if size == 1.0:
        # Tách hai chóp vàng chạm nhau tại thắt eo giữa hai hàng, không cắt theo
        # chiều cao cố định. Khe hẹp phải ít hơn 15% bề ngang thẻ.
        cols = slice(max(0,int(cx-95)-xa), min(mask.shape[1],int(cx+123)-xa))
        profile = mask[:,cols].mean(axis=1)
        cuts=[]
        for lo,hi,ideal in [(-35,-5,-18),(280,307,296)]:
            ys=list(range(max(0,int(top+lo)-ya), min(len(profile),int(top+hi)-ya)))
            cut=min(ys,key=lambda y: (float(profile[y]),abs(y+ya-(top+ideal))))
            cuts.append(cut)
            split_ok = split_ok and profile[cut] < .15
        cut_top, cut_bottom = cuts
        mask[:cut_top]=0
        mask[cut_bottom:]=0
    else:
        cut_top, cut_bottom = 0, mask.shape[0]
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    candidates=[]
    for i in range(1,n):
        x,y,bw,bh,area=stats[i];left,right=xa+x,xa+x+bw;upper,lower=ya+y,ya+y+bh
        if not (160*size<=bw<=262*size and 240*size<=bh<=365*size):continue
        if abs((left+right)/2-cx)>35*size or not top-48*size<=upper<=top+25*size:continue
        if not top+250*size<=lower<=top+340*size:continue
        candidates.append((int(area),i,(int(left),int(upper),int(right),int(lower))))
    if not candidates:return None,info
    _,index,box=max(candidates)
    left,upper,right,lower=box
    info['bien']=list(box)
    bw,bh=right-left,lower-upper
    # Không suy diễn phần bị màn cố định, mép ảnh hoặc ROI tìm biên cắt mất.
    if (not columns_ok or not split_ok or left<=xa or right>=xb or upper<=ya or lower>=yb
            or upper<visible_top or lower>visible_bottom):
        info['ly_do']='bien_bi_cat_hoac_che';return None,info
    component = labels[upper-ya:lower-ya,left-xa:right-xa] == index
    side = max(4,round(bw*.06))
    middle = component[round(bh*.25):round(bh*.85)]
    supports = [float(middle[:,:side].any(axis=1).mean()),float(middle[:,-side:].any(axis=1).mean())]
    info.update(ho_tro_vien=supports,vung_sao_day_du=True,vien_day_du=min(supports)>=.2)
    if not info['vien_day_du']:
        info['ly_do']='chua_xac_minh_hai_vien';return None,info
    # Vùng gốc được cắt đúng biên, sau đó đặt giữa canvas. Không đưa hàng bên cạnh vào mẫu.
    k=min(122/bw,189/bh)
    tw,th=round(bw*k),round(bh*k)
    bg_pixels=roi[(hsv[:,:,1]<60)&(hsv[:,:,2]>200)]
    bg=np.median(bg_pixels,axis=0).astype(np.uint8) if len(bg_pixels) else np.array([220,234,243],np.uint8)
    out=np.empty((205,130,3),np.uint8);out[:]=bg
    ox,oy=(130-tw)//2,(205-th)//2
    out[oy:oy+th,ox:ox+tw]=cv2.resize(ref[upper:lower,left:right],(tw,th),interpolation=cv2.INTER_AREA)
    info.update(day_du=True,khe_hang_tach=bool(split_ok),khe_cot_tach=bool(columns_ok),ly_do='bien_day_du',bien_chuan=[ox,oy,ox+tw,oy+th],ty_le=float(k))
    return out,info
