# AFK Auto: bot leo ải cho Hành Trình AFK

Kế hoạch, nghiệp vụ và bằng chứng nằm trong [YEU_CAU.md](YEU_CAU.md). Người mới vào dự án (sửa code, bảo trì) đọc
[HUONG_DAN_DEV.md](HUONG_DAN_DEV.md). Bản hiện tại là **bản máy tính** (Python + OpenCV, điều khiển máy qua ADB). Đã xong **bước 1: nhận diện màn hình** và **bước 2: leo ải** (`leo_ai.py`).

## Chạy bot

Cắm máy (hoặc kết nối Gỡ lỗi không dây), mở game ở bất kỳ màn nào trong số: Màn AFK, bản đồ thế giới, màn đội hình, màn kết quả. Sau đó chạy:

```bash
.venv/bin/python leo_ai.py                        # leo Thách Đấu Huyền Linh, kẹt thì sang Màn AFK
.venv/bin/python leo_ai.py --che-do huyen-linh --thu-lai 2 --gio-toi-da 3
.venv/bin/python leo_ai.py --xem-thanh-tich       # chỉ đọc 10 đội trong Thành Tích rồi dừng (không đánh)
.venv/bin/python leo_ai.py --thu-thap-tuong       # leo như thường, mỗi ải mới lưu tướng của cả 10 bản ghi (ô lọc tắt)
.venv/bin/python leo_ai.py --mot-tran             # đánh 1 trận rồi dừng
.venv/bin/python leo_ai.py --leo-ho               # leo hộ người khác (Đại Diện Tác Chiến), xem mục dưới
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

## Leo hộ người khác (Đại Diện Tác Chiến)

Khi tài khoản đã qua hết ải ("Đã Vượt Qua Tất Cả Màn Chơi"), bạn có thể leo hộ thành viên bang: họ đăng "Yêu Cầu Đại
Diện AFK Liên Hoàn" trong Trò chuyện Bang Hội, bạn bấm **Đi** ở tin đó. Game mở bảng chọn ải của người nhờ (thẻ Thách
Đấu Huyền Linh và thẻ Màn AFK, mỗi thẻ ghi ải của họ). Lúc đó chạy:

```bash
.venv/bin/python leo_ai.py --leo-ho
```

- Bot đánh bằng **tướng của người nhờ** (màn đội hình ghi "Đội của <tên>", chỉ có 1 nút Chiến Đấu, không có Chiến Đấu
  Tự Động). Chọn đội y như leo của bạn: đội trống hoặc thua thì mở Thành Tích, bật lọc (lọc theo tướng của người nhờ),
  chép thử theo tỉ lệ lực chiến. Không so khung tướng (dữ liệu khung là của bạn).
- Thắng: màn THẮNG có dải "Đại Diện Tác Chiến" và nút **Tiếp Theo**; bot bấm Tiếp Theo, về bảng chọn ải và đánh ải kế.
  Thua: bấm Thử Lại (về màn đội hình), không bao giờ bấm ← vì có thể ra khỏi phiên.
- `--che-do` vẫn dùng được (mặc định Huyền Linh trước, kẹt thì sang Màn AFK). Số ải của người nhờ đọc ở tiêu đề màn
  đội hình.
- Bot dừng khi đã thử hết đội ở mọi chế độ, hoặc khi thấy màn của riêng bạn (bản đồ, Màn AFK): phiên đã kết thúc.
  Đo 17/10: để màn THẮNG leo hộ đứng yên vài phút thì game tự về bản đồ.
- Chưa có ảnh mẫu màn BẠI của leo hộ (6 trận đầu đều thắng); nếu màn BẠI khác màn thường, bot sẽ lưu ảnh "khong-ro".

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

`doc_tuong_cua_toi.py --serial <máy>` mở Hội Trường Cộng Hưởng từ nút trên bản đồ/Màn AFK và cuộn danh sách lớn để đọc khung. Dùng `--doi-hinh` khi cần bộ đọc cũ. Tướng được nhận bằng ảnh mặt trong thư viện tướng
`templates/vi/tuong/` (tạo bằng `tao_thu_vien_tuong.py` từ dữ liệu Thành Tích đã thu; app Android dùng chung). Kết quả:
`thu_thap_tuong/tuong_cua_toi.json` và `tuong_cua_toi.html` (tướng nào của bạn không khung trong khi bản ghi có khung).
Thẻ khớp chưa chắc nằm ở mục "Cần xác nhận"; `--xac-nhan 29=Damian` lưu mặt thẻ đó vào thư viện và gán tên lại. Xác nhận tên chỉ thêm mẫu viền khi đã đánh dấu khung bằng `--khung TEN=0|1`. Kết quả rỗng hoặc lỗi ghi ảnh/JSON giữ nguyên phiên cũ; ảnh mỗi phiên có đường dẫn riêng và được giữ lại để khôi phục.

Bản Python đang thử nghiệm bộ cắt Hội Trường cải tiến: đọc cả 5 thẻ ở màn đầu, giữ thẻ tóc trắng, chọn ảnh mặt nét hơn qua nhiều lần thấy và chỉ gợi ý nếu hai tên khớp gần nhau. Python có thêm trạng thái **chưa xác định khung** (`khung: null` trong JSON): ảnh ít chi tiết, mẫu viền chưa đồng thuận hoặc các lần đọc mâu thuẫn không bị ép thành không khung. Bộ so đội bỏ qua khung chưa rõ; lựa chọn thủ công vẫn ưu tiên. Báo cáo HTML/JSON lưu bằng chứng điểm sao và phiếu mẫu viền. Các thay đổi này chưa chuyển sang Android.

Nhập hàng loạt tên người dùng đã xác nhận theo snapshot ảnh cố định:

```bash
.venv/bin/python nhap_ten_tuong.py --danh-sach debug/can-bo-sung-ten-20261030 --ten debug/can-bo-sung-ten-20261030/ten_nguoi_dung.txt
```

Tệp tên có dạng `SO=TEN`, hỗ trợ tên nhiều từ; bỏ trống hoặc `?` để chưa xác nhận. Công cụ kiểm tra mã phiên, số thẻ trùng/ngoài danh sách và ảnh trước khi bổ sung mẫu mặt. Không học khung từ xác nhận tên. Khi sửa tên cùng số thẻ/cùng phiên, mẫu mang nhãn cũ được thay thế.

Để tạo thư viện mặt bổ sung từ các nhóm đã đặt tên và các ảnh đã xác nhận:

```bash
.venv/bin/python bo_sung_mau_tuong.py --ra debug/mau-bo-sung-python.npz
```

Bộ chọn giữ tối đa 6 mẫu đa dạng mỗi nhóm, lưu khóa nguồn để đối chiếu. Nhãn nhóm kế thừa dữ liệu đã đặt tên; không lấy tên tự đoán từ danh sách tướng làm nhãn học. Nạp bằng `--thu-vien-mat debug/mau-bo-sung-python.npz`. Nếu cần tái tạo bốn mẫu tên đọc trực tiếp trong game, dùng thêm `--mat-da-xac-nhan tests/fixtures/tuong_da_xac_nhan` khi tạo thư viện.

Đọc lại khung trên ảnh gốc và giữ số thẻ/tên từ báo cáo đã xác nhận:

```bash
.venv/bin/python doc_lai_khung_tuong.py --anh-goc debug/hoi-truong-buoc-nho-20261030 --tham-chieu debug/da-bo-sung-ten-20261030 --ra debug/can-lai-khung-20261030 --thu-vien-mat debug/mau-bo-sung-python.npz
```

Bộ căn tìm biên từng thẻ trong vùng ứng viên, tách tại khe cột/hàng khi chóp vàng chạm nhau, giữ tỷ lệ và đặt giữa ảnh chuẩn. Vùng mặt tham chiếu được lưu riêng để không đổi tên đã xác nhận. Mỗi lượt đọc ghi chất lượng biên, vùng sao và hai cạnh; trường hợp thiếu bằng chứng không dùng để kết luận khung. Báo cáo `so_sanh.html` giữ mã thẻ, ảnh trước/sau và số lượt đủ biên; `nguon/` chứa 15 ảnh gốc có đánh dấu biên; `truoc_sau.json` chứa số liệu thay đổi.

Tạo lại bảng xác nhận từ biên bản kiểm tra bằng mắt ngày 07/11/2026:

```bash
.venv/bin/python tao_bang_xac_nhan_khung.py --bao-cao debug/can-lai-khung-20261030 --anh-goc debug/hoi-truong-buoc-nho-20261030 --danh-gia docs/kiem-tra-bang-mat-khung-20261107.json --ra debug/kiem-tra-khung-20261107
```

Mở `xac_nhan_khung.html` trong thư mục kết quả để xem 42 thẻ chưa rõ và #95 Indris nghi nhận nhầm tóc thành sao. Chọn `1` (có khung), `0` (không khung) hoặc `?` (chưa rõ), rồi lấy văn bản gửi vào chat hoặc tải TXT/JSON. Số thẻ/tên giữ nguyên; nhận xét của trợ lý không được tự đưa thành xác nhận người dùng. Nếu báo cáo nguồn đã đổi SHA-256, công cụ dừng để tránh dùng nhận xét của phiên cũ.

Nhập câu trả lời khung vào báo cáo mới và lựa chọn tay của Python:

```bash
.venv/bin/python nhap_khung_tuong.py --bao-cao debug/can-lai-khung-20261030 --danh-gia docs/kiem-tra-bang-mat-khung-20261107.json --nhan debug/kiem-tra-khung-20261107/tra_loi_da_dinh_chinh.txt --ra debug/da-xac-nhan-khung-20261107 --khung-tay thu_thap_tuong/khung_tay.json
```

Câu trả lời dùng `SO=1|0|? # Tên`; tên sau `#` được đối chiếu nếu có. Báo cáo lưu riêng nguồn nhãn người dùng và kết luận máy trước xác nhận; `?` tiếp tục là chưa rõ. Đợt 07/11 có 43 nhãn đã xác nhận, gồm Lumont #89 và Indris #95 không khung. Báo cáo 117 thẻ sau nhập là 84 có/33 không; 74 thẻ còn lại vẫn mang nhãn tự đọc. Bộ nhập không tự học mẫu sao/viền.

