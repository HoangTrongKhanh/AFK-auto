# Hướng dẫn cho người mới vào dự án AFK Auto

Tài liệu này viết cho người **chưa biết Python, Kotlin hay OpenCV**. Đọc hết một lượt (khoảng 1-2 giờ), vừa đọc vừa mở
code bên cạnh. Sau đó bạn sẽ hiểu bot chạy thế nào, sửa ở đâu, và kiểm tra ra sao để không làm hỏng phần đang chạy tốt.

- Bot làm gì, dùng ra sao: [README.md](README.md)
- Vì sao làm như vậy, bằng chứng đo trên máy thật: [YEU_CAU.md](YEU_CAU.md)
- Code chạy thế nào và sửa ra sao: **tài liệu này**

Mục lục

1. [Bức tranh tổng thể](#1-bức-tranh-tổng-thể)
2. [Bản đồ thư mục](#2-bản-đồ-thư-mục)
3. [Cài đặt và chạy thử lần đầu](#3-cài-đặt-và-chạy-thử-lần-đầu)
4. [Kiến thức nền: ảnh số và OpenCV](#4-kiến-thức-nền-ảnh-số-và-opencv)
5. [Python đủ dùng cho dự án này](#5-python-đủ-dùng-cho-dự-án-này)
6. [Các ý tưởng chính của dự án](#6-các-ý-tưởng-chính-của-dự-án)
7. [Đi qua từng file Python](#7-đi-qua-từng-file-python)
8. [Kotlin và Android đủ dùng](#8-kotlin-và-android-đủ-dùng)
9. [App Android: cấu trúc và cách nó khớp với bản Python](#9-app-android-cấu-trúc-và-cách-nó-khớp-với-bản-python)
10. [Công thức cho các việc hay gặp](#10-công-thức-cho-các-việc-hay-gặp)
11. [Gỡ lỗi khi bot chạy thật](#11-gỡ-lỗi-khi-bot-chạy-thật)
12. [Quy tắc và các bẫy hay gặp](#12-quy-tắc-và-các-bẫy-hay-gặp)
13. [Từ điển tên biến](#13-từ-điển-tên-biến)

---

## 1. Bức tranh tổng thể

**Game:** Hành Trình AFK (bản tiếng Việt, gói `com.farlightgames.igame.gp.vn`). Người chơi phải "leo ải": đánh ải 1,
thắng thì sang ải 2, cứ thế. Có 2 chế độ leo: **Màn AFK** và **Thách Đấu Huyền Linh**. Thua thì có thể vào bảng
**Thành Tích** (10 đội của người chơi khác đã qua ải này) và bấm **Sao chép** để lấy đội hình của họ.

**Bot** làm thay người chơi: đánh, thua thì chép đội khác, thắng thì đánh ải kế, kẹt cả hai chế độ thì dừng và báo.

Bot **không đọc dữ liệu của game**. Nó chỉ làm đúng việc một người làm: **nhìn màn hình rồi bấm**. Mỗi vòng lặp gồm:

```
┌────────────┐   ┌──────────────────────┐   ┌─────────────────────┐   ┌──────────┐
│ Chụp màn   │──▶│ Nhận diện: đang ở màn │──▶│ Quyết định: ở màn này│──▶│ Bấm / chờ│──┐
│ hình       │   │ nào, nút nằm ở đâu?   │   │ thì làm việc gì?    │   │          │  │
└────────────┘   └──────────────────────┘   └─────────────────────┘   └──────────┘  │
      ▲                                                                              │
      └──────────────────────────────────────────────────────────────────────────────┘
```

Có **2 bản** của bot, cùng thuật toán:

| | Bản máy tính (PC) | App Android |
|---|---|---|
| Ngôn ngữ | Python | Kotlin |
| Chạy ở đâu | Máy tính, điều khiển điện thoại qua cáp USB / Wi-Fi | Ngay trên điện thoại chạy game |
| Chụp màn hình, bấm | Lệnh `adb` (Android Debug Bridge) | Dịch vụ Trợ năng (Accessibility Service) của Android |
| Nhận diện ảnh | OpenCV cho Python (`cv2`) | OpenCV cho Java/Kotlin |
| Vai trò | Nơi **thử nghiệm**: tính năng mới làm ở đây trước, đo trên máy thật | Bản **phát cho người dùng** (file APK) |

Hai bản dùng **chung một bộ ảnh mẫu** trong `templates/`. Có một bài kiểm tra tự động bắt bản Kotlin phải cho kết quả
giống hệt bản Python trên mọi ảnh mẫu (xem [mục 9.4](#94-bài-kiểm-tra-đối-chiếu-python--kotlin)).

> Quy trình làm tính năng: **sửa Python → thử trên máy thật → chuyển sang Kotlin → chạy bài kiểm tra đối chiếu → build APK.**

---

## 2. Bản đồ thư mục

```
AFK-Auto/
├── README.md, YEU_CAU.md, HUONG_DAN_DEV.md   tài liệu
├── requirements.txt          thư viện Python cần cài (numpy, opencv)
│
├── adb.py                    điều khiển máy qua ADB: chụp, chạm, vuốt, đọc trạng thái máy
├── nhan_dien.py              ảnh → "đang ở màn nào" + vị trí các nút      ← quan trọng nhất
├── so_ai.py                  đọc chữ số: số ải ở Màn AFK, "A → B" ở màn THẮNG
├── thanh_tich.py             đọc 1 đội trong bảng Thành Tích (tên, lực chiến, nhãn)
├── leo_ai.py                 CHƯƠNG TRÌNH CHÍNH: vòng lặp leo ải, chọn đội   ← quan trọng nhất
├── doc_tuong_cua_toi.py      đọc khung (phẩm) tướng của bạn ở danh sách tướng
├── thong_ke_tuong.py         thống kê tướng trong Thành Tích (công cụ dùng một lần)
├── tao_mau.py                cắt ảnh mẫu từ samples/ → templates/vi/  (+ xuất mau.json)
├── tao_thu_vien_tuong.py     tạo thư viện mặt tướng templates/vi/tuong/
├── test_*.py                 các bài kiểm tra tự động (không cần cắm máy)
│
├── samples/                  ẢNH CHỤP MÀN HÌNH THẬT (nguyên liệu để cắt mẫu + để kiểm tra)
│   ├── nhan.txt              "đáp án": ảnh nào là màn nào
│   └── thanh_tich/           ảnh bảng Thành Tích + nhan.txt (lực chiến, nhãn… đúng của từng ảnh)
├── templates/vi/             ẢNH MẪU đã cắt (do tao_mau.py sinh ra, đừng sửa tay)
│   ├── *.png                 mẫu nút / chữ để tìm trên màn hình
│   ├── mau.json              bảng toạ độ mẫu cho app Android (sinh tự động)
│   ├── luc_chien/            mẫu từng chữ số 0-9, M, K
│   └── tuong/                thư viện mặt tướng
│
├── android/                  APP ANDROID
│   ├── app/                  phần app: giao diện, dịch vụ Trợ năng, vòng lặp leo ải (Leo.kt)
│   └── vision/               phần nhận diện ảnh, viết lại từ Python, chạy được cả trên máy tính để kiểm tra
│
│   (các thứ dưới đây sinh ra khi chạy, KHÔNG đưa lên git - xem .gitignore)
├── leo_ai.log                nhật ký chi tiết lần chạy
├── debug/                    ảnh màn hình lúc có sự cố
├── tran.csv                  mỗi trận một dòng: lực chiến, kết quả… (để phân tích)
└── thu_thap_tuong/           dữ liệu tướng cá nhân của người chơi
```

Thứ tự đọc code đề xuất: `nhan_dien.py` → `so_ai.py` → `thanh_tich.py` → `leo_ai.py` → `adb.py` → phần còn lại.

---

## 3. Cài đặt và chạy thử lần đầu

### 3.1 Bản Python

Cần Python 3.10 trở lên (máy chủ dự án dùng 3.12).

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

`.venv` là "môi trường ảo": một thư mục chứa Python và thư viện riêng cho dự án, không ảnh hưởng máy. Vì thế mọi lệnh
đều gọi `.venv/bin/python` chứ không gọi `python`.

**Thử ngay mà không cần điện thoại** (chạy nhận diện trên ảnh có sẵn):

```bash
.venv/bin/python nhan_dien.py samples/tab_s7_man_afk.png
```

Kết quả: `tab_s7_man_afk.png: man_afk | sáng 123 | man_afk_tieu_de@302,1244, man_afk_chien_dau@1268,2142, ...`
nghĩa là: đây là Màn AFK, độ sáng trung bình 123, nút Chiến Đấu có tâm ở toạ độ (1268, 2142).

Xem tận mắt bot "nhìn thấy" gì (vẽ vòng đỏ lên các nút tìm được, lưu vào `debug/`):

```bash
.venv/bin/python nhan_dien.py --ve debug/ samples/tab_s7_man_afk.png
```

**Chạy toàn bộ bài kiểm tra** (làm việc này trước và sau mỗi lần sửa):

```bash
.venv/bin/python test_nhan_dien.py && .venv/bin/python test_thanh_tich.py && .venv/bin/python test_so_ai.py && .venv/bin/python test_leo_ai.py
```

Mất khoảng 1-2 phút. Thấy `OK` ở cả 4 là đạt.

### 3.2 Chạy bot thật (cần điện thoại)

1. Trên điện thoại: bật **Tùy chọn nhà phát triển** → **Gỡ lỗi USB**. Cắm cáp, bấm "Cho phép" trên máy.
2. Kiểm tra máy tính đã thấy điện thoại: `adb devices` phải liệt kê 1 máy ở trạng thái `device`.
3. Mở game ở Màn AFK, rồi:

```bash
.venv/bin/python leo_ai.py --mot-tran
```

`--mot-tran` = đánh đúng 1 trận rồi dừng, an toàn để thử. Bấm `Ctrl+C` để dừng bất cứ lúc nào. Xem mọi tuỳ chọn:
`.venv/bin/python leo_ai.py --help`.

> **Cẩn thận:** bot bấm thật trên tài khoản thật. Nút "Chiến Đấu Tự Động" bắt đầu trận **ngay lập tức**. Chỉ chạy bot
> trên máy/tài khoản đã được cho phép thử.

### 3.3 App Android

Cần Android SDK (Android Studio cài sẵn) và JDK 17. Mở thư mục `android/` bằng Android Studio, hoặc dùng dòng lệnh
trong thư mục `android/`:

```bash
./gradlew :vision:test
```

(chạy bài kiểm tra đối chiếu với Python, không cần điện thoại)

```bash
./gradlew installDebug
```

(build và cài bản thử lên điện thoại đang cắm). Bản phát hành: `./gradlew phatHanh` (cần file khóa ký
`android/keystore.properties`, hỏi người phụ trách; file này không nằm trên git).

---

## 4. Kiến thức nền: ảnh số và OpenCV

### 4.1 Ảnh là một bảng số

Ảnh chụp màn hình Tab S7 là một bảng **2560 hàng × 1600 cột** điểm ảnh (pixel). Mỗi điểm có 3 số 0-255 cho 3 màu.
OpenCV xếp 3 màu theo thứ tự **B, G, R** (xanh dương, xanh lá, đỏ) chứ không phải RGB như thường thấy.

Trong Python, ảnh là một mảng `numpy` có `shape = (cao, rộng, 3)`:

```python
img = cv2.imread("samples/tab_s7_man_afk.png")
img.shape          # (2560, 1600, 3)
img[100, 50]       # điểm ở HÀNG 100, CỘT 50 → ví dụ [ 34  67 200] (B=34, G=67, R=200: màu đỏ)
```

> **Bẫy số 1:** toạ độ màn hình viết `(x, y)` = (cột, hàng), nhưng mảng ảnh truy cập `img[y, x]` = [hàng, cột].
> Cắt một vùng chữ nhật từ (x0, y0) tới (x1, y1): `img[y0:y1, x0:x1]`.

Gốc toạ độ (0, 0) là **góc trên trái**. x tăng sang phải, y tăng xuống dưới.

### 4.2 Các phép xử lý ảnh dùng trong dự án

Chỉ có khoảng 10 hàm OpenCV được dùng. Hiểu chúng là hiểu gần hết phần nhận diện.

| Hàm | Làm gì | Dùng ở đâu |
|---|---|---|
| `cv2.imread(đường_dẫn)` / `cv2.imwrite` | đọc / ghi file ảnh | khắp nơi |
| `cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)` | phóng to / thu nhỏ theo hệ số k. `INTER_AREA` là cách thu nhỏ cho ảnh mịn | đưa mọi máy về cùng kích thước |
| `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)` | ảnh màu → ảnh xám (1 số mỗi điểm: độ sáng) | đo độ sáng, đọc chữ |
| `cv2.cvtColor(img, cv2.COLOR_BGR2HSV)` | đổi sang hệ màu HSV (xem 4.3) | tìm vùng theo màu |
| `cv2.inRange(hsv, thấp, cao)` | điểm nào có màu nằm trong khoảng → trắng, còn lại đen | `hsv_mask()` trong `so_ai.py` |
| `cv2.matchTemplate(vùng, mẫu, cv2.TM_CCOEFF_NORMED)` | trượt ảnh mẫu khắp vùng, chấm điểm giống nhau ở mỗi vị trí (xem 4.4) | **trái tim** của `nhan_dien.py` |
| `cv2.minMaxLoc(kết_quả)` | tìm điểm cao nhất và vị trí của nó | đi kèm `matchTemplate` |
| `cv2.connectedComponentsWithStats(ảnh_trắng_đen)` | tìm các "cụm" điểm trắng dính liền nhau, cho biết hộp bao quanh mỗi cụm | tách từng chữ số |
| `cv2.dilate(ảnh, nhân)` | làm nét chữ dày thêm 1 điểm | so chữ ký tên (`giong_ten`) |
| `cv2.absdiff(a, b)` | hiệu từng điểm giữa 2 ảnh | phát hiện danh sách tướng hết trôi |

### 4.3 Vì sao dùng HSV để tìm màu

Trong BGR, "màu đỏ" khó mô tả vì đỏ sáng, đỏ tối, đỏ nhạt có 3 số rất khác nhau. HSV tách màu thành:

- **H** (Hue, sắc): loại màu. OpenCV dùng thang 0-180: đỏ ≈ 0-10 và 170-180, cam ≈ 10-25, xanh lá ≈ 35-85,
  xanh dương ≈ 100-120.
- **S** (Saturation, độ đậm): 0 = xám/trắng, 255 = màu rực.
- **V** (Value, độ sáng): 0 = đen, 255 = sáng nhất.

Ví dụ trong `so_ai.py`, tìm ô đỏ chứa số ải: lấy điểm có H trong 0-10 **hoặc** 170-180, S ≥ 100, V ≥ 150:

```python
do = hsv_mask(dai, (0, 100, 150), (10, 255, 255)) | hsv_mask(dai, (170, 100, 150), (180, 255, 255))
```

`hsv_mask` trả về mảng True/False cùng kích thước ảnh. `.mean()` của mảng này = tỉ lệ điểm thoả màu (0-1). Code hay
viết `mask.mean() > 0.25` nghĩa là "hơn 25% vùng này có màu đó".

### 4.4 Khớp mẫu (template matching): cách bot "thấy" một nút

Ý tưởng: cắt sẵn ảnh nhỏ của nút "Chiến Đấu" (ảnh mẫu). Khi có ảnh chụp mới, trượt ảnh mẫu qua từng vị trí trong một
vùng, ở mỗi vị trí tính một điểm "giống nhau" từ -1 tới 1. Điểm cao nhất ≥ ngưỡng (thường 0.8) → thấy nút, tâm nút là
vị trí đó.

```python
r = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)   # bảng điểm cho mọi vị trí
_, score, _, (mx, my) = cv2.minMaxLoc(r)                 # điểm cao nhất và góc trên trái ở đó
```

`TM_CCOEFF_NORMED` có một tính chất quý: **ảnh tối đều đi hay sáng đều lên thì điểm không đổi**. Nhờ vậy bot vẫn nhận
ra màn hình khi lớp khóa Game Booster làm tối cả màn hình (xem chú thích trong `nhan_dien.py`).

Hạn chế: mẫu phải **cùng kích thước** với thứ cần tìm trên ảnh. Vì vậy trước khi so, mọi ảnh đều được đưa về cùng một
khổ (xem 6.1).

### 4.5 Đọc chữ số không cần OCR

Dự án không dùng thư viện đọc chữ (OCR). Game dùng một font cố định, nên làm thủ công:

1. Cắt vùng có con số, biến thành ảnh trắng đen (chữ = trắng). Ví dụ chữ màu kem sáng: `xam > 185`.
2. `connectedComponentsWithStats` tách từng cụm trắng = từng chữ số. Chữ dính nhau thì cắt theo bề rộng dự kiến
   (`_ky_tu()` trong `thanh_tich.py`).
3. Mỗi chữ số được cắt sát rồi co về đúng 24×32 điểm (`chuan_hoa()`).
4. So với các mẫu trong `templates/vi/luc_chien/` (`0_0.png`, `0_1.png`, …, `M_0.png`): đếm tỉ lệ điểm trùng. Mẫu
   giống nhất (≥ 0.65 **và** hơn mẫu thứ hai ít nhất 0.05) là kết quả; không đủ chắc thì trả `"?"`.

Tên file mẫu `9_d1.png`: ký tự `9`, chữ `d` = mẫu lấy ở màn đội hình (nét hơi khác Thành Tích), `1` = mẫu thứ hai.

---

## 5. Python đủ dùng cho dự án này

Không cần học hết Python. Đây là những cú pháp xuất hiện trong code, kèm ví dụ lấy từ dự án.

```python
# Biến, kiểu dữ liệu
x = 5                    # số nguyên
k = 0.8                  # số thực
ten = "man_afk"          # chuỗi
co = True                # đúng/sai (True / False)
khong_co = None          # "không có giá trị" (giống null)

# Danh sách (list), bộ (tuple), từ điển (dict), tập (set)
ds = [1, 2, 3]           # list: sửa được.  ds[0] = 1, ds[-1] = 3 (phần tử cuối)
hop = (114, 1195, 490, 1290)   # tuple: không sửa được. x0, y0, x1, y1 = hop  (mở gói)
nut = {"man_afk_chien_dau": (1266, 2142)}   # dict: tên → giá trị.  nut["man_afk_chien_dau"]
"man_afk_chien_dau" in nut     # True: có khoá này không?
nut.get("abc")                 # None nếu không có (không lỗi)

# Chuỗi có chèn giá trị (f-string)
log.info(f"Đánh ải {ai} với {doi}")      # {…} được thay bằng giá trị.  {x:.0%} = phần trăm, {x:.1f} = 1 chữ số lẻ

# Câu điều kiện và vòng lặp - THỤT ĐẦU DÒNG là cú pháp (4 dấu cách), không có { }
if diem >= 0.8:
    ...
elif diem >= 0.6:
    ...
else:
    ...
for i, d in enumerate(ds):     # i = 0, 1, 2…  d = phần tử
    ...

# Viết gọn
a = x if dieu_kien else y                         # toán tử 3 ngôi
ung = [i for i, d in enumerate(ds) if dung(d)]    # list comprehension: lọc ra danh sách mới
tot = next((i for i in ung if not ds[i].thieu_khung), None)   # phần tử đầu tiên thoả, không có thì None
any(cung_doi(d, x) for x in da_thu)               # có ít nhất một cái thoả?
all(thay(t) for t in can)                         # tất cả đều thoả?

# Hàm và lớp
def trieu(luc_chien):            # định nghĩa hàm
    """Chú thích của hàm (docstring)."""
    return float(luc_chien[:-1])  # "287M"[:-1] = "287"  (cắt bỏ ký tự cuối)

class NhanDien:
    def __init__(self, tpl_dir=TPL_DIR):   # hàm khởi tạo; tpl_dir có giá trị mặc định
        self.mau = {}                       # self = chính đối tượng (giống this)
    def tim(self, small, ten): ...

@dataclass                                  # lớp chỉ chứa dữ liệu: Python tự viết __init__
class CheDo:
    ten: str
    thua: int = 0
    da_thu: list = field(default_factory=list)   # mỗi đối tượng một list riêng (đừng viết = [])

# Gợi ý kiểu (type hint): chỉ để người đọc / công cụ hiểu, Python không kiểm tra khi chạy
def doc(self, img) -> DoiThanhTich | None: ...    # trả về DoiThanhTich hoặc None

# Ngoại lệ
class Dung(Exception): ...          # tự định nghĩa loại lỗi
raise Dung("Đã chạy đủ 3 giờ.")      # ném lỗi → thoát khỏi mọi vòng lặp tới chỗ bắt
try:
    bot.chay()
except Dung as e:                    # bắt lỗi
    log.info("DỪNG: %s", e)
finally:                             # luôn chạy, dù có lỗi hay không
    ...

# Mở file an toàn (tự đóng)
with TRAN_CSV.open("a", encoding="utf-8") as f: ...

# Đường dẫn
from pathlib import Path
BASE = Path(__file__).resolve().parent     # thư mục chứa file .py này
TPL_DIR = BASE / "templates" / "vi"        # dấu / nối đường dẫn

# Chạy file như chương trình
if __name__ == "__main__":     # chỉ chạy main() khi gọi "python file.py", không chạy khi file khác import nó
    main()
```

**numpy** (thư viện mảng số) - những gì hay gặp:

```python
img[y0:y1, x0:x1]          # cắt vùng
g > 185                    # so từng điểm → mảng True/False (ảnh trắng đen)
mask.mean()                # tỉ lệ điểm True
mask.sum(axis=0)           # tổng theo từng CỘT (axis=1: theo từng hàng)
np.nonzero(mask)           # toạ độ các điểm True: (mảng y, mảng x)
a & b, a | b, ~a           # và / hoặc / phủ định từng điểm
```

**`getattr` gọi hàm theo tên** - cách `leo_ai.py` chọn hàm xử lý cho từng màn hình:

```python
getattr(self, f"xu_ly_{k.man_hinh}")(img, k)
# màn "thang" → gọi self.xu_ly_thang(img, k); màn "bai" → self.xu_ly_bai(img, k)
```

Hệ quả: **thêm tên màn hình mới vào `MAN_HINH` thì bắt buộc thêm hàm `xu_ly_<tên>` trong `LeoAi`**, nếu không bot sẽ
lỗi `AttributeError` ngay khi gặp màn đó.

**logging**: `log.info(...)` hiện ra màn hình và ghi vào `leo_ai.log`; `log.debug(...)` chỉ ghi vào file (hiện ra màn
hình khi chạy với `--debug`); `log.warning(...)` cho cảnh báo.

---

## 6. Các ý tưởng chính của dự án

### 6.1 Máy gốc 1600×2560 và cách quy đổi sang máy khác

Mọi toạ độ trong code được đo trên **Tab S7 (1600 rộng × 2560 cao)**, gọi là "máy gốc" (`REF_W`, `REF_H`). Máy khác
có độ phân giải khác, nên phải quy đổi. Quan sát được về cách game co giãn giao diện:

- **Chiều ngang:** giao diện co giãn theo tỉ lệ `rộng màn hình / 1600`.
- **Chiều dọc:** máy dài hơn thì phần giữa giãn ra. Nên mỗi mẫu phải nói nó **bám vào đâu** (`neo`):
  - `"tren"`: cách mép trên một khoảng cố định (tiêu đề, đồng hồ trận).
  - `"duoi"`: cách mép dưới một khoảng cố định (hàng nút dưới đáy).
  - `"giua"`: cách tâm màn hình một khoảng cố định (bảng hiện giữa màn).

Để chạy nhanh, ảnh chụp được **thu nhỏ về rộng 800** (`WORK_W`, bằng 1/2 máy gốc) trước khi tìm mẫu. Ảnh mẫu cũng được
thu nhỏ 1/2 lúc nạp.

Hàm `_vung()` trong `nhan_dien.py` tính vùng tìm của một mẫu trên ảnh thu nhỏ. Ví dụ tính tay cho nút
`man_afk_chien_dau` (hộp gốc `(1043, 2095, 1490, 2190)`, `neo="duoi"`, `le=80`) trên máy 1080×2340:

```
Ảnh thu nhỏ: rộng 800, cao 2340 × 800/1080 ≈ 1733
x: 1043 × 0.5 − 40 = 481        1490 × 0.5 + 40 = 785          (le 80 px gốc = 40 px thu nhỏ)
y (bám đáy): 1733 − (2560 − 2095) × 0.5 − 40 = 1460
             1733 − (2560 − 2190) × 0.5 + 40 = 1588
→ chỉ tìm nút trong khung (481, 1460) – (785, 1588), không tìm cả màn hình.
```

`le` (lề) là khoảng nới thêm quanh vị trí gốc, phòng khi máy khác lệch vài chục điểm. Tìm trong vùng nhỏ vừa nhanh vừa
tránh khớp nhầm thứ giống mẫu ở chỗ khác.

### 6.2 Mẫu (`MAU`), màn hình (`MAN_HINH`), nút thêm (`NUT_THEM`)

Ba bảng ở đầu `nhan_dien.py` là "bộ não" nhận diện. Hầu hết việc sửa nhận diện chỉ là sửa 3 bảng này.

```python
MAU = {
    # tên mẫu:          Mau(ảnh nguồn trong samples/,  hộp cắt x0,y0,x1,y1,   neo,   le,  nguong=…)
    "man_afk_chien_dau": Mau("tab_s7_man_afk", (1043, 2095, 1490, 2190), "duoi"),
    "danh_giay":         Mau("tab_s7_dang_danh", (1420, 30, 1590, 150), "tren", 40, nguong=0.9),
}
```

Mỗi mẫu ghi **nó được cắt từ ảnh nào, ở hộp nào**. `tao_mau.py` đọc bảng này và cắt ra `templates/vi/<tên>.png`.
Muốn đổi mẫu: sửa hộp hoặc ảnh nguồn rồi chạy lại `tao_mau.py`.

```python
MAN_HINH = [
    ("nghi",            ["nghi_nhan_tiep_tuc"]),
    ("thanh_tich",      ["tt_sao_chep", "tt_nhan_de_dong"]),     # phải thấy CẢ HAI mẫu
    ("bai",             ["bai_thu_lai"]),
    ...
]
```

Xét **từ trên xuống**, màn hình đầu tiên thấy đủ mọi mẫu trong danh sách là kết quả. **Thứ tự rất quan trọng**: màn
nào có thể "trùng" một phần với màn khác thì phải đứng trước. Ví dụ bảng Thành Tích hiện đè lên màn đội hình, nên
`thanh_tich` đứng trước `doi_hinh`; nếu đảo lại, bot sẽ tưởng đang ở màn đội hình. Một tên màn có thể xuất hiện nhiều
dòng (nhiều cách nhận ra cùng một màn).

```python
NUT_THEM = {"man_afk": ["man_afk_chien_dau", "man_afk_huyen_linh", "nut_quay_lai", ...]}
```

Khi đã biết màn hình, tìm thêm các mẫu này để biết vị trí nút sẽ bấm. Kết quả nằm trong `KetQua.nut`
(tên mẫu → toạ độ tâm trên ảnh gốc). Code bấm nút bằng tên: `self.bam(k, "man_afk_chien_dau")`.

Hai màn hình đặc biệt không nằm trong bảng:

- `"khoa"`: ảnh tối (độ sáng trung bình < 60), thường là lớp khóa Samsung Game Booster.
- `"khong_ro"`: không màn nào khớp, thường đang chuyển cảnh. Bot chờ rồi chụp lại; quá 60 giây thì lưu ảnh và báo.

### 6.3 Mốc (anchor) và độ dời

Đọc số liệu (lực chiến, số ải) cần biết **chính xác** vị trí con số. Nhưng bảng có thể nằm lệch lên xuống tuỳ máy. Cách
giải: tìm một mẫu "mốc" ở gần (ví dụ biểu tượng nắm đấm `tt_nam_dam` cạnh lực chiến), so vị trí tìm được với vị trí ở
máy gốc → được độ dời `(dx, dy)`, rồi cộng độ dời này vào mọi vùng cần đọc.

```python
# thanh_tich.py
dx = vt[0] * 2 - (MOC[0] + MOC[2]) / 2       # vt: tâm mốc tìm được (ảnh thu nhỏ, nhân 2 về máy gốc)
dy = vt[1] * 2 - (MOC[1] + MOC[3]) / 2
VUNG_LUC_CHIEN = (368, 692, 560, 758)        # vùng "287M" ở máy gốc
vung = (368 + dx, 692 + dy, 560 + dx, 758 + dy)
```

### 6.4 Nhận ra đội theo nội dung, không theo vị trí

Thứ tự 10 đội trong Thành Tích **đổi sau mỗi lần mở bảng**. Nên bot không nhớ "đã thử đội số 3" mà nhớ "đã thử đội của
người tên X có lực chiến 287M". Tên người chơi không đọc thành chữ được (đủ loại ký tự), nên bot lưu **chữ ký ảnh**: ảnh
trắng đen 128×24 của dòng tên. Hai chữ ký giống nhau ≥ 0.85 (`giong_ten`) và cùng lực chiến → cùng đội (`cung_doi`).

### 6.5 Máy trạng thái: mỗi vòng làm đúng một việc

`LeoAi.chay()` là vòng lặp vô tận: chụp → nhận diện → gọi `xu_ly_<màn hình>` → lặp lại. Mỗi hàm xử lý chỉ làm **một
việc nhỏ** (bấm một nút, hoặc chờ) rồi trả về. Bot **không** viết kịch bản dài kiểu "bấm A, chờ 2 giây, bấm B, chờ…",
vì chỉ cần một hộp thoại lạ chen vào là kịch bản sai hết. Thay vào đó, sau mỗi lần bấm bot nhìn lại màn hình và quyết định
từ đầu. Đi lạc đâu cũng tự tìm được đường về.

Những gì bot cần **nhớ** giữa các vòng nằm trong thuộc tính của `LeoAi` và `CheDo` (mỗi chế độ leo một `CheDo`): đội
đang dùng, đã thua mấy trận, đã thử những đội nào ở ải này, có cần chép đội khác không…

Bảng tóm tắt hành vi:

| Màn hình | Bot làm |
|---|---|
| `khoa` | màn hình tắt → chờ; bị Game Booster khóa → chạm cho ổ khóa hiện rồi vuốt ổ khóa lên |
| `nghi`, `phan_thuong_afk`, `bang_ban_goi` | bấm "Nhấn để tiếp tục" / "Nhận" / "Nhấn để thoát" (không bao giờ bấm mua) |
| `ban_do` | bấm nút về Màn AFK |
| `man_afk` | đọc số ải; chọn chế độ (đổi chế độ nếu chế độ hiện tại kẹt); bấm Chiến Đấu / Thách Đấu Huyền Linh |
| `doi_hinh` | cần đổi đội → mở Thành Tích; chưa → đọc lực chiến đội, bấm Chiến Đấu |
| `thanh_tich` | đọc các đội, chọn đội chưa thử tốt nhất, bấm Sao chép |
| `thanh_tich_trong` | bảng trống (mọi bản ghi cần tướng chưa có) → đánh dấu chế độ này kẹt, đóng bảng |
| `dang_danh` | chờ; trận quá 5 phút thì cảnh báo |
| `thang` | tính thắng, ghi `tran.csv`, sang ải mới, bấm Chiến Đấu đánh ải kế |
| `bai` | tính thua; thua đủ số trận → về để chép đội khác; chưa đủ → Thử Lại |
| `xu_ly_ngam`, `xu_ly_xong`, `tu_dong_hoan_tat` | chế độ Tự Động Xử Lý (game tự đánh ngầm nhiều ải): chờ, rồi đọc kết quả chuỗi |
| `dai_dien_chon` | (chỉ `--leo-ho`) bảng chọn ải của người nhờ: bấm Thách Đấu Huyền Linh / Chiến Đấu theo chế độ đang leo |
| `dai_dien_thang` | (chỉ `--leo-ho`) THẮNG leo hộ: tính thắng, bấm Tiếp Theo (không có tiến trình; ải đọc ở tiêu đề màn đội hình) |
| `khong_ro` | chờ; quá 60 giây → lưu ảnh vào `debug/` và cảnh báo |

Leo hộ (`--leo-ho`, Đại Diện Tác Chiến): màn đội hình leo hộ vẫn là `doi_hinh` nhưng có cờ `k.dai_dien` (không có nút
Chiến Đấu Tự Động). Ở chế độ này bot không bao giờ bấm ← (chưa biết nó có đưa ra khỏi phiên không), thua thì Thử Lại,
và coi bản đồ / Màn AFK / đội hình của bạn là dấu hiệu phiên đã kết thúc.

### 6.6 Chú thích ghi bằng chứng

Bạn sẽ thấy nhiều chú thích kiểu `# Đo 13/10: đội chép thắng 42% ở trận đầu nhưng chỉ 6-7% ở trận 2-3`. Đó là **lý do**
của một con số hay một quyết định, đo trên máy thật. Trước khi sửa một con số, đọc chú thích đó; khi sửa, **ghi lại bằng
chứng mới** theo cùng kiểu (ngày, đã đo gì, kết quả). Đừng xoá các chú thích này.

---

## 7. Đi qua từng file Python

### `adb.py` - tay và mắt của bản PC

Lớp `Adb` chạy lệnh `adb` bằng `subprocess` (gọi chương trình ngoài):

- `screenshot()`: chụp màn hình. Thử 2 cách lấy ảnh thô (nén gzip / không nén), đo cách nào nhanh hơn thì dùng; lỗi thì
  quay về PNG. Trả về ảnh BGR như `cv2.imread`.
- `tap(x, y)`, `swipe(x0, y0, x1, y1, ms)`: chạm, vuốt (lệnh `input tap` của Android).
- `game_booster_locked()`, `screen_awake()`, `charging()`, `foreground_package()`: đọc trạng thái máy bằng `dumpsys`.
- Lỗi adb → ném `AdbError`. `leo_ai.main()` bắt lỗi này, chờ 20 giây rồi chạy tiếp (ví dụ khi rút cáp tạm).

### `nhan_dien.py` - đang ở màn nào?

- Các bảng `MAU`, `MAN_HINH`, `NUT_THEM` (mục 6.2).
- `NhanDien.__init__`: nạp mọi ảnh mẫu, thu nhỏ 1/2. Thiếu mẫu → báo "chạy tao_mau.py".
- `_vung(m, h_work)`: vùng tìm của mẫu (mục 6.1).
- `tim(small, ten)`: khớp một mẫu, trả `(điểm, tâm)`.
- `nhan_dien(img) -> KetQua`: hàm chính. Đo độ sáng → nếu tối thì `khoa` (trừ khi thấy mẫu Tự Động Xử Lý) → duyệt
  `MAN_HINH` → tìm `NUT_THEM` → đổi toạ độ về ảnh gốc → nếu là màn đội hình thì xác định chế độ theo tiêu đề.
  Hàm con `thay(ten)` nhớ điểm đã tính để mỗi mẫu chỉ khớp một lần.
- `KetQua`: `man_hinh`, `nut` (tên → (x, y)), `diem` (tên → điểm), `do_sang`, `che_do`.
- Chạy trực tiếp với `--diem` để in điểm khớp của mọi mẫu (dùng khi chỉnh ngưỡng), `--ve` để vẽ.

### `so_ai.py` - đọc số

- `ChuSo`: nhận dạng một ký tự bằng mẫu (mục 4.5). `doc_so(ảnh_trắng_đen)` đọc cả dãy số.
- `DocSoAi.ai_man_afk(img)`: tìm ô đỏ lớn nhất trên dải đường ải, đọc chữ trắng trong đó.
- `DocSoAi.tien_trinh_thang(img)`: đọc "751 → 752" ở màn THẮNG (số trước màu kem, số sau màu xanh lá).
- `tien_trinh_tu_dong(img)`: cùng thứ đó trên bảng kết quả Tự Động Xử Lý.
- Các hàm tiện ích dùng chung: `cat(img, hop)` (cắt an toàn, không lỗi khi hộp ra ngoài ảnh), `hsv_mask`, `chuan_hoa`.

### `thanh_tich.py` - đọc một đội trong bảng Thành Tích

- `DoiThanhTich`: kết quả đọc - `chu_ky` (chữ ký tên), `luc_chien` ("287M"), `nhan` (`cuc_han` / `phu_hop` /
  `chua_xep_hang` / None), `ly_tuong`, `thu_cong` (Chiến Đấu Thủ Công: bot không dùng được vì không tung chiêu tay),
  `loc_bat` (ô lọc "chỉ đội đã sở hữu" đang bật?), `thieu_khung`.
- `DocThanhTich.doc(img)`: tìm mốc nắm đấm → đọc lực chiến → đọc nhãn theo **màu nền** (đỏ = Cực Hạn, xanh = Phù Hợp) →
  tìm thẻ người chơi đang chọn (đoạn **màu cam** dài nhất trên thanh thẻ) → cắt tên làm chữ ký, kiểm tra "Thủ Công" và
  "Lý Tưởng".
- `luc_doi(img)`: lực chiến đội của bạn ở màn đội hình ("338,210K" → 338.21 triệu).
- `cung_doi(a, b)`, `giong_ten(a, b)`, `o_loc_bat(img)`.
- `dai_tuong(img)`: cắt dải 5 thẻ tướng của đội (dùng cho so khung tướng và thống kê).

### `leo_ai.py` - chương trình chính

Đọc theo thứ tự này:

1. **Hằng số đầu file** (`CHO_SAU_BAM = 1.5`, …): các thời gian chờ và giới hạn. Mỗi cái có chú thích.
2. **`CheDo`**: trạng thái leo của một chế độ ở ải hiện tại. Đọc kỹ chú thích từng trường.
3. **`main()`** (cuối file): đọc tham số dòng lệnh (`argparse`), cấu hình nhật ký, kết nối máy, bật "giữ màn hình sáng",
   chạy `bot.chay()`, trả lại cài đặt cũ khi thoát. Mọi tham số có giá trị mặc định và chú thích `help=`.
4. **`chay()`**: vòng lặp (mục 6.5).
5. **Các hàm `xu_ly_*`**: mỗi màn một hàm.
6. **Phần Thành Tích**: `xu_ly_thanh_tich` → `ve_doi_dau` (chờ bảng đứng yên, bật/tắt ô lọc, về đội đầu) → `doc_tiep`
   (đọc lần lượt tới đội cuối) → `chon_doi` (chọn đội) → bấm mũi tên tới đội đã chọn → `chep` (bấm Sao chép).
   `chup_doi()` chụp tới khi 2 lần đọc liên tiếp giống nhau (bảng còn trượt sau khi bấm mũi tên).

Logic chọn đội (`chon_doi` + `dung_duoc`), tóm tắt:

- Bỏ đội Chiến Đấu Thủ Công, đội đã thử ở ải này, đội Cực Hạn nếu chọn `--cuc-han bo`.
- Còn lại: theo **thứ tự của game** (game đã xếp theo khả năng thắng của tài khoản).
- Vòng 2 (`--so-vong`): ưu tiên đội có tỉ lệ lực chiến cao.
- Đội "thiếu khung" (bản ghi có tướng có khung mà tướng đó của bạn không khung) để cuối cùng.
- **Chép thử** (`--nguong-luc 0.95`): chép xong, ở màn đội hình đọc lực chiến đội bạn; thấp hơn 95% lực chiến bản ghi thì
  chưa đánh, hoãn lại và chép thử đội kế. Hết đội thì đánh các đội đã hoãn, tỉ lệ cao trước.
- Chép nhanh: nếu đội đứng đầu dùng được và không thiếu khung, chép luôn không cần đọc cả 10 đội.

`test_leo_ai.py` kiểm tra logic này trên 20 đội đọc từ ảnh mẫu, **không cần máy**. Sửa logic chọn đội thì thêm test ở đây.

### `doc_tuong_cua_toi.py`, `thong_ke_tuong.py`, `tao_thu_vien_tuong.py` - khung tướng

Phần phức tạp nhất, ít khi cần sửa. Ý tưởng:

- Mỗi đội có 5 thẻ tướng. Thẻ **có khung** (phẩm chuẩn) có hàng sao ở mép trên; thẻ **không khung** (phẩm thấp) thì không.
  Đội chép về mà tướng của bạn không khung trong khi bản ghi có khung → thường thua (đã đo).
- `thong_ke_tuong.py`: tách thẻ, so **ảnh mặt tướng** để gom thẻ cùng tướng, phân loại khung (điểm khớp mẫu ngôi sao;
  lưng chừng thì so viền với các thẻ đã biết - thuật toán "k láng giềng gần nhất").
- `tao_thu_vien_tuong.py`: đóng gói kết quả thành thư viện `templates/vi/tuong/` (mặt tướng đã đặt tên, tỉ lệ có khung).
- `doc_tuong_cua_toi.py`: mở màn đội hình, vuốt danh sách tướng của bạn, đọc khung từng tướng → `tuong_cua_toi.json`.
  Lớp `SoKhung` được `leo_ai.py` dùng để gắn cờ `thieu_khung` cho đội trong Thành Tích.

### `tao_mau.py` - sinh ảnh mẫu

Cắt mọi mẫu trong `MAU`, các mẫu chữ phụ, mẫu chữ số (tách từ ảnh Thành Tích đã biết lực chiến trong
`samples/thanh_tich/nhan.txt`), và xuất `templates/vi/mau.json` cho app Android. **Chạy lại mỗi khi sửa `MAU`.**

### Các bài kiểm tra `test_*.py`

| File | Kiểm tra | Đáp án lấy từ |
|---|---|---|
| `test_nhan_dien.py` | mọi ảnh mẫu được nhận đúng màn hình; mọi mẫu đều được dùng; ảnh thu nhỏ vẫn nhận đúng | `samples/nhan.txt` |
| `test_thanh_tich.py` | đọc đúng lực chiến, nhãn, tên của 20 đội, cả ở ảnh rộng 1080 | `samples/thanh_tich/nhan.txt` |
| `test_so_ai.py` | đọc đúng số ải | trong file test |
| `test_leo_ai.py` | logic chọn đội, chép thử, so khung, đổi chế độ khi một phần hết ải | trong file test |

`test_nhan_dien.py --bien` in "biên an toàn" của từng mẫu: điểm thấp nhất trên ảnh đúng và điểm cao nhất trên ảnh sai.
Ngưỡng nên nằm giữa hai số đó, cách xa cả hai.

---

## 8. Kotlin và Android đủ dùng

### 8.1 Kotlin so với Python

Kotlin là ngôn ngữ chính của Android, chạy trên máy ảo Java. Khác Python: **có kiểu dữ liệu chặt**, dùng `{ }` thay cho
thụt đầu dòng, phải biên dịch trước khi chạy. Bảng đối chiếu với code dự án:

| Python | Kotlin | Ghi chú |
|---|---|---|
| `x = 5` | `val x = 5` / `var x = 5` | `val` không gán lại được, `var` gán lại được |
| `None` | `null` | |
| `d: DoiThanhTich \| None` | `d: DoiThanhTich?` | dấu `?` = được phép null |
| `x.a if x is not None else None` | `x?.a` | gọi an toàn: x null thì cả biểu thức null |
| `a if a is not None else b` | `a ?: b` | toán tử Elvis |
| `def f(a, b=1):` | `fun f(a: Int, b: Int = 1): Int {` | |
| `f"Ải {ai}"` | `"Ải $ai"`, `"Ải ${k.manHinh}"` | |
| `[x for x in ds if ok(x)]` | `ds.filter { ok(it) }` | `it` = tham số ngầm của lambda |
| `[f(x) for x in ds]` | `ds.map { f(it) }` | |
| `next((x for x in ds if ok(x)), None)` | `ds.firstOrNull { ok(it) }` | |
| `any(...)`, `all(...)` | `ds.any { }`, `ds.all { }` | |
| `{"a": 1}` | `mapOf("a" to 1)` | `a to b` tạo một cặp `Pair(a, b)` |
| `x, y = k.nut[nut]` | `val (x, y) = k.nut[nut]` | mở gói |
| `@dataclass class A: ...` | `data class A(val x: Int)` | |
| `if / elif / else` | `when (x) { "a" -> ...; "b" -> ...; else -> ... }` | xem vòng lặp `Leo.chay()` |
| `raise Dung("...")` | `throw StopBot("...")` | |
| `time.sleep(1.5)` | `delay(1500)` | **mili giây**, và chỉ dùng trong hàm `suspend` |
| `snake_case` | `camelCase` | `xu_ly_doi_hinh` → `xuLyDoiHinh`, `man_hinh` → `manHinh` |

Vài thứ Kotlin có mà Python không có:

```kotlin
lateinit var nd: NhanDien          // "sẽ gán sau", truy cập trước khi gán thì lỗi
private val tt by lazy { DocThanhTich(svc.nd) }   // chỉ tạo lần đầu dùng tới
object AppLog { ... }              // đối tượng duy nhất trong cả app (singleton)
companion object { var instance: BotService? = null }   // giống biến của lớp (static)
fun Mat.cat(...): Mat { ... }      // "hàm mở rộng": thêm hàm cat() cho lớp Mat của OpenCV
k.nut[nut] ?: run { delay(CHO_KHONG_RO); return }   // không có nút thì chờ rồi thoát hàm
```

### 8.2 Coroutine và `suspend`: chờ mà không làm đơ app

Trên Android, **luồng chính** (main thread) vẽ giao diện. Nếu bot `sleep` trên luồng này, app đơ. Kotlin giải quyết bằng
**coroutine**: hàm đánh dấu `suspend` có thể "tạm dừng" (ví dụ `delay(1500)`, chờ ảnh chụp) mà không chặn luồng.

```kotlin
private suspend fun bam(k: KetQua, nut: String, cho: Long = CHO_SAU_BAM) {
    val (x, y) = k.nut[nut] ?: run { delay(CHO_KHONG_RO); return }
    svc.tap(x, y)          // cũng là suspend: chờ hệ thống báo đã chạm xong
    delay(cho)
}
```

Quy tắc: hàm `suspend` chỉ gọi được từ hàm `suspend` khác (hoặc từ `scope.launch { }`). Việc tính toán nặng (nhận diện
ảnh) được đẩy sang luồng khác bằng `cpu { ... }` = `withContext(Dispatchers.Default) { ... }`.

`BotService.runJob()` chạy tác vụ bằng `scope.launch { }`. Bấm ■ thì `job.cancel()`: coroutine bị huỷ ở lần `delay` kế tiếp
(ném `CancellationException`).

### 8.3 OpenCV trong Kotlin: nhớ giải phóng ảnh

Trong Python, ảnh tự được thu dọn. Trong Kotlin, `Mat` (ảnh của OpenCV) giữ bộ nhớ ngoài Java, **phải tự gọi
`.release()`** khi xong, nếu không app sẽ hết bộ nhớ sau vài giờ (mỗi ảnh Tab S7 ~12MB). Mẫu code luôn thấy trong dự án:

```kotlin
val (img, k) = chup()
try {
    ...                   // dùng img
} finally {
    img.release()         // luôn giải phóng, kể cả khi có lỗi
}
```

API Kotlin khác Python một chút: kết quả trả qua tham số thay vì giá trị trả về.

```python
r = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)       # Python
```
```kotlin
val r = Mat()
Imgproc.matchTemplate(roi, m.anh, r, Imgproc.TM_CCOEFF_NORMED)   // Kotlin: r là "chỗ chứa" kết quả
val mm = Core.minMaxLoc(r)
r.release()
```

Phần đọc chữ số trong Kotlin dùng lớp tự viết `Bin` (ảnh trắng đen dạng mảng `BooleanArray`, trong `SoAi.kt`) để làm
các phép mà Python làm bằng numpy (`.mean()`, cắt, đếm theo cột).

### 8.4 Các khái niệm Android dùng trong app

- **Dịch vụ Trợ năng (AccessibilityService)**: dịch vụ hệ thống dành cho app hỗ trợ người khuyết tật. App dùng 2 khả
  năng của nó thay cho ADB: `takeScreenshot()` (chụp màn hình, Android 11+) và `dispatchGesture()` (chạm, vuốt). Người
  dùng phải tự bật trong Cài đặt → Hỗ trợ. Khai báo ở `AndroidManifest.xml` và `res/xml/accessibility_service.xml`.
- **Activity**: một màn hình của app. Ở đây chỉ có `MainActivity` (màn cài đặt), giao diện trong
  `res/layout/activity_main.xml`.
- **Bảng nổi (overlay)**: cửa sổ nhỏ nổi trên game (▶ ■ ⋯ ✕), là cửa sổ của dịch vụ Trợ năng. Nó nằm trong một dải trống
  phía trên màn hình (`DAI_AN_TOAN`) để không che mẫu nhận diện; lấn ra ngoài thì được ẩn tạm lúc chụp.
- **SharedPreferences**: nơi lưu cài đặt dạng khoá-giá trị. Lớp `Prefs` trong `App.kt` bọc lại thành thuộc tính.
- **assets**: file đóng gói kèm APK. `android/app/build.gradle.kts` lấy thẳng thư mục `templates/` ở gốc dự án làm assets,
  nên app luôn dùng đúng bộ mẫu của bản Python.
- **Gradle**: công cụ build. `*.gradle.kts` là file cấu hình (viết bằng Kotlin). `versionCode` / `versionName` trong
  `android/app/build.gradle.kts` là phiên bản app.

---

## 9. App Android: cấu trúc và cách nó khớp với bản Python

### 9.1 Hai module

```
android/
├── vision/   Nhận diện ảnh. Kotlin thuần (không phụ thuộc Android) → chạy kiểm tra được trên máy tính.
│   └── src/main/kotlin/vn/afkauto/leoai/vision/
│       ├── NhanDien.kt    ← nhan_dien.py    (+ BoMau: nạp mau.json và ảnh mẫu)
│       ├── SoAi.kt        ← so_ai.py        (+ lớp Bin)
│       ├── ThanhTich.kt   ← thanh_tich.py
│       └── TheTuong.kt    ← thong_ke_tuong.py + doc_tuong_cua_toi.py (phần nhận diện thẻ tướng, khung)
└── app/      Phần Android.
    └── src/main/java/vn/afkauto/leoai/
        ├── BotService.kt  ← adb.py           (chụp, chạm, vuốt bằng Trợ năng; chạy/dừng tác vụ)
        ├── Leo.kt         ← leo_ai.py        (vòng lặp leo ải, chọn đội; + đọc danh sách tướng trên máy)
        ├── KhungTuong.kt  ← doc_tuong_cua_toi.py (phần lưu/đánh dấu khung tướng)
        ├── App.kt         cài đặt (Prefs), khởi động OpenCV
        ├── MainActivity.kt màn hình cài đặt, hướng dẫn bật Trợ năng, bảng khung tướng
        ├── Overlay.kt     bảng nổi
        ├── Status.kt      dòng trạng thái, thống kê trong ngày, thông báo (Notifier)
        └── AppLog.kt      nhật ký (hiện trên app + ghi file nhat_ky.txt)
```

Tên hàm giữ nguyên nghĩa, chỉ đổi kiểu viết: `xu_ly_man_afk` ↔ `xuLyManAfk`, `chon_doi` ↔ `chonDoi`,
`cung_doi` ↔ `cungDoi`. Muốn tìm bản Kotlin của một hàm Python: tìm tên camelCase của nó. Đầu các file Kotlin có chú thích
"Chuyển từ …py".

Khác biệt chính giữa `Leo.kt` và `leo_ai.py`:

- Python gọi hàm theo tên (`getattr`); Kotlin dùng khối `when (k.manHinh) { ... }` trong `Leo.chay()`. **Thêm màn hình
  mới thì thêm một nhánh vào `when`** (thiếu nhánh thì rơi vào `else -> xuLyKhongRo`, không lỗi nhưng bot đứng chờ).
- Tham số dòng lệnh của Python ↔ cài đặt `Prefs` trên màn hình chính (`--thu-lai` ↔ `prefs.thuLai`, …).
- Thời gian: Python tính bằng giây (`1.5`), Kotlin bằng mili giây (`1500L`).
- App có thêm: kiểm tra pin, thông báo, ghi nhớ đang chạy để dịch vụ khởi động lại thì chạy tiếp.
- Một số tính năng chỉ có ở PC, theo quyết định của chủ dự án: `--thu-thap-tuong` và thống kê tướng.

### 9.2 `mau.json`: toạ độ chỉ khai báo một chỗ

Toạ độ mẫu chỉ được viết **một lần** trong `MAU` của `nhan_dien.py`. `tao_mau.py` xuất nó ra `templates/vi/mau.json`,
và `BoMau.load()` trong `NhanDien.kt` đọc file này. Vì vậy **không sửa `mau.json` bằng tay** và không chép toạ độ mẫu vào
Kotlin.

Lưu ý: các toạ độ **khác** (vùng đọc lực chiến, vùng số ải, vị trí chạm cố định…) vẫn được khai báo ở cả hai bên (ví dụ
`VUNG_LUC_CHIEN` trong `thanh_tich.py` và `ThanhTich.kt`). Sửa một bên phải sửa bên kia; bài kiểm tra đối chiếu sẽ bắt
lỗi nếu quên.

### 9.3 Một ví dụ đối chiếu

Python (`nhan_dien.py`):

```python
for man, can in MAN_HINH:
    if all(thay(t) for t in can):
        ket.man_hinh = man
        for t in NUT_THEM.get(man, []):
            thay(t)
        break
```

Kotlin (`NhanDien.kt`):

```kotlin
for ((ten, can) in bo.manHinh) {
    if (can.all { thay(it) }) {
        man = ten
        bo.nutThem[ten]?.forEach { thay(it) }
        break
    }
}
```

Cùng một thuật toán, từng dòng tương ứng. Khi chuyển code, cố giữ cấu trúc giống hệt như vậy để dễ so.

### 9.4 Bài kiểm tra đối chiếu Python ↔ Kotlin

1. `android/vision/tao_ket_qua_python.py` chạy bản Python trên **mọi ảnh trong `samples/`** và ghi kết quả (màn hình, vị
   trí nút, điểm khớp mọi mẫu, đội Thành Tích, số ải, lực chiến, thẻ tướng…) vào
   `android/vision/src/test/resources/ket_qua_python.tsv`.
2. `PythonParityTest.kt` chạy bản Kotlin trên cùng ảnh và so với file đó (cho phép lệch nhỏ: điểm ±0.02, vị trí ±2 px, vì
   hai bên dùng phiên bản OpenCV khác nhau).

```bash
.venv/bin/python android/vision/tao_ket_qua_python.py
```

```bash
cd android && ./gradlew :vision:test
```

Chạy lại bước 1 **mỗi khi sửa thuật toán Python hoặc thêm ảnh mẫu**, rồi chạy bước 2. Bước 2 hỏng nghĩa là hai bản đã
lệch nhau: sửa Kotlin cho tới khi qua.

Python làm tròn "nửa về số chẵn" (`round(2.5) = 2`), khác cách làm tròn thông thường. Kotlin dùng hàm `pyRound()` để làm
tròn giống hệt Python. Chuyển code có `round()` thì dùng `pyRound()`.

---

## 10. Công thức cho các việc hay gặp

### 10.1 Game có màn hình / hộp thoại mới mà bot chưa biết

Dấu hiệu: nhật ký báo "Không nhận ra màn hình đã 60 giây", có ảnh trong `debug/…-khong-ro.png`.

1. **Lấy ảnh mẫu.** Dùng ảnh trong `debug/`, hoặc chụp trực tiếp khi máy đang ở màn đó:
   ```bash
   adb exec-out screencap -p > samples/tab_s7_ten_man_moi.png
   ```
   Đặt tên theo kiểu sẵn có: `tab_s7_<mô tả>.png`. Nên ở máy gốc Tab S7 (1600×2560); máy khác thì phải tự quy đổi toạ độ.
2. **Chọn vùng làm mẫu**: một chữ hay biểu tượng **chỉ có ở màn này**, **đứng yên** (không nhấp nháy, không phóng to thu
   nhỏ, không chứa số thay đổi). Mở ảnh bằng trình xem có hiện toạ độ con trỏ (GIMP, hoặc bất kỳ trình vẽ nào) để đo hộp
   `(x0, y0, x1, y1)`.
3. **Thêm vào `MAU`** trong `nhan_dien.py`, chọn `neo` đúng (vùng gần đáy → `"duoi"`, gần đỉnh → `"tren"`, bảng giữa
   màn → `"giua"` với `le` lớn hơn, khoảng 200). Kèm chú thích: mẫu là gì, gặp lúc nào, ngày nào.
4. **Thêm vào `MAN_HINH`** ở vị trí đúng thứ tự (mục 6.2), và nếu cần bấm nút khác thì thêm vào `NUT_THEM`.
5. Chạy `.venv/bin/python tao_mau.py`.
6. Ghi đáp án cho ảnh mới vào `samples/nhan.txt`: `tab_s7_ten_man_moi.png ten_man_moi`.
7. **Viết hàm xử lý** `xu_ly_ten_man_moi(self, img, k)` trong lớp `LeoAi` (`leo_ai.py`). Chỉ bấm những nút đã nhận ra
   (`self.bam(k, "ten_mau")`); chạm vào toạ độ cố định chỉ khi thật sự không có cách khác (xem `bam_dong_trong`).
8. Chạy toàn bộ test Python (mục 3.1), kèm `test_nhan_dien.py --bien` xem mẫu mới có cách biệt an toàn không.
9. Thử trên máy thật.
10. **Chuyển sang Android**: thêm nhánh vào `when` trong `Leo.chay()` (`Leo.kt`), viết hàm `xuLyTenManMoi`. Chạy
    `tao_ket_qua_python.py` rồi `./gradlew :vision:test`. Tăng `versionCode` và `versionName` trong
    `android/app/build.gradle.kts`.

Ví dụ thật để học theo: commit `ec831a1` (thêm nút Chiến Đấu ngang khi Huyền Linh hết ải). Xem nó sửa những file nào:

```bash
git show --stat ec831a1
```

### 10.2 Bot nhận nhầm màn hình hoặc không thấy nút

1. Lấy ảnh bị nhận sai, xem điểm khớp mọi mẫu:
   ```bash
   .venv/bin/python nhan_dien.py --diem debug/anh_bi_sai.png
   ```
2. Mẫu đáng lẽ thấy mà điểm thấp (ví dụ 0.75 < 0.8): game đổi giao diện một chút, hoặc máy khác lệch nhiều → cắt lại mẫu
   từ ảnh mới, hoặc tăng `le`, hoặc thêm một dòng `MAN_HINH` dùng mẫu khác cho cùng màn.
3. Mẫu không đáng thấy mà điểm cao: mẫu không đủ đặc trưng → chọn vùng khác, hoặc tăng `nguong` cho riêng mẫu đó
   (`nguong=0.9`), hoặc bắt màn đó cần thêm một mẫu nữa.
4. **Thêm ảnh bị sai vào `samples/` và `nhan.txt`** để lỗi này không bao giờ quay lại. Chạy toàn bộ test.

**Đừng hạ ngưỡng chung `MATCH_THRESHOLD`**: sửa một chỗ sẽ làm hỏng chỗ khác. Chỉnh riêng từng mẫu.

### 10.3 Thêm một tuỳ chọn cài đặt

- PC: thêm `ap.add_argument("--ten-moi", ...)` trong `leo_ai.main()`, có `default` và `help`. Dùng trong bot qua
  `self.a.ten_moi` (gạch ngang trong tên tham số thành gạch dưới).
- Android: thêm thuộc tính trong `Prefs` (`App.kt`) theo mẫu sẵn có, thêm ô nhập vào `res/layout/activity_main.xml`, nối
  ô đó với thuộc tính trong `MainActivity.kt` (`bindNumber` / `bindCheck`). Bot đọc qua `prefs.tenMoi`.
- `test_leo_ai.py` tạo bot bằng hàm `bot()` với đủ mọi tham số: thêm tham số mới vào đó, nếu không test sẽ lỗi.
- Cập nhật README.

### 10.4 Sửa logic chọn đội

Sửa `chon_doi` / `dung_duoc` trong `leo_ai.py`, viết test trong `test_leo_ai.py` (dùng các đội đọc từ ảnh mẫu có sẵn),
chạy thật đủ lâu để có số liệu (`tran.csv` ghi lại mọi trận), rồi sửa `chonDoi` / `dungDuoc` trong `Leo.kt` cho giống.
Ghi số liệu đo được vào chú thích.

### 10.5 Phát hành bản app mới

1. Tăng `versionCode` (số nguyên, luôn tăng) và `versionName` trong `android/app/build.gradle.kts`.
2. `./gradlew :vision:test` phải qua.
3. Trong `android/`: `./gradlew phatHanh` → sinh `AfkAuto-<phiên bản>.apk` ở gốc dự án.
4. Cài thử lên máy, chạy thật một lúc, rồi mới gửi đi. **Luôn ký bằng cùng một khóa**, nếu không người dùng không cài đè
   được bản cũ.

---

## 11. Gỡ lỗi khi bot chạy thật

| Nguồn | Có gì |
|---|---|
| `leo_ai.log` | nhật ký chi tiết (cả mức debug): từng lần nhận diện, từng lần bấm. Xoay vòng 3 file × 2MB |
| `.venv/bin/python leo_ai.py --debug` | in chi tiết ra màn hình luôn |
| `debug/*.png` | ảnh lúc có sự cố (màn lạ, trận quá lâu, bảng bán gói…). Giữ 200 ảnh mới nhất |
| `tran.csv` | mỗi trận một dòng: chế độ, ải, đội, lực chiến bản ghi / đội bạn, tỉ lệ, kết quả, thời gian |
| App: nút Sao chép nhật ký | nhật ký của app; file `nhat_ky.txt` trong thư mục riêng của app trên máy |
| App: bật "Lưu ảnh để tra lỗi" ở màn chính | ảnh lưu vào `Android/data/vn.afkauto.leoai/files/debug/` |

Các lệnh adb hữu ích:

```bash
adb devices
```

```bash
adb exec-out screencap -p > /tmp/anh.png && .venv/bin/python nhan_dien.py /tmp/anh.png
```

```bash
adb logcat -s AfkAuto
```

(xem nhật ký app trực tiếp khi đang cắm máy)

Cách nghĩ khi gỡ lỗi: luôn hỏi theo thứ tự **(1) bot nhận ra màn hình nào?** (xem dòng debug `[afk] thang | sáng …`)
**(2) nhận đúng chưa?** (so với ảnh) **(3) nếu đúng, hàm `xu_ly_*` của màn đó đã quyết định gì, vì sao?** (đọc trạng thái
`CheDo`). Phần lớn lỗi nằm ở bước 2.

---

## 12. Quy tắc và các bẫy hay gặp

**Quy tắc an toàn (không được phá)**

- Bot **chỉ bấm vào nút đã nhận ra**. Không nhận ra thì chờ, không bấm bừa.
- Bot **không bao giờ mua hay tiêu tài nguyên**. Bảng bán gói chỉ bấm "Nhấn để thoát".
- Không đẩy dữ liệu cá nhân lên git (`tran.csv`, `thu_thap_tuong/`, nhật ký, khóa ký app đã nằm trong `.gitignore`).

**Quy tắc làm việc**

- Chạy toàn bộ test **trước** khi sửa (để biết lúc đầu đã qua) và **sau** khi sửa.
- Mỗi lỗi sửa được nhờ một ảnh mới → **thêm ảnh đó vào `samples/` kèm nhãn**.
- Sửa Python thì chuyển sang Kotlin trong cùng đợt, chạy bài kiểm tra đối chiếu.
- Viết chú thích tiếng Việt, theo phong cách sẵn có: nói **vì sao** và **bằng chứng** (ngày, số liệu), không chỉ nói làm gì.
- Đặt tên tiếng Việt không dấu, giống code sẵn có (`so_tran_toi_da`, không `max_battles`).
- Commit nhỏ, mỗi commit một việc, lời commit tiếng Việt mô tả việc đã làm (xem `git log`).

**Các bẫy**

| Bẫy | Hậu quả | Cách tránh |
|---|---|---|
| Nhầm `img[y, x]` với `(x, y)` | cắt sai vùng, không lỗi gì nhưng kết quả sai | nhớ: mảng là [hàng, cột] |
| Quên chạy `tao_mau.py` sau khi sửa `MAU` | mẫu cũ vẫn được dùng, app Android lệch PC | chạy ngay sau khi sửa |
| Sửa `templates/vi/*.png` hoặc `mau.json` bằng tay | lần chạy `tao_mau.py` sau ghi đè mất | sửa `MAU` / ảnh trong `samples/` |
| Thêm màn vào `MAN_HINH` mà thiếu `xu_ly_<tên>` | PC: lỗi `AttributeError` khi gặp màn đó | luôn thêm cặp |
| Đặt màn mới sai thứ tự trong `MAN_HINH` | nhận nhầm sang màn khác | màn "đè lên" màn khác đứng trước |
| Chọn mẫu là chữ nhấp nháy / phóng to thu nhỏ | lúc khớp lúc không | chọn phần đứng yên (xem chú thích `xu_ly_xong_chu`) |
| Đọc số ngay sau khi bấm | game chưa cập nhật, đọc ra số cũ | chờ tới khi 2 lần đọc giống nhau (`chup_doi`, `doc_luc_doi`) |
| Nhận đội theo vị trí trong Thành Tích | thứ tự đổi mỗi lần mở bảng | luôn dùng `cung_doi` |
| Kotlin: quên `release()` ảnh `Mat` | app chậm dần rồi văng vì hết bộ nhớ | `try { } finally { img.release() }` |
| Kotlin: dùng `Math.round` thay cho `pyRound` | lệch 1 px so với Python, test đối chiếu hỏng | dùng `pyRound()` |
| Giây (Python) vs mili giây (Kotlin) | chờ 1.5 ms thay vì 1.5 giây | Kotlin luôn `1500L` |
| Thử bot bằng "Chiến Đấu Tự Động" | trận bắt đầu ngay, không dừng được | thử bằng `--mot-tran` |
| Kiểm tra chỉ trên ảnh Tab S7 | máy tỉ lệ khác (A54 1080×2340, dài hơn) có thể lệch | thêm ảnh của máy đó vào `samples/` khi có |

---

## 13. Từ điển tên biến

Code đặt tên bằng tiếng Việt không dấu. Các từ hay gặp:

| Tên | Nghĩa | | Tên | Nghĩa |
|---|---|---|---|---|
| `man_hinh` | màn hình | | `doi` | đội |
| `mau` | mẫu (ảnh mẫu) | | `doi_hinh` | màn đội hình |
| `nut` | nút | | `chep` | chép (Sao chép đội) |
| `nhan_dien` | nhận diện | | `da_thu` | đã thử |
| `diem` | điểm khớp (0-1) | | `thua`, `thang`, `bai` | thua, thắng, màn BẠI |
| `nguong` | ngưỡng | | `ket` | kẹt (thử hết đội ở ải này) |
| `neo` | mốc theo chiều dọc (tren/duoi/giua) | | `het` | hết ải (phần này không còn ải) |
| `le` | lề tìm thêm | | `hoan` | hoãn (chép thử, đánh sau) |
| `hop`, `vung` | hộp, vùng (x0, y0, x1, y1) | | `vong` | vòng thử đội |
| `moc` | mốc (để tính độ dời) | | `ty_le` | tỉ lệ lực chiến đội bạn / bản ghi |
| `dx`, `dy` | độ dời ngang, dọc | | `luc_chien`, `luc_doi` | lực chiến bản ghi, lực chiến đội bạn |
| `cat` | cắt (vùng ảnh) | | `ban_ghi` | bản ghi (một đội trong Thành Tích) |
| `thu_nho` | thu nhỏ | | `nhan` | nhãn (Cực Hạn, Phù Hợp…) / hoặc "nhận" tuỳ chỗ |
| `sang`, `do_sang` | độ sáng | | `chu_ky` | chữ ký ảnh của tên người chơi |
| `xanh`, `do`, `cam`, `kem` | màu xanh, đỏ, cam, kem | | `tuong`, `the` | tướng, thẻ tướng |
| `chup` | chụp màn hình | | `khung` | khung thẻ = phẩm tướng (có / không) |
| `bam`, `cham`, `vuot` | bấm, chạm, vuốt | | `thieu_khung` | bản ghi có khung mà tướng bạn không khung |
| `cho` | chờ | | `che_do` | chế độ (`afk` / `huyen_linh`) |
| `xu_ly_*` | xử lý màn * | | `hien` | chế độ đang leo |
| `so_ai`, `ai` | số ải, ải | | `tien_trinh` | số ải đang phải đánh |
| `tran` | trận | | `chuoi` | chuỗi ải đánh liên tiếp (Tự Động Xử Lý) |
| `tk` | thống kê | | `khoa` | màn bị Game Booster khóa |
| `Dung` / `StopBot` | lỗi "dừng bot" | | `khong_ro` | không nhận ra màn hình |

Hỏi gì chưa rõ, xem trước trong [YEU_CAU.md](YEU_CAU.md) (nghiệp vụ game, bằng chứng) và `git log` (lịch sử từng thay đổi
và lý do).
