# Lỗi chọn Bản Ghi Thành Tích Huyền Linh — 10/11/2026

Nhật ký máy SM-T870 lúc 03:22–03:24 ghi nhận bot ở tiến trình AFK 450, đọc được 5 đội, chọn đội 3 (13073M) nhưng lặp “Không tới được đội 3 vừa chọn - đọc lại danh sách”. Màn thử trực tiếp hiện ghi Huyền Linh Sinh Vật 300; AFK và Huyền Linh có số ải riêng.

## Nguyên nhân đã tái hiện

Ảnh đại diện và viền đại diện động lấn vào vùng đọc tên, vốn bắt đầu cách mép thẻ 150px. Khi qua phải rồi quay trái, cùng tên bị đọc thành chữ ký khác: đội 3 khớp 0.4744, đội 4 khớp 0.4502, thấp hơn ngưỡng 0.85. Chuyển vùng đọc sang 200px loại phần đại diện lấn vào; trên hai cặp ảnh này độ khớp đều đạt 1.0. Không hạ ngưỡng nhận dạng.

Ngoài ra, bộ nhận màn yêu cầu chữ “Nhấn để đóng” đang nhấp nháy. Có ảnh đủ nút sao chép, nắm đấm và ô lọc nhưng bị nhận thành `khong_ro`.

## Thay đổi

- Đồng bộ vùng đọc tên trong Python và Kotlin.
- Nhận bảng bằng các mốc tĩnh khi chữ đóng mờ; khi cần đóng bảng, có tọa độ dự phòng bám đáy và kiểm tra lại màn hiện tại.
- Lưu ảnh và thông tin đội cần/đội đọc được khi chọn thất bại; dừng sau 3 lần chọn thất bại liên tiếp, đặt lại bộ đếm khi chép được.
- Thêm ảnh hồi quy và kiểm tra ở độ rộng 1600, 1080, 800; kiểm tra cùng đội hai chiều và đội khác nhau.

## Bằng chứng

Ảnh gốc và nhật ký: `debug/thanh-tich-20261110/`. Bộ ảnh hồi quy: `samples/thanh_tich_dong/`. Kết quả kiểm tra trực tiếp Android được lưu riêng sau khi chạy bộ thử thiết bị.

## Kết quả hoàn tất

- 34 kiểm thử Python qua (33 kiểm thử cũ và 1 kiểm thử mới có các trường hợp ở ba độ rộng).
- Bộ JVM có 21 kiểm thử: 20 qua ngay; kiểm thử nhận màn còn lại cần cập nhật ảnh `afk_751_06.png` từ `khong_ro` thành `thanh_tich`, đúng mục tiêu sửa lỗi. Chạy lại kiểm thử này và kiểm thử ảnh động mới đều qua. Các kiểm tra V2/tài khoản/kho mẫu hiện có đều qua.
- Đóng gói thành công 1.19 (versionCode 29).
- Thử trực tiếp SM-T870 bằng bộ nhận diện Kotlin/Android: từ đội 3 đi phải qua đội 4, 5 rồi trái về 4, 3; đối chiếu cùng đội; bấm sao chép và xác nhận về `doi_hinh`. Không bắt đầu trận đánh.
- Kết quả: `chosen_power=13073M`, `third_name_match=0.998165`, `fourth_name_match=0.995448`, `copied=true`, lực đội sau chép `12909M`.
- Báo cáo máy thật: `debug/thanh-tich-20261110/ket-qua-may-that.json`; ảnh từng bước: `debug/thanh-tich-20261110/thanh-tich-check/`.