Học bộ so viền dành riêng cho ảnh đã căn (tập tướng kiểm tra giữ riêng):

```bash
.venv/bin/python huan_luyen_khung_can.py --bao-cao debug/can-lai-khung-20261030 --nhan debug/da-xac-nhan-khung-20261107/khung_da_xac_nhan.json --anh-goc debug/hoi-truong-buoc-nho-20261030 --chia-tap debug/cai-thien-khung-20261107/chia_tap.json --ra thu_thap_tuong/khung_can_python.npz
```

Python tự nạp mẫu này khi có; `ThuVien(mau_khung_can=PATH)` chọn tệp khác. Bộ so chỉ dùng màu/cấu trúc viền và dải sao, không tra tên hoặc lựa chọn tay. Trường hợp xa mẫu/không tách biệt vẫn giữ chưa rõ. Bộ căn đã bổ sung viền tím nhạt, bộ tìm hàng có dự phòng khi chữ Cấp không khớp. Phiên 16 ảnh mới đọc được đủ 43 tướng có nhãn: tự động đúng 36, sai 0, còn 7 chưa rõ; 14 tướng giữ lại đạt 9 đúng/0 sai/5 chưa rõ. Đây là tập khó cùng máy, chưa đại diện mọi thiết bị. Báo cáo ảnh và bằng chứng nằm ở `debug/cai-thien-khung-20261107/bao_cao.html`; các script lặp lại phép đo cũng lưu cùng thư mục. 43 lựa chọn tay vẫn ưu tiên khi Python so khung.

