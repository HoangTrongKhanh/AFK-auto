# Hồ sơ tài khoản và quản lý mẫu Android — 1.18

Mỗi hồ sơ có lựa chọn khung tay, kết quả đọc, ảnh thẻ, ứng viên và xác nhận ảnh riêng. Bộ mẫu nhận diện tên dùng chung. Trong mục Khung tướng, chọn đúng hồ sơ khớp tài khoản đang mở trong game trước khi đọc. Tạo hồ sơ mới bằng “Thêm tài khoản”; tạo hồ sơ không tự chuyển tài khoản trong game. Không chuyển hồ sơ hoặc đổi bộ mẫu trong lúc tác vụ đang chạy.

Lần đầu mở 1.18 tự sao chép dữ liệu cũ vào một hồ sơ riêng, kiểm tra mã nội dung của toàn bộ tệp đã sao chép, rồi mới lưu hồ sơ đang chọn. Dữ liệu gốc được giữ làm bản lưu. Tên mặc định lấy từ số thẻ trong kết quả cũ; người dùng có thể đổi tên. Người dùng đã xác nhận 10 lựa chọn khung tay hiện tại thuộc tài khoản 120 tướng.

Mỗi phiên đọc ghi `profile_id` và `profile_name` cùng mã lựa chọn tay trước/sau. Khung được ghi vào thư mục của hồ sơ đã chọn, không dùng dữ liệu hồ sơ khác. Các đường dẫn ảnh trong kết quả vẫn tương đối với thư mục hồ sơ.

## Mẫu tên

- “Đúng tướng” lưu mẫu chờ duyệt; mẫu chờ không tham gia nhận diện.
- Duyệt mẫu tạo phiên bản mới. Không thay nhãn hay trọng số mô hình khung.
- Bỏ tích hoặc “Thu hồi mẫu” tạo phiên bản loại đúng mẫu cá nhân đã duyệt, giữ các mẫu khác và lịch sử.
- Khi cập nhật bộ mẫu trong APK, chỉ chuyển các mẫu cá nhân đang được dùng ở bản hiện hành. Không đưa lại các mẫu đã thu hồi hoặc mẫu nằm trong phiên bản đã bỏ qua khi khôi phục.
- Mẫu trùng bộ mới, xung đột tên hoặc thuộc dữ liệu kiểm tra được giữ ngoài phần nhận diện mới và có thông báo lý do. Hàng chờ được giữ lại.
- Khôi phục đi lùi từng phiên bản đã ghi trong lịch sử, có thể qua các bộ gốc v2 tương thích. Việc mở lại ứng dụng không tự hủy lựa chọn khôi phục. Nếu đang dùng bộ gốc cũ, “Dùng bộ mẫu mới nhất” quay về bộ đóng gói hiện tại và chuyển mẫu cá nhân hợp lệ.
- Không khôi phục bản chứa mẫu cá nhân thuộc bộ kiểm tra mới được bảo vệ. Lịch sử cũ trước 1.18 giữ được bản trước mà con trỏ cũ còn ghi; lịch sử nhiều bước được lưu từ bản này.

Bộ hiện tại vẫn 146 mẫu mặt/125 tên, khung giữ 29 mẫu học/14 validation. Hai bộ khung niêm phong và quy tắc/ngưỡng nhận diện không đổi.

## Kiểm tra

Có kiểm thử chuyển dữ liệu và tách hồ sơ; hồ sơ hỏng dừng đọc thay vì nhập lại từ bản cũ; thu hồi mẫu giữ các mẫu khác; nhiều bước khôi phục; chuyển bộ gốc giữ mẫu đang dùng và hàng chờ; bảo vệ mới không bị bỏ qua bằng khôi phục; phục hồi khi ghi trạng thái hàng chờ bị gián đoạn. Kiểm tra native chạy trong thư mục thử riêng, không duyệt/loại mẫu người dùng.

Bằng chứng: `debug/ho-so-mau-20261109/`.

## Kết quả thực tế 09–10/11/2026

