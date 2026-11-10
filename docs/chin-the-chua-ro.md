# Hoàn thiện tên tướng — 09/11/2026

Bản đang dùng là **Android 1.17 / Python `v-647cbc8e579f3e3d`**, 146 mẫu mặt cho 125 tên. Lượt đọc thật cuối trên Tab S7 đã xác minh đủ **120 thẻ / 120 tên duy nhất / 0 tên chưa rõ**, giữ nguyên 10 lựa chọn khung tay. Đối chiếu ba lượt cũ gồm 48 ảnh, 360 kết quả danh sách và 90 thẻ khung đều khớp Python trên JVM và Tab S7. Đây là hồi quy trên cùng tài khoản, chưa phải kiểm chứng tên độc lập trên tài khoản mới.

Đã xuất bảng từ đúng phiên Android 120 thẻ trước đó, đọc tên trực tiếp trong game trên tài khoản đã xác nhận có 120 tướng, rồi bổ sung mẫu mặt từ ảnh chụp mới. Giữ ngưỡng 0,85 và khoảng hơn tên thứ hai 0,04.

| Nhóm trong phiên cũ | Tên đọc trực tiếp | Cách xử lý |
|---|---|---|
| 5 | Silven | Bổ sung diện mạo |
| 17 | Satrana | Bổ sung diện mạo |
| 21 | Ludovic | Bổ sung diện mạo |
| 27 | Shakir | Bổ sung diện mạo |
| 55 | Antandra | Bổ sung diện mạo |
| 103 | Talene | Bổ sung diện mạo |
| 106 | Saida | Bổ sung diện mạo |
| 107 | Voracia | Bổ sung tên còn thiếu |
| 116 | Baden | Bổ sung tên còn thiếu |

Bảng ban đầu: `debug/9-the-chua-ro-20261109/9_the_chua_ro.html`. Bảng kèm ảnh đọc tên: `ket_qua_9_the.html` trong cùng thư mục. Các số nhóm ở đây thuộc phiên 120 thẻ, không phải số thứ tự của những bảng xác nhận trước đó.

## Mẫu và kết quả Python

Ứng viên `v-e0cb4d62c79a0015` có 133 mẫu mặt đã duyệt cho 125 tên; thêm 9 mẫu vào bộ 124 mẫu trước. Kho có 176 bản ghi gồm 133 mẫu mặt và 43 mẫu khung. Mô hình khung giữ nguyên 29 mẫu học/14 validation và nguyên mã nội dung. 43 lựa chọn khung tay của Python không thay đổi.

Từng mẫu mới có ảnh nguồn, vị trí thẻ, ảnh hiện tên, mã nội dung và nguồn nhãn `on_screen_name`. Chỉ chuyển sang đã duyệt sau khi xem tên. Không dùng các ứng viên yếu làm nhãn, không sửa hoặc thêm mẫu vào hai bộ kiểm tra khung đã niêm phong.

Đọc lại đúng 16 ảnh cũ: vẫn 120 nhóm, nhận đủ 120 tên duy nhất; 111 tên đã nhận giữ nguyên. Cả 120 kết quả khung và biên ảnh được chọn giữ nguyên (85 có khung, 35 không khung). Các mẫu học mới có pixel khác ảnh đại diện của 9 thẻ cũ, nhưng đây vẫn là hồi quy những trường hợp đã biết cùng tài khoản, không phải phép đo độc lập mới.

## Kiểm tra Android

Bộ đối chiếu mới nằm tại `debug/vision-fixtures/v-e0cb4d62c79a0015/expected.json`, ghim phiên bản và mã bộ mẫu Android. Kiểm tra 90 thẻ khung lấy nguyên đáp án/đặc trưng đã cố định trước đó; phần danh sách dùng đúng 16 ảnh cũ và 120 tên đã đối chiếu.

Bộ chạy JVM/thiết bị tìm bảng đối chiếu theo phiên bản mẫu, giữ nguyên bảng phiên bản trước. Kiểm tra cả tên, lý do tên, khung, biên cắt và ảnh đại diện được chọn. Bản Android 1.15 dùng cùng bộ mẫu với Python, tiếp tục giữ riêng lựa chọn tay và hàng chờ mẫu trên điện thoại.

```bash
.venv/bin/python xuat_the_chua_ro.py --phien debug/android-v2-20261109/live-120 --ra debug/9-the-chua-ro-20261109
.venv/bin/python android/vision/xuat_mau_v2.py --version v-e0cb4d62c79a0015
cd android
JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 ./gradlew :vision:test --offline
```