Quản lý mẫu theo phiên bản và kiểm chứng độc lập:

```bash
.venv/bin/python quan_ly_mau.py current
.venv/bin/python xuat_kho_mau.py --ra debug/quan-ly-mau-20261108/kho_mau.html
.venv/bin/python quan_ly_mau.py rollback
```

Kho `thu_thap_tuong/kho_mau/` đã có 102 mẫu tên và 43 mẫu khung được duyệt; bản đang chạy chỉ học 29 mẫu khung, giữ riêng 14 mẫu đánh giá. Mẫu chờ/bị loại không tự vào bản phát hành, kích hoạt và khôi phục kiểm tra đủ mã nội dung rồi mới thay con trỏ. `ThuVien()` ưu tiên kho đã kích hoạt; tệp mô hình rời không tự thay bản đang chạy. Xác nhận tên mới được đưa vào hàng chờ; chỉ mẫu đã duyệt mới được bổ sung vào bộ cá nhân.

Vòng v1 đã kiểm chứng trên tài khoản khác: 16 ảnh mới, 50 nhóm thẻ được người dùng gán nhãn sau khi dự đoán được niêm phong. Kết quả **45 đúng / 1 sai / 4 chưa rõ**; lỗi #38 được ghi rõ. Tập kiểm tra được chặn khỏi học bằng mã ảnh và ảnh nguồn/dẫn xuất. Cùng Tab S7, chưa đánh giá thiết bị khác hoặc độ phủ danh sách đầy đủ. [Hướng dẫn quản lý và kiểm chứng](docs/quan-ly-mau-va-kiem-chung.md) có quy trình duyệt, học ứng viên, phát hành, kích hoạt, khôi phục và chấm lại.

