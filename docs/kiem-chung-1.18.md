# Kiểm chứng sau bản 1.18

## Nguồn hiện có

Người dùng xác nhận chỉ có hai tài khoản đã tham gia phát triển (120 và 48 tướng), chưa có tài khoản khác, tài khoản thực sự không cuộn được hoặc thiết bị khác Tab S7. Vì vậy chưa có nguồn để chấm độ chính xác trên tài khoản mới hay xác nhận hỗ trợ máy khác.

## Bước 3 — vòng độc lập tiếp theo

Ghi nhận trạng thái `awaiting_independent_source` trong kế hoạch có mã APK/bộ mẫu; chưa tạo một bộ kết quả độc lập mới. Khi có nguồn mới:

1. Ghi số tướng sở hữu từ người dùng/Bộ Sưu Tập và xác nhận tài khoản chưa dùng bổ sung mẫu. Tạo hồ sơ riêng trong ứng dụng.
2. Ghim đúng APK và bộ mẫu trước khi chụp; giữ hàng chờ chưa duyệt. Mỗi phiên phải ghi đúng hồ sơ và phiên bản đã ghim.
3. Thu ảnh gốc, cố định kết quả máy và mã nội dung trước khi lấy nhãn chuẩn. Đăng ký nguồn/pixel vào danh sách bảo vệ; không đưa ảnh này vào mẫu học.
4. Tạo bảng ảnh không hiện dự đoán. Gán tên và khung từng thẻ, đánh dấu chưa rõ khi không đủ bằng chứng; kiểm tra sao/viền trên ảnh gốc. Dùng tên chuẩn/rút gọn đã thống nhất (ví dụ Elijah & Lailah → SS).
5. Chấm riêng đúng/sai/chưa rõ cho tên và khung; bỏ sót/đếm trùng theo danh sách chuẩn; báo riêng số ảnh trùng mẫu cũ. Giữ đủ cả có khung và không khung.
6. Kiểm tra lại mã APK, bộ mẫu, nguồn và dự đoán; công cụ phải từ chối khi nguồn thay đổi. Chỉ đánh giá, không chỉnh quy tắc theo đáp án của bộ này.

Đối chiếu Python–Android hoặc chụp lại hai tài khoản cũ được ghi là hồi quy cùng nguồn, không thay cho vòng tài khoản mới.

## Bước 4 — kiểm tra máy thật

| Ca | Cách làm | Điều kiện đạt |
|---|---|---|
| Tài khoản lớn | Hồ sơ 120, số tham chiếu 120 | Đủ 120 thẻ; hai chiều/chồng lấp hợp lệ; khung tay giữ nguyên trong hồ sơ này; ảnh và tên/khung khớp Python |
| Tài khoản ít | Hồ sơ 48, số tham chiếu do người dùng xác nhận lại | Đủ số thẻ; không mang 10 lựa chọn của hồ sơ 120; kiểm tra hai chiều; ảnh đọc lại khớp Python |
| Danh sách lọc | Lọc phe trên tài khoản ít tướng, xác nhận số thẻ thực tế gồm cả nhóm cố định | Đếm đúng danh sách hiện tại và căn đủ biên; cuối thử phải bỏ lọc và đọc lại toàn bộ danh sách vào hồ sơ |
| Tham chiếu sai | Số dự kiến khác nguồn chuẩn trên một phiên thử | Báo không hợp lệ và giữ nguyên JSON/khung tay cũ |
| Không thể cuộn | Tài khoản thực sự chỉ có vài tướng, cả hai chiều không dịch chuyển | Mốc đầu, số tham chiếu độc lập, đủ biên, mặt ổn định và không trùng; thử giả lập chưa thay cho nguồn này |
| Thiết bị khác | Ảnh thật trên máy khác Tab S7 | Kiểm tra quyền/chụp/cuộn/đếm, vùng sao/viền và tên/khung; ảnh thu nhỏ/đổi kích thước không được tính là máy mới |

Các ca chưa có nguồn được ghi `not_run_missing_source`. Những ca đã có ảnh cũ nhưng chưa chạy thu thật trên Android được phân biệt với kiểm tra ảnh hồi quy. Bằng chứng lượt mới lưu trong `debug/ho-so-mau-20261109/`.