Lệnh xuất bảng đầu tiên cần đúng bản mẫu cũ của phiên, trước khi kích hoạt bản mới. Không chạy lại để ghi đè bảng ban đầu sau khi cập nhật mẫu.

## Kết quả cuối

Đã kích hoạt `v-e0cb4d62c79a0015`. 30 kiểm thử Python và 13 kiểm thử JVM đều qua. Trên Tab S7, bộ đối chiếu gồm 90 thẻ khung cố định, 16 ảnh gốc và 120 nhóm tướng đều qua: 120 tên khớp Python, 111 tên cũ giữ nguyên, biên cắt/canvas và khung của 120 nhóm giữ nguyên. Thời gian chạy bộ đối chiếu trên thiết bị là 95,4 giây; đây không phải thời gian cuộn và chụp một phiên mới.

Các tệp gốc/dự đoán niêm phong của bộ 50/40 giữ nguyên. Bộ 50 thuộc quy tắc v1 lịch sử, nên không diễn giải kiểm tra mã v1 thành v2; bộ 40 và bản phát hành trước xác nhận mã quy tắc v2 không đổi. Mã mô hình khung cũng giữ nguyên. Bằng chứng gồm `activated.json`, `android.json`, `python_after.json`, `summary.json` và các nhật ký kiểm thử trong `debug/9-the-chua-ro-20261109/`.

APK ký cùng khóa với bản cũ: `AfkAuto-1.15.apk`. Bảng bằng chứng tên: `debug/9-the-chua-ro-20261109/ket_qua_9_the.html`.

## Bổ sung sau lượt chụp mới trên 1.15

Lượt chụp thật tiếp theo xác minh đủ 120 thẻ và nhận đúng cả 9 tên trên, nhưng hai thẻ khác còn dưới ngưỡng tên: nhóm 36 (SS, 0,844668) và nhóm 75 (Gunnar, 0,842366). Đây là số nhóm trong phiên mới `phien-1794238879527`, khác phiên ở bảng trên. Đã mở trực tiếp từng thẻ: tên hiển thị là **Elijah & Lailah** và **Gunnar**. Giữ tên rút gọn SS của thư viện cũ, đồng thời lưu tên đầy đủ trong nguồn bằng chứng. Không hạ ngưỡng 0,85.

Hai mẫu diện mạo mới đưa ứng viên lên `v-a8a60dd04b23ad31`, 135 mẫu mặt cho 125 tên. Kiểm tra tên trên cả hai lượt ảnh cho 120/120 tên mỗi lượt, giữ nguyên 111 tên cũ ở lượt đầu và 118 tên chắc ở lượt sau. Bằng chứng tên, ảnh nguồn và đánh giá riêng nằm trong `debug/9-the-chua-ro-20261109/hai-the-tiep/`; bảng ảnh là `ket_qua_2_the.html`.

Bộ đối chiếu mới ghim 32 ảnh, 240 kết quả danh sách của cùng tài khoản và giữ nguyên 90 thẻ khung cố định. Đây là kiểm tra hồi quy hai lượt chụp của cùng tài khoản; không tính thành hai tài khoản độc lập hay 240 tướng khác nhau. Bản đóng gói tương ứng là Android 1.16.

Kiểm tra tên hai thẻ trên ảnh đại diện của lượt 1.15 đạt điểm SS 0,965104 và Gunnar 0,963629, cách tên đứng thứ hai lần lượt 0,445037 và 0,497814. Hai mẫu học mới có pixel khác ảnh đại diện này. Kiểm thử JVM được cấu hình luôn chạy và không lấy kết quả từ bộ nhớ kiểm thử, vì đọc bộ mẫu và ảnh ngoài module; không dùng trạng thái `UP-TO-DATE` làm bằng chứng cho một phiên bản mẫu mới.

Ứng viên hai mẫu đã qua 30 kiểm thử Python và 13 kiểm thử JVM chạy thực sự. Trên Tab S7, đối chiếu 90 thẻ khung, 32 ảnh và 240 kết quả danh sách đều thành công (190,7 giây); trên JVM phần đối chiếu v2 mất 124,1 giây. Bộ mẫu `v-a8a60dd04b23ad31` đã kích hoạt trên Python và cài vào ứng dụng 1.16 bằng cập nhật giữ dữ liệu. Hai bộ kiểm tra niêm phong giữ nguyên; mô hình khung, ngưỡng tên và lựa chọn khung tay của Python giữ nguyên. APK 1.16 ký cùng khóa với 1.15.

