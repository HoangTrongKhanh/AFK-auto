"""Đọc thẻ lớn trong Hội Trường Cộng Hưởng; không chạm nút nâng cấp/trang bị."""
import cv2
import numpy as np
from nhan_dien import REF_W, TPL_DIR

# Nhãn Cấp ở đáy thẻ: mốc đứng yên, không lấy chữ số cấp thay đổi theo tài khoản.
TY_LE_NHAN = (0.95, 1.0, 1.15, 1.2, 1.25)


def _hang_tu_bien(ref, top, bottom):
    """Dự phòng khi cả trang phẩm thấp không có chữ Cấp khớp mẫu nền cũ."""
    ya=max(0,int(top));yb=min(ref.shape[0],int(bottom))
    if yb-ya<240:return []
    hsv=cv2.cvtColor(ref[ya:yb,100:1490],cv2.COLOR_BGR2HSV)
    pale=(hsv[:,:,0]>=120)&(hsv[:,:,0]<=175)&(hsv[:,:,1]>=25)
    mask=((hsv[:,:,1]>65)|(hsv[:,:,2]<180)|pale).astype(np.uint8)
    _,_,stats,_=cv2.connectedComponentsWithStats(mask,8)
    groups=[]
    for x,y,w,h,area in stats[1:]:
        if not(150<=w<=265 and 240<=h<=355):continue
        cx=100+x+w/2
        col=round((cx-250)/218.5)
        if not(0<=col<6) or abs(cx-(250+218.5*col))>35:continue
        rough=float(ya+y+h/2-145)
        group=next((g for g in groups if abs(np.median([v[0] for v in g])-rough)<25),None)
        if group is None:groups.append([(rough,col)])
        else:group.append((rough,col))
    return [(float(np.median([v[0] for v in g])),len({v[1] for v in g}))
            for g in groups if len({v[1] for v in g})>=2]


