# AFK Auto: bot leo ải cho Hành Trình AFK

Kế hoạch, nghiệp vụ và bằng chứng nằm trong [YEU_CAU.md](YEU_CAU.md). Bản hiện tại là **bản máy tính** (Python + OpenCV, điều khiển máy qua ADB). Đã xong **bước 1: nhận diện màn hình** và **bước 2: leo ải** (`leo_ai.py`).

## Chạy bot

Cắm máy (hoặc kết nối Gỡ lỗi không dây), mở game ở bất kỳ màn nào trong số: Màn AFK, bản đồ thế giới, màn đội hình, màn kết quả. Sau đó chạy:

```bash
.venv/bin/python leo_ai.py                        # leo Màn AFK, kẹt thì sang Thách Đấu Huyền Linh
.venv/bin/python leo_ai.py --che-do huyen-linh --thu-lai 2 --gio-toi-da 3
.venv/bin/python leo_ai.py --xem-thanh-tich       # chỉ đọc 10 đội trong Thành Tích rồi dừng (không đánh)
.venv/bin/python leo_ai.py --thu-thap-tuong       # leo như thường, mỗi ải mới lưu tướng của cả 10 bản ghi (ô lọc tắt)
.venv/bin/python leo_ai.py --mot-tran             # đánh 1 trận rồi dừng
```

Bấm Ctrl+C để dừng. Nhật ký chi tiết ghi ở `leo_ai.log`, ảnh lúc có sự cố lưu ở `debug/`. Xem mọi tham số bằng `--help`.

Bot làm gì:
- Ở mỗi ải, bot đánh bằng đội đang có. Đội mang từ ải trước sang được đánh `--thu-lai-doi-cu` trận (mặc định 1), đội vừa chép được `--thu-lai` trận (mặc định 1: đo 13/10, đội chép thắng 42% ở trận đầu nhưng chỉ 6-7% ở trận 2-3). Thua đủ số trận thì bot mở Thành Tích, bật lọc "chỉ đội đã sở hữu" và chép đội dùng được đầu tiên theo thứ tự của game (bỏ đội Chiến Đấu Thủ Công; đội thiếu khung tướng để sau cùng, xem phần khung tướng). Đội đã thử được nhớ theo tên và lực chiến, vì thứ tự 10 đội đổi mỗi lần mở bảng.
- **Chép thử** (`--nguong-luc`, mặc định 0.95): sau khi chép, bot đọc lực chiến đội bạn ở màn đội hình. Thấp hơn 95% lực chiến bản ghi thì chưa đánh mà chép thử đội kế (dùng lại danh sách đã đọc, khoảng 15 giây mỗi đội); hết đội thì đánh các đội đã hoãn theo tỉ lệ giảm dần. Đo 13/10 (trận đầu): < 90% thắng 1/13, 90-100% thắng 4/10, >= 100% thắng 17/26. `--nguong-luc 0` tắt.
- Đánh hết mọi đội ở một ải mà chưa qua thì bot đánh thêm một vòng (`--so-vong`, mặc định 2), lần này ưu tiên đội có tỉ lệ lực chiến cao.
- Khi đã thử hết đội ở một chế độ, bot chuyển sang chế độ kia. Hết đội ở cả hai thì bot dừng và báo "kẹt ở ải X".
- Thắng thì bấm Chiến Đấu ở màn THẮNG để đánh ải kế, giữ nguyên đội vừa thắng.
- Bot tự gỡ lớp khóa Game Booster, màn nghỉ "Nhấn để tiếp tục", bảng phần thưởng AFK (bấm Nhận), và đi từ bản đồ thế giới về Màn AFK.
- Bot chỉ bấm vào những nút nhận ra được. Gặp màn lạ quá 60 giây thì lưu ảnh và báo.