Đã cài bản cuối 1.18, ký cùng khóa với 1.17. 8 kiểm thử JVM cho hồ sơ/vòng đời mẫu đều qua. Kiểm tra native trên SM-T870 cũng qua chuyển/tách hồ sơ, mẫu chờ không tham gia nhận diện, thu hồi mẫu đã duyệt, chuyển bộ gốc, khôi phục qua bộ gốc v2 tương thích và giữ nguyên mô hình khung. Kiểm tra giao diện đã bấm thực sự vào bỏ tích, Thu hồi mẫu và Lưu hồ sơ; tất cả qua trên bản cuối.

| Ca thử bản 1.18 | Kết quả |
|---|---|
| Hồ sơ 120 | Đếm đủ 120, nhận 119 tên/1 chưa rõ; 85 có khung/35 không. Python đọc lại cùng 16 ảnh khớp hoàn toàn. 10 lựa chọn khung tay giữ đúng mã nội dung trước/sau. |
| Hồ sơ 48 mới | Trước lần đọc không có kết quả hay khung tay của hồ sơ 120. Thu đủ 48, nhận 47 tên/1 chưa rõ; 4 có khung/43 không/1 chưa rõ. Python đọc lại cùng 7 ảnh khớp hoàn toàn. |
| Nhập sai 49 khi thực tế 48 | Dừng và giữ nguyên mã JSON 48 cũ; khung tay vẫn rỗng, không mang dữ liệu từ hồ sơ khác. |
| Lọc 5 thẻ cố định, không có thẻ lưới | Có dịch chuyển ban đầu; không xác minh được cuộn ngược nên từ chối lưu và giữ nguyên JSON 48. Đây chưa phải ca dương tính cho nhánh hoàn toàn không cuộn. |
| Lọc 6: 5 cố định + 1 lưới | Đọc thành công đủ 6 tên, 3 ảnh; khung 3 có/2 không/1 chưa rõ. Tên, khung và biên khớp Python. |

Tên chưa rõ ở hồ sơ 120 nằm ở nhóm 12; so với tập tên cũ còn thiếu Shemira, đây chỉ là đối chiếu ứng viên chứ chưa dùng làm nhãn học. Hồ sơ 48 có 1 khung chưa rõ ở thẻ máy nhận tên Aurora: cả hai quan sát chưa được xác minh đủ biên. Không đổi “chưa rõ” thành “không khung”. Bộ mẫu vẫn v-647cbc8e579f3e3d, không duyệt 9 mẫu chờ thật của người dùng trong quá trình thử. Các mẫu giả trong kiểm tra giao diện thuộc ứng dụng validation riêng.

Sau thử lọc đã bỏ lọc và chạy lại toàn bộ 48 để lưu dữ liệu đầy đủ. Lượt cuối thu đủ 48 thẻ, nhận 47 tên/1 chưa rõ, khung 4 có/43 không/1 chưa rõ; đối chiếu Python khớp hoàn toàn. Kết quả lưu riêng tại `restore-48/`. Hồ sơ 48 vẫn không có lựa chọn khung tay. Sau khi gỡ ứng dụng kiểm thử, dịch vụ bản chính vẫn kết nối; lần chụp giao diện cuối bị màn khóa bảo mật che nên không dùng ảnh đó làm bằng chứng hiển thị kết quả.

## Phần còn thiếu nguồn

Bước 3 đã có kế hoạch ghim APK/bộ mẫu tại `ke-hoach-doc-lap.json`, trạng thái `awaiting_independent_source`. Người dùng xác nhận chỉ có hai tài khoản đã tham gia phát triển, chưa có tài khoản mới/thiết bị khác/tài khoản thực sự chỉ có vài tướng. Vì vậy không ghi nhận thêm phép đo độc lập mới. Chi tiết: [kế hoạch kiểm chứng 1.18](kiem-chung-1.18.md).

Bước 4 đã thử máy thật 120/48, lọc 6, lọc 5 và số tham chiếu sai. Ca lọc 5 bị từ chối là một giới hạn cần tiếp tục xử lý/kiểm chứng; nhánh hoàn toàn không cuộn và thiết bị khác vẫn thiếu nguồn. Các bộ 50/40 lịch sử giữ nguyên, các lượt đọc lại hai tài khoản chỉ dùng làm hồi quy.