## Rà nhóm sát ngưỡng sau lượt đọc thật 1.16

Lượt đọc thật 1.16 xác minh đủ 120 thẻ, nhận đúng SS và Gunnar, nhưng chỉ nhận 119 tên: Gwyneth còn 0,847808. 10 lựa chọn khung tay trên Android giữ nguyên trước/sau phiên. Không lấy kết quả hồi quy 120/120 của hai lượt cũ để thay cho kết quả 119/120 của lượt thật này.

Đã mở trực tiếp và đọc được tên Gwyneth. Rà thêm các tên đã nhận nhưng còn dưới 0,88 để bổ sung mẫu cùng một đợt: Frieren, Koko, Eironn, Baelran, Mikola, Kordan, Florabelle, Callan, Peggy và Orion. Mốc 0,88 chỉ dùng chọn mẫu cần kiểm tra; ngưỡng gán tên vẫn là 0,85 và khoảng cách tên thứ hai 0,04. Ảnh nguồn/bằng chứng nằm trong `debug/9-the-chua-ro-20261109/sat-nguong/`.

Đã đọc đủ tên trực tiếp của 11 thẻ và thêm 11 mẫu mặt đã duyệt, đưa ứng viên lên `v-647cbc8e579f3e3d`: 146 mẫu mặt/125 tên, tổng 189 bản ghi cùng 43 mẫu khung giữ nguyên. Đánh giá tên trên cả ba lượt ảnh đều đạt 120/120 tên duy nhất; 111, 118 và 119 tên đã chắc của từng lượt giữ nguyên. Mẫu mới được phát hành riêng sau khi kiểm tra, không ghi đè các phiên bản trước. Bảng bằng chứng là `sat-nguong/ket_qua_11_the.html` trong thư mục gốc bằng chứng nêu trên.

Đối chiếu nguồn mẫu xác nhận giữ đủ 124 mẫu mặt ban đầu và thêm đúng 22 mẫu trong ba đợt (9 + 2 + 11). Tất cả mẫu mới đều có nguồn tên đọc trên màn hình và đã duyệt; không thay mẫu khung. Cả 11 mẫu cuối có pixel khác ảnh đại diện của lượt 1.16, nhưng vẫn thuộc cùng tài khoản/phát triển nên không gọi đây là kiểm chứng độc lập.

Bộ mẫu 146 ảnh đã qua đối chiếu trên JVM và Tab S7: 90 thẻ khung cố định, 48 ảnh gốc và 360 kết quả danh sách của ba lượt. Mỗi lượt giữ đủ 120 tên duy nhất, khung và biên chọn ảnh đúng Python. Phần v2 trên JVM mất 257,9 giây, trên Tab S7 303,8 giây. Đây là thời gian chạy đối chiếu dữ liệu, không phải thời gian cuộn/chụp thật. Mã thuật toán không đổi từ bản đã qua 30 kiểm thử Python và 13 kiểm thử JVM trước đó; lần này chạy lại kiểm tra v2 theo bộ mẫu mới. Bản `v-647cbc8e579f3e3d` đã kích hoạt trên Python sau khi cả hai nền tảng đều qua.

## Lượt đọc thật cuối trên 1.17

Phiên `phien-1794242486536` thu 16 ảnh, xác minh đầu/cuối và số tham chiếu 120, nhận đủ 120 tên duy nhất, không còn tên chưa rõ. Tập tên khớp cả ba lượt hồi quy. 120 ảnh đại diện đều đủ biên, vùng sao và viền; kết quả khung tự đọc gồm 85 có/35 không. Thời gian đến lưu kết quả là 158,3 giây. Mã nội dung lựa chọn tay trước/sau và với phiên 1.16 giống nhau, giữ 10 lựa chọn. Dữ liệu chính đã cập nhật thành phiên mới.

Bằng chứng cuối: `sat-nguong/live-117/`, `sat-nguong/live_check.json`, `sat-nguong/summary.json`, `sat-nguong/activated.json`. APK `AfkAuto-1.17.apk` đã cài trên Tab S7, ký cùng khóa với 1.15/1.16; hai ứng dụng thử riêng đã gỡ sau khi hoàn tất kiểm tra.