## Cài đặt

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python tao_mau.py      # cắt mẫu từ samples/ vào templates/vi/ (chạy lại khi sửa toạ độ hoặc thêm ảnh mẫu)
```

## Thống kê tướng trong Thành Tích (thu một lần)

1. `leo_ai.py --thu-thap-tuong`: mỗi ải mới của mỗi chế độ, bot tắt ô lọc, lướt cả 10 bản ghi và lưu dải tướng
   (`thu_thap_tuong/<lượt>/NN.png`, kèm ảnh màn hình nhỏ) cùng một dòng trong `thu_thap_tuong/ban_ghi.csv`. Khi cần chép
   đội, bot bật lại ô lọc như thường.
2. `thong_ke_tuong.py gom`: tách 5 thẻ tướng mỗi bản ghi, gom thẻ cùng tướng thành nhóm (so ảnh mặt, ngưỡng chặt nên
   một tướng có thể ra 2-3 nhóm), xuất `thu_thap_tuong/nhom.html`.
3. Đặt tên nhóm trong `thu_thap_tuong/ten_tuong.json`; nhóm cùng tướng đặt trùng tên là gộp.
4. `thong_ke_tuong.py thong-ke`: ghi `thu_thap_tuong/tuong.csv` và `thu_thap_tuong/thong_ke.html` (số bản ghi có từng
   tướng theo chế độ, ở bản ghi đầu, đội hình hay gặp).

## Khung tướng (phẩm) của bạn

`doc_tuong_cua_toi.py --serial <máy>` mở màn đội hình (chưa đánh), lướt danh sách tướng (vuốt ở khe giữa 2 cột, nửa
hàng mỗi lần; lực chiến đội đổi là dừng), đọc khung từng thẻ và nhận tướng bằng ảnh mặt trong thư viện tướng
`templates/vi/tuong/` (tạo bằng `tao_thu_vien_tuong.py` từ dữ liệu Thành Tích đã thu; app Android dùng chung). Kết quả:
`thu_thap_tuong/tuong_cua_toi.json` và `tuong_cua_toi.html` (tướng nào của bạn không khung trong khi bản ghi có khung).
Thẻ khớp chưa chắc nằm ở mục "Cần xác nhận"; `--xac-nhan 29=Damian` lưu mặt thẻ đó vào thư viện và gán tên lại.

Khi đã có `tuong_cua_toi.json`, `leo_ai.py` so khung lúc chọn đội: bản ghi có tướng mà bản ghi có khung còn của bạn
không khung (chỉ xét tướng bản ghi dùng có khung >= 50% số lần) bị đánh dấu "thiếu khung" và để sau cùng
(`--thieu-khung cuoi`, mặc định), bỏ hẳn (`bo`) hoặc không so (`thu`). Đo 13/10: bản ghi thiếu khung Saida thắng 1/14
trận đầu, bản ghi không thiếu khung thắng 15/20. Đọc lại danh sách tướng mỗi khi nâng phẩm tướng.

## App Android (android/)

App AfkAuto (`./gradlew phatHanh` → `AfkAuto-<phiên bản>.apk`) có cùng các tính năng chọn đội với bản PC: đánh mỗi đội 1
trận, chép thử theo tỉ lệ lực chiến, vòng 2, so khung tướng, xử lý Thành Tích trống. Lần chạy đầu, app tự đọc danh sách
tướng ở màn đội hình (lưu trong thư mục riêng của app); đọc lại bằng ⋯ → Khung tướng trên bảng nổi. Module `:vision` là
bản Kotlin của phần nhận diện; `vision/tao_ket_qua_python.py` ghi kết quả của bản Python để `./gradlew :vision:test`
kiểm tra bản Kotlin cho kết quả giống hệt (cả thẻ tướng, khung, danh sách tướng).

## Các module

| File | Việc |
|---|---|
| `nhan_dien.py` | Ảnh màn hình → tên màn hình và vị trí các nút. Các màn hình: `khoa` (Samsung Game Booster), `nghi` (màn nghỉ "Nhấn để tiếp tục"), `phan_thuong_afk`, `thanh_tich`, `bai`, `thang`, `dang_danh` (kèm cờ `tu_dong`), `doi_hinh` (kèm `che_do` là `afk` hoặc `huyen_linh`), `man_afk`, `ban_do`, `khong_ro` (đang chuyển cảnh) |
| `thanh_tich.py` | Đọc đội đang chọn trong Thành Tích: chữ ký tên người chơi, lực chiến ("287M"), nhãn (`chua_xep_hang`, `cuc_han`, `phu_hop` hoặc không có), Lý Tưởng, Chiến Đấu Thủ Công, trạng thái ô lọc. `cung_doi(a, b)` cho biết 2 lần đọc có phải cùng một đội không (thứ tự đội trong Thành Tích thay đổi giữa các lần mở) |
| `so_ai.py` | Đọc số ải hiện tại ở Màn AFK (ô đỏ) và "Tiến Trình Màn Chơi Đỉnh Cao A → B" ở màn THẮNG |
| `tao_mau.py` | Tạo mẫu trong `templates/vi/`: mẫu màn hình, mẫu nút, mẫu chữ số |

Mọi toạ độ đo trên máy gốc 1600x2560 (Tab S7). Game co giãn theo chiều ngang. Theo chiều dọc, mỗi mẫu bám vào mép trên, mép dưới hoặc giữa màn hình. Phần đọc Thành Tích và số ải dời toạ độ theo vị trí tìm thấy của một mẫu mốc.

## Thử

```bash
.venv/bin/python nhan_dien.py samples/tab_s7_man_afk.png            # tên màn hình + nút
.venv/bin/python nhan_dien.py --diem anh.png                        # điểm khớp của mọi mẫu
.venv/bin/python nhan_dien.py --ve debug/ samples/*.png             # ảnh có đánh dấu nút
.venv/bin/python thanh_tich.py samples/thanh_tich/*.png
.venv/bin/python so_ai.py samples/tab_s7_man_afk.png samples/tab_s7_ket_qua_thang.png
```

Ảnh trực tiếp từ máy:

```bash
adb exec-out screencap -p > /tmp/anh.png && .venv/bin/python nhan_dien.py /tmp/anh.png
```

## Kiểm tra

```bash
.venv/bin/python test_nhan_dien.py        # 32 ảnh mẫu (thêm --bien để in biên an toàn của từng mẫu)
.venv/bin/python test_thanh_tich.py       # 20 đội Thành Tích (Màn AFK 751 và Huyền Linh 515), cả ở độ rộng 1080
.venv/bin/python test_so_ai.py
.venv/bin/python test_leo_ai.py           # logic chọn đội (không cần máy)
```

Nhãn đúng của ảnh mẫu nằm ở `samples/nhan.txt` và `samples/thanh_tich/nhan.txt`. Khi thêm ảnh mẫu mới, ghi nhãn vào các file đó.

## Giới hạn hiện tại

- Mới có ảnh mẫu của **Tab S7 (1600x2560)**. Bài kiểm tra có thu nhỏ ảnh về rộng 800 và 1080, nhưng vẫn **giữ nguyên tỉ lệ khung hình**. Máy A54 (1080x2340, dài hơn) cần ảnh thật để kiểm tra lại các mốc bám mép trên, mép dưới và giữa màn hình.
- Chưa có mẫu cho các hộp thoại (đội chưa đủ, lỗi mạng…), cho màn chuyển ải khi Chiến Đấu Tự Động thắng liên tiếp, và cho tình huống "Màn Chơi Đỉnh Cao đã đóng". Tùy chọn `--tu-dong` vì thế chưa được thử.
- Bot không nhớ các đội đã thử khi chạy lại chương trình.
- Đã chạy thật 1 giờ 10 phút trên Tab S7 (12/10): thắng 754 → 762 ở Màn AFK. Chưa gặp tình huống kẹt hẳn ở cả hai chế độ.
- Băng chữ "Trận Chiến Bắt Đầu" và màn trắng chuyển cảnh sau khi thắng đều trả về `khong_ro`. Bot chỉ cần chờ thêm vài giây.