def cat_the_hoi_truong(img, *, can_bien=True, kem_chat_luong=False):
    """Căn theo biên; chế độ chi tiết giữ cả ứng viên lỗi để theo dõi nhưng không đọc khung.
    Kết quả chi tiết: (ảnh căn/ảnh tạm, tâm y, chất lượng, ảnh cũ để đối chiếu danh tính).
    can_bien=False chỉ dùng cho hồi quy/đối chiếu ảnh tham chiếu cũ.
    """
    s = REF_W / img.shape[1]
    ref = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s != 1 else img
    h = ref.shape[0]
    gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    tpl = cv2.imread(str(TPL_DIR / 'ht_cap.png'), cv2.IMREAD_GRAYSCALE)
    # Ở đầu Hội Trường chưa có thanh Di Vật/Trang Bị nổi che đáy danh sách.
    dau = cv2.imread(str(TPL_DIR / 'ht_dau.png'), cv2.IMREAD_GRAYSCALE)
    dau = cv2.resize(dau, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
    small = cv2.resize(gray, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
    tren_cung = float(cv2.matchTemplate(small, dau, cv2.TM_CCOEFF_NORMED).max()) >= .8
    day = h - (260 if tren_cung else 490)
    # Chừa thanh nút cố định phía dưới và phần đầu đang bị cắt khi cuộn.
    y0, y1 = 260, day + 20
    hits = []
    for scale in TY_LE_NHAN:
        t = cv2.resize(tpl, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        r = cv2.matchTemplate(gray[y0:y1, 100:1490], t, cv2.TM_CCOEFF_NORMED)
        for _ in range(80):
            _, score, _, (x, y) = cv2.minMaxLoc(r)
            if score < .65:
                break
            hits.append((score, x + 100, y + y0, scale))
            r[max(0,y-50):y+51, max(0,x-50):x+51] = 0
    kept = []
    for hit in sorted(hits, reverse=True):
        if not any(abs(hit[1]-a[1]) < 65 and abs(hit[2]-a[2]) < 35 for a in kept):
            kept.append(hit)
    rows = []
    for hit in sorted(kept, key=lambda a:a[2]):
        group = next((r for r in rows if abs(np.median([a[2] for a in r])-hit[2]) < 22), None)
        if group is None: rows.append([hit])
        else: group.append(hit)
    # Khôi phục các hàng lưới từ nhãn Cấp còn thấy được. Nhãn ở một số thẻ phẩm thấp
    # có nền khác mẫu; không đòi từng hàng đều phải có nhãn khớp.
    large, grid = [], []
    for row in rows:
        if len(row) < 2 and row[0][0] < .83:
            continue
        big = float(np.median([a[3] for a in row])) > 1.08
        size = 1.15 if big else 1.
        top = float(np.median([a[2] for a in row])) - 234 * size
        (large if big else grid).append((top, sum(a[0] for a in row)))
    positions = [(top, True) for top, _ in large]
    grid_top = max([top + 290 * 1.15 + 150 for top, _ in large] or [y0])
    if not grid and large:
        grid = _hang_tu_bien(ref, grid_top, day)
    if grid:
        anchor = max(grid, key=lambda x: x[1])[0]
        # Nhóm 5 thẻ và tiêu đề Tướng Cộng Hưởng che phần đầu của hàng đang trôi.
        for j in range(-12, 13):
            top = anchor + j * 308
            if top >= grid_top and top + 290 <= day:
                positions.append((top, False))
    out = []
    for top, big in sorted(positions):
        size = 1.15 if big else 1.
        if top < y0 or top + 290 * size > day:
            continue
        centers = [249 + 268.5*i for i in range(5)] if big else [250 + 218.5*i for i in range(6)]
        k = 130 / (218 * size)
        small = cv2.resize(ref, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        for cx in centers:
            # Nút lọc tròn đè lên cột cuối: bỏ thẻ này, đọc khi thẻ hiện trọn ở ảnh sau.
            if not tren_cung and cx + 100*size > 1340 and top + 290*size > h - 650:
                continue
            x, y = int(cx*k), int(top*k)-15
            card = small[y:y+205, x-65:x+65]
            if card.shape[:2] != (205,130) or card.std() < 18:
                continue
            # Tóc/lông trắng cũng giống màu nền kem; dùng độ biến thiên vùng mặt thay tỷ lệ kem.
            face_bgr = card[55:140,21:109]
            if cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY).std() < 12:
                continue  # ô trống hoặc chữ trên nền, không ghi thành tướng
            if not can_bien:
                out.append((card.copy(), top + 145*size))
                continue
            from can_khung_tuong import can_khung
            aligned, quality = can_khung(ref, cx, top, size, grid_top if not big else y0, day)
            quality.update(tam_x=float(cx),tam_y=float(top+145*size))
            if kem_chat_luong:
                out.append((aligned if aligned is not None else card.copy(), top+145*size, quality, card.copy()))
            elif aligned is not None:
                out.append((aligned, top+145*size))
    return out

def kiem_tra_danh_sach_ngan(img, so_tuong_du_kien, tren_cung):
    """Không suy ra danh sách ngắn từ ảnh đứng yên: cần số sở hữu đối chiếu từ nguồn khác."""
    from doc_tuong_cua_toi import mat, CUNG_THE
    from thong_ke_tuong import giong
    from quan_ly_mau import pixel_sha
    out=dict(hop_le=False,so_tuong_du_kien=so_tuong_du_kien,ly_do='thieu_so_luong_nguon')
    if type(so_tuong_du_kien) is not int or so_tuong_du_kien<1:return out
    if not tren_cung:return dict(out,ly_do='chua_co_moc_dau')
    from cat_the_bo_sung import cat_day_du
    cards=cat_day_du(img,kem_chat_luong=True)
    out['so_the_day_du']=sum(bool(c[2].get('day_du')) for c in cards)
    if len(cards)!=so_tuong_du_kien:return dict(out,ly_do='so_the_khong_khop_nguon')
    if not all(c[2].get('day_du') for c in cards):return dict(out,ly_do='co_the_cat_thieu')
    faces=[mat(c[3]) for c in cards]
    if any(giong(a,b)>=CUNG_THE for i,a in enumerate(faces) for b in faces[i+1:]):
        return dict(out,ly_do='the_co_the_bi_dem_trung')
    return dict(out,hop_le=True,ly_do='du_the_du_bien_khop_so_luong_nguon',mat_sha256=[pixel_sha(f) for f in faces])


def chup_hoi_truong(adb, nd, thu_muc=None, *, toi_da=60, xac_minh_cuoi=True,
                   so_tuong_du_kien=None, bang_chung_phien=None):
    """Mở bằng nút nhận diện, về đầu rồi cuộn hết. Không ghi đè kết quả khi mất màn hoặc chưa tới cuối."""
    import time
    if so_tuong_du_kien is not None and (type(so_tuong_du_kien) is not int or so_tuong_du_kien<1):
        raise ValueError('Số tướng tham chiếu phải là số nguyên dương')
    def capture():
        from leo_ai import tim_o_khoa
        for _ in range(4):
            img=adb.screenshot()
            if not adb.game_booster_locked(): return img
            h,w=img.shape[:2]
            adb.tap(w//2,h//2);time.sleep(.6)
            x,y=tim_o_khoa(adb.screenshot()) or (w//2,int(h*.52))
            adb.swipe(x,y,x,y-h//8,400);time.sleep(1)
        raise RuntimeError('Không gỡ được khóa Game Booster; giữ dữ liệu khung cũ.')
    img=capture()
    ket = nd.nhan_dien(img)
    if ket.man_hinh == 'nghi' and 'nghi_nhan_tiep_tuc' in ket.nut:
        adb.tap(*ket.nut['nghi_nhan_tiep_tuc']);time.sleep(2)
        img=capture();ket=nd.nhan_dien(img)
    if thu_muc is not None:
        cv2.imwrite(str(thu_muc/'truoc_khi_doc.png'),img)
    print('Màn trước khi đọc:',ket,flush=True)
    if ket.man_hinh != 'hoi_truong':
        small, k = nd._thu_nho(img)
        buttons = [(nd.tim(small, n), n) for n in ('ht_nut_menu','ht_nut_afk')]
        (score, pos), name = max(buttons, key=lambda a:a[0][0])
        if score < .8 or pos is None or ket.man_hinh == 'khoa':
            raise RuntimeError('Hãy mở game ở bản đồ, Màn AFK hoặc Hội Trường Cộng Hưởng; không thấy nút Hội Trường.')
        adb.tap(round(pos[0]/k), round(pos[1]/k))
        for _ in range(12):
            time.sleep(1)
            img = capture()
            if nd.nhan_dien(img).man_hinh == 'hoi_truong': break
        else: raise RuntimeError('Không mở được Hội Trường Cộng Hưởng.')
    h,w=img.shape[:2];s=w/1600
    def region(im):
        return cv2.resize(im[int(1000*s):int(h-490*s),int(130*s):int(1450*s)],(132,100),interpolation=cv2.INTER_AREA)
    def check(im):
        if nd.nhan_dien(im).man_hinh != 'hoi_truong':
            if thu_muc is not None: cv2.imwrite(str(thu_muc/'man_bi_doi.png'),im)
            print('Màn sau cuộn:',nd.nhan_dien(im),flush=True)
            raise RuntimeError('Đã rời Hội Trường hoặc game bị khóa; giữ nguyên dữ liệu khung cũ.')
    images=[];short=None
    for direction in (1,-1):
        stable=0;old=region(img);moved=False
        for i in range(toi_da):
            if direction==1 and 'ht_dau' in nd.nhan_dien(img).nut: break
            if direction == -1 and not images:
                images.append(img)
            ya = h - 800*s
            yb = ya - (600 if direction == 1 else 300)*s
            adb.swipe(800*s, yb if direction == 1 else ya, 800*s,
                      ya if direction == 1 else yb, 700 if direction == 1 else 1000)
            time.sleep(1.1)
            img=capture();check(img)
            new=region(img)
            delta=float(cv2.absdiff(old,new).mean())
            if direction == -1 and delta >= 2:
                images.append(img)
                print(f'Đọc Hội Trường: ảnh {len(images)}', flush=True)
            stable=stable+1 if delta<2 else 0
            moved=moved or delta>=2
            old=new
            if stable>=2:
                if not moved:
                    proof=kiem_tra_danh_sach_ngan(img,so_tuong_du_kien,
                        'ht_dau' in nd.nhan_dien(img).nut) if direction==-1 else None
                    if not proof or not proof['hop_le']:
                        raise RuntimeError('Danh sách không phản hồi cuộn, chưa xác nhận được đầu/cuối. Không lưu dữ liệu khung.')
                    first=kiem_tra_danh_sach_ngan(images[0],so_tuong_du_kien,
                        'ht_dau' in nd.nhan_dien(images[0]).nut)
                    if not first['hop_le'] or first['mat_sha256']!=proof['mat_sha256']:
                        raise RuntimeError('Ảnh đầu không xác minh đủ danh sách ngắn; giữ dữ liệu cũ.')
                    short=proof
                break
        else: raise RuntimeError(f'Chưa tới đầu/cuối sau {toi_da} lần cuộn; không lưu kết quả chưa đầy đủ.')
    if short and not xac_minh_cuoi:
        raise RuntimeError('Danh sách ngắn cần xác minh cả hai chiều; chưa lưu kết quả')
    if xac_minh_cuoi:
        # Không coi một lần cuộn bị kẹt giữa danh sách là cuối. Lùi lại phải có dịch chuyển,
        # rồi cuộn xuôi phải quay về đúng ảnh cuối vừa thấy.
        end = region(img)
        adb.swipe(800*s, h-1100*s, 800*s, h-800*s, 1000)
        time.sleep(1.1)
        back = capture(); check(back)
        back_delta=float(cv2.absdiff(end, region(back)).mean())
        if short:
            proof=kiem_tra_danh_sach_ngan(back,so_tuong_du_kien,'ht_dau' in nd.nhan_dien(back).nut)
            if back_delta>=2 or not proof['hop_le'] or proof['mat_sha256']!=short['mat_sha256']:
                raise RuntimeError('Danh sách còn dịch chuyển hoặc đổi thẻ khi kiểm tra ngược; chưa xác nhận danh sách ngắn.')
        elif back_delta < 2:
            raise RuntimeError('Không xác minh được cuối danh sách: cuộn ngược không phản hồi. Giữ dữ liệu cũ.')
        if not short:
            for _ in range(4):
                adb.swipe(800*s, h-800*s, 800*s, h-1100*s, 1000)
                time.sleep(1.1)
                again = capture(); check(again)
                if float(cv2.absdiff(end, region(again)).mean()) < 2:
                    break
            else:
                raise RuntimeError('Không quay lại được ảnh cuối danh sách sau kiểm tra cuộn. Giữ dữ liệu cũ.')
        if not any(cat_the_hoi_truong(image) for image in images):
            raise RuntimeError('Không đọc được thẻ nào trong phiên Hội Trường; không xác nhận hoàn tất.')
    if thu_muc is not None:
        for i, image in enumerate(images, 1):
            cv2.imwrite(str(thu_muc/f'{i:02d}.png'), image)
    if xac_minh_cuoi:
        audit = kiem_tra_do_phu(images)
        if any(item['can_kiem_tra'] for item in audit['noi_trang']):
            raise RuntimeError('Các trang lưới không có thẻ chồng lấp; chưa xác nhận thu đủ danh sách.')
    proof=dict(cach_xac_minh='so_luong_nguon_va_hai_chieu_dung_yen' if short else 'cuon_nguoc_roi_quay_lai_anh_cuoi',
               so_tuong_du_kien=so_tuong_du_kien,nguon_so_luong='nguoi_goi_cung_cap' if so_tuong_du_kien else None,
               danh_sach_ngan=short,da_xac_minh=bool(xac_minh_cuoi))
    if bang_chung_phien is not None:bang_chung_phien.update(proof)
    if thu_muc is not None:
        from quan_ly_mau import ghi_json
        ghi_json(thu_muc/'xac_minh_phien.json',proof)
    print(f'Đã đọc hết Hội Trường: {len(images)} ảnh.',flush=True)
    return images


def kiem_tra_do_phu(images):
    """Kiểm tra nối tiếp lưới cuộn; bỏ nhóm 5 thẻ cố định để không báo chồng lấp giả."""
    from doc_tuong_cua_toi import mat, CUNG_THE
    from thong_ke_tuong import giong
    from cat_the_bo_sung import cat_day_du
    pages = [cat_day_du(im,can_bien=False) for im in images]
    links = []
    for i, (a, b) in enumerate(zip(pages, pages[1:]), 1):
        # Các ảnh Hội Trường hiện tại có nhóm 5 thẻ lớn cố định trước phần lưới.
        ga, gb = a[5:], b[5:]
        shared = sum(any(giong(mat(c), mat(d)) >= CUNG_THE for d, _ in gb) for c, _ in ga)
        links.append(dict(tu=i, den=i+1, the_luoi_trung=shared,
                          can_kiem_tra=bool(ga and gb and shared == 0)))
    return dict(so_anh=len(images), so_the_tung_anh=[len(p) for p in pages], noi_trang=links,
                luu_y='Chồng lấp ảnh chỉ kiểm tra tính liên tục; không chứng minh mọi ô thẻ đã được phát hiện.')
