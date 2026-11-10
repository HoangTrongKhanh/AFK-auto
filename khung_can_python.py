"""Mẫu khung đã căn của Python: chỉ so màu/cấu trúc vùng viền và dải sao.

Không nhận tên, không dùng ảnh mặt ở giữa. Chênh lệch khoảng cách là bằng
chứng so mẫu, không phải xác suất. Mẫu xa hoặc hai lớp gần nhau trả chưa rõ.
"""
from pathlib import Path
import cv2
import numpy as np

PHIEN_BAN = 1
MAC_DINH = Path(__file__).resolve().parent/'thu_thap_tuong'/'khung_can_python.npz'


def dac_trung(the, quality):
    if the is None or the.shape!=(205,130,3) or not quality.get('day_du'):
        raise ValueError('Chỉ lấy đặc trưng từ ảnh căn có biên đã xác minh')
    a,b,c,d = quality['bien_chuan']
    if not (0<=a<c<=130 and 0<=b<d<=205):
        raise ValueError('Biên chuẩn nằm ngoài ảnh')
    obj = cv2.resize(the[b:d,a:c], (96,144), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(obj, cv2.COLOR_BGR2HSV).astype(np.float32)
    # Hai góc trên, hai cạnh; bỏ vùng mặt trung tâm và biểu tượng phe ở đáy trái.
    patches = [hsv[:20,:24], hsv[:20,-24:], hsv[35:115,:7], hsv[35:115,-7:]]
    features = []
    for patch in patches:
        hue,sat,val = [patch[:,:,i] for i in range(3)]
        # Hue có trọng số saturation để tóc trắng không thành màu sao/viền.
        hist=np.histogram(hue,bins=12,range=(0,180),weights=sat/255)[0]/hue.size
        features.extend(hist)
        features.extend([sat.mean()/255, sat.std()/255, val.mean()/255, val.std()/255])
    star=hsv[:42]
    # Cấu trúc màu dải sao theo ba phần ngang, không học chi tiết chân dung.
    for patch in np.array_split(star,3,axis=1):
        hue,sat,val=[patch[:,:,i] for i in range(3)]
        features.extend([float(((hue>=75)&(hue<=115)&(sat>=25)&(val>=150)).mean()),
                         float(((hue>=10)&(hue<=38)&(sat>=100)&(val>=150)).mean())])
    return np.array(features,dtype=np.float32)


class MauKhungCan:
    def __init__(self, features, labels, ids, radius, ratio=.6):
        self.features=np.asarray(features,dtype=np.float32)
        self.labels=np.asarray(labels,dtype=np.int64)
        self.ids=np.asarray(ids,dtype=np.int64)
        self.radius=np.asarray(radius,dtype=np.float32)
        self.ratio=float(ratio)
        if (self.features.ndim!=2 or self.features.shape[1]!=70 or len(self.features)!=len(self.labels)
                or len(self.ids)!=len(self.labels) or set(self.labels.tolist())!={0,1}
                or self.radius.shape!=(2,) or not np.isfinite(self.features).all()
                or not np.isfinite(self.radius).all() or np.any(self.radius<=0)
                or not 0<self.ratio<1):
            raise ValueError('Mẫu khung căn không đúng định dạng')

    @classmethod
    def nap(cls,path=MAC_DINH):
        with np.load(path,allow_pickle=False) as z:
            if int(z['phien_ban'])!=PHIEN_BAN:raise ValueError('Sai phiên bản mẫu khung căn')
            return cls(z['features'],z['labels'],z['ids'],z['radius'],float(z['ratio']))

    def luu(self,path=MAC_DINH):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(path,features=self.features,labels=self.labels,ids=self.ids,
                            radius=self.radius,ratio=self.ratio,phien_ban=PHIEN_BAN)

    def du_doan(self,the,quality):
        f=dac_trung(the,quality)
        distances=((self.features-f)**2).mean(axis=1)
        # Mỗi lớp lấy cùng số láng giềng, không để lớp nhiều mẫu lấn át.
        ds=[float(np.sort(distances[self.labels==k])[:3].mean()) for k in (0,1)]
        k=int(ds[1]<ds[0]);near,far=ds[k],ds[1-k]
        out=dict(khung=None,khoang_cach_khong=ds[0],khoang_cach_co=ds[1],
                 mau_gan_nhat=int(self.ids[int(distances.argmin())]),
                 ty_le_mau_sao_xanh=float(f[[64,66,68]].mean()),ly_do='mau_can_chua_tach_biet')
        if near>self.radius[k]:out['ly_do']='ngoai_mien_mau_can'
        elif near<self.ratio*far:
            out.update(khung=k,ly_do='mau_can_dong_thuan')
        return out


def hoc(features,labels,ids,ratio=.6):
    features=np.asarray(features,dtype=np.float32);labels=np.asarray(labels)
    radii=[]
    for k in (0,1):
        cls=features[labels==k]
        if len(cls)<4:raise ValueError('Mỗi lớp cần ít nhất 4 tướng để kiểm tra bỏ một mẫu')
        ds=((cls[:,None]-cls[None,:])**2).mean(axis=2)
        np.fill_diagonal(ds,np.inf)
        # Bán kính từ láng giềng cùng lớp khi loại chính mẫu, không dùng tập kiểm tra.
        radii.append(max(.0001,float(np.quantile(np.sort(ds,axis=1)[:,:3].mean(axis=1),.95))*1.5))
    return MauKhungCan(features,labels,ids,radii,ratio)