Để kiểm tra đầy đủ một phiên trên máy thật:

```bash
.venv/bin/python kiem_tra_hoi_truong.py --serial SERIAL --ra debug/phien-hoi-truong-moi --thu-vien-mat debug/mau-bo-sung-python.npz
```

Chương trình dùng bước vuốt ngắn, kiểm tra cuộn ngược/quay lại ảnh cuối và chồng lấp của lưới giữa các trang. Nhóm 5 thẻ cố định không được tính là bằng chứng chồng lấp. Phiên thiếu chồng lấp báo lỗi và giữ ảnh để kiểm tra; ảnh, `phien.json`, `do_phu.json` và kết quả đọc được xuất riêng. Kiểm tra nối trang chưa thay thế việc gán nhãn đầy đủ từng ô để đo tỷ lệ bỏ sót.

Để thử gợi ý tên nhiều tỷ lệ và xuất báo cáo riêng:

```bash
.venv/bin/python doc_tuong_cua_toi.py --anh samples/tab_s7_hoi_truong_tren_cung.png samples/tab_s7_hoi_truong_dau.png samples/tab_s7_hoi_truong_cuon.png --goi-y-da-ty-le --thu-muc-ra debug/kiem-tra-ten-python
```

Báo cáo hiện tối đa 3 ứng viên cùng ảnh mẫu cho mọi thẻ chưa nhận tên, kể cả điểm thấp. Điểm thử nhiều tỷ lệ chỉ dùng để tham khảo; ngưỡng tự nhận tên vẫn dùng điểm gốc. Nếu đã kiểm tra đúng tên, dùng `--thu-muc-ra debug/kiem-tra-ten-python --xac-nhan SO=TEN` để xác nhận thẻ trong báo cáo riêng. Ảnh xác nhận bổ sung vào thư viện mặt dùng chung; viền chỉ được học khi đã chọn khung thủ công.

Khi đã có `tuong_cua_toi.json`, `leo_ai.py` so khung lúc chọn đội: bản ghi có tướng mà bản ghi có khung còn của bạn
không khung (chỉ xét tướng bản ghi dùng có khung >= 50% số lần) bị đánh dấu "thiếu khung" và để sau cùng
(`--thieu-khung cuoi`, mặc định), bỏ hẳn (`bo`) hoặc không so (`thu`). Đo 13/10: bản ghi thiếu khung Saida thắng 1/14
trận đầu, bản ghi không thiếu khung thắng 15/20. Đọc lại danh sách tướng mỗi khi nâng phẩm tướng.

## App Android (android/)

Từ bản 1.13, **Đọc lại khung tướng** dùng danh sách lớn trong **Hội Trường Cộng Hưởng**. Mở game ở bản đồ/Màn AFK có nút Hội Trường hoặc mở sẵn Hội Trường, rồi bấm Khung tướng trên bảng nổi (hay Đọc lại khung tướng trong app). Bot nhận phần mũ của cả hai kiểu biểu tượng, cuộn từ đầu tới cuối, đọc nhóm 5 thẻ lớn và lưới 6 cột. Không tự đọc danh sách nhỏ ở đội hình khi bắt đầu leo nữa. Nếu chưa có dữ liệu, bot dùng lựa chọn tay và nhắc đọc Hội Trường. Mất màn, không cuộn được, danh sách rỗng hoặc vượt giới hạn cuộn đều giữ dữ liệu cũ. Thư viện tên còn giới hạn: thẻ chưa chắc chỉ hiện gợi ý, cần xác nhận trong app.

Từ bản 1.12, nút Đóng nằm cạnh nút mở rộng trên hàng đầu của bảng nổi, cách nhau 8dp và có viền riêng. Nền xám của app và bảng nổi sáng thêm một mức; giữ chiều cao nút 24dp.

Từ bản 1.11, nền tối sáng hơn và chữ phụ rõ hơn. Nút mở rộng bảng nổi rộng riêng 40dp, nút Đóng bảng chuyển xuống hàng riêng trong phần mở rộng. Các nút thao tác cao 24dp (trước 32dp), hàng lựa chọn cao 26dp với biểu tượng nhỏ hơn.

Từ bản 1.10, toàn bộ app và bảng nổi dùng giao diện tối. Thiết lập ban đầu và Giới hạn chạy mặc định mở. Bảng nổi nhỏ hơn, Leo hộ / Tự động cùng hàng, Nâng cao có nút viền rõ và chỉ giữ ô nhật ký. Khi chạy bảng tự thu gọn; khi chụp hoặc chạm/vuốt luôn ẩn tạm để tránh che game. Đọc lại khung tướng trong app đưa app xuống nền, chờ tối đa 45 giây để bạn mở Màn AFK hoặc đội hình rồi dùng luồng đọc cũ; báo rõ kết quả hoặc màn cần mở.

Từ bản 1.9, bảng nổi mặc định thu gọn: mở ⌄ để chọn Cả hai / Ải AFK, Leo hộ và Tự động chiến đấu. Mở tiếp Nâng cao để dùng Leo 1 trận, Nhận diện, Thành Tích, Khung tướng và xem nhật ký. App tách bốn mục Điều khiển, Khung tướng, Nhật ký và Cài đặt. Chỉ giữ màn hình sáng khi có tác vụ đang chạy; dừng, kết thúc, lỗi hoặc đóng bảng nổi đều bỏ giữ sáng (không tự tắt màn hình ngay).

Từ bản 1.8, bảng nổi có hàng chọn **Cả hai / Ải AFK / Huyền Linh** và ô **Tự động chiến đấu**, dùng chung cài đặt
với màn hình app. Chọn chế độ khi bot đang dừng rồi bấm ▶; ô tự động có thể bật/tắt khi bot đang chạy và được áp dụng
ở quyết định tiếp theo (không hủy chuỗi tự động game đã bắt đầu). Màn hình hẹp có thể vuốt ngang hàng lựa chọn.

Từ bản 1.7, màn THẮNG nhận cả nút "Chiến Đấu" cũ và nút "Thách Đấu Huyền Linh Sinh Vật" mới (25/10), đọc đủ tiến
trình 4 chữ số, bấm lại nút đi tiếp nếu màn thắng chưa chuyển sau lần bấm đầu, và xử lý bảng thông tin ải Huyền Linh
khi bảng này đang mở.

App AfkAuto (`./gradlew phatHanh` → `AfkAuto-<phiên bản>.apk`) có cùng các tính năng chọn đội với bản PC: đánh mỗi đội 1
trận, chép thử theo tỉ lệ lực chiến, vòng 2, so khung tướng, xử lý Thành Tích trống. Đọc danh sách tướng riêng từ Hội Trường (lưu trong thư mục riêng của app) bằng Nâng cao → Khung tướng trên bảng nổi. Từ bản 1.6 có ô
"Leo hộ người khác" (giống `--leo-ho`): bật ô này **trước**, rồi vào game bấm Đi ở yêu cầu trong Trò chuyện Bang Hội và
bấm ▶ trên bảng nổi. Đo 17/10: mở game bằng nút "Mở game" của app (hoặc biểu tượng game) khi game đang chạy làm game tải
lại từ đầu, mất phiên leo hộ đang mở. Module `:vision` là
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

Lượt Python v2 ngày 08/11: quy tắc mới đạt 43/43 trên bộ phát triển và 50/50 khi đọc lại bộ đã biết nhãn; không coi hai số này là kiểm chứng độc lập mới. Đã đối chiếu đủ 121/121 tướng trên tài khoản kiểm tra qua nguồn Bộ Sưu Tập. Vòng mới `test-2d9de2fc4f0046c5` gồm 40 thẻ chọn từ 71 nhóm chưa thuộc bộ cũ, đã được người dùng gán nhãn và đạt 40/40 đúng. Bản v2 đã được kích hoạt trên Python, có thể khôi phục bản trước. Chi tiết trong [hướng dẫn](docs/quan-ly-mau-va-kiem-chung.md).

09/11 — Python đã bổ sung xác minh danh sách ngắn theo số tham chiếu, sửa hàng lưới chỉ có một thẻ tóc trắng và giữ nhiều diện mạo cho một tên. Đã thử máy thật với 48 tướng và danh sách lọc 6 thẻ. Thêm 22 mẫu đọc tên trực tiếp, gồm hai chân dung Isabella/Silvina từng dễ nhầm; bản mới đã kích hoạt. Xem [hướng dẫn danh sách ngắn và diện mạo](docs/danh-sach-ngan-va-dien-mao.md).

09/11 — Android 1.14 chuyển bộ nhận diện v2 và 124 mẫu mặt đã duyệt, kiểm tra biên/sao, giữ khung chưa rõ, xác minh cuộn và quản lý mẫu tên theo phiên bản. Bộ đối chiếu Python–Kotlin: 90 thẻ, 42 ảnh gốc, 296 kết quả danh sách khớp. Xem [báo cáo Android](docs/android-khung-v2.md) cho kết quả thiết bị và giới hạn.

Kiểm tra trực tiếp Android 1.14: tài khoản đang mở có 120 tướng theo Bộ Sưu Tập (131 ô, 11 chưa sở hữu). Phiên 16 ảnh cho 120 nhóm, 111 tên tự nhận/9 chưa rõ, toàn bộ kết quả và biên khớp Python khi đọc lại cùng ảnh. Thử mốc 121 đã giữ nguyên dữ liệu cũ và lựa chọn tay.

09/11 — Android 1.17 đã bổ sung 22 mẫu mặt có bằng chứng đọc tên trực tiếp, gồm 9 thẻ chưa rõ ban đầu, SS/Gunnar và 11 thẻ sát ngưỡng (có Gwyneth). Bộ mẫu có 146 ảnh mặt/125 tên, giữ ngưỡng và mô hình khung. Đối chiếu 48 ảnh, 360 kết quả danh sách và 90 thẻ khung đều qua trên JVM/Tab S7. Lượt đọc thật cuối nhận đủ 120/120 tên, giữ nguyên 10 lựa chọn tay. Xem [bảng tên và kiểm tra hồi quy](docs/chin-the-chua-ro.md).

10/11 — Android 1.18 tách kết quả/khung tay/ảnh xác nhận theo hồ sơ tài khoản, giữ bộ mẫu tên dùng chung; bổ sung thu hồi mẫu đã duyệt, chuyển mẫu hợp lệ qua cập nhật và lịch sử khôi phục. Đã thử máy thật 120/48 tướng, danh sách lọc 6 và các ca từ chối lưu khi tham chiếu sai/cuộn ngược không xác minh. Xem [hồ sơ và quản lý mẫu](docs/ho-so-va-mau-android.md); kiểm chứng trên tài khoản mới/thiết bị khác còn thiếu nguồn.
