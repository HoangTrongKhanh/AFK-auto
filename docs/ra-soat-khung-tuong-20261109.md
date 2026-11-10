# Rà soát phần đọc khung tướng — 09/11/2026

Cập nhật 10/11: các mục 1, 2 bên dưới đã được triển khai trong 1.18 và qua kiểm tra hồ sơ/vòng đời mẫu trên JVM, Tab S7 và giao diện. Xem [kết quả bản 1.18](ho-so-va-mau-android.md). Các nhận xét chi tiết bên dưới mô tả bản 1.17 tại lúc rà soát; bước kiểm chứng nguồn mới và các trường hợp còn thiếu được theo dõi trong [kế hoạch 1.18](kiem-chung-1.18.md).

Bản đã cài là Android 1.17, dùng cùng bộ mẫu Python `v-647cbc8e579f3e3d`: 146 mẫu mặt/125 tên. Lượt đọc thật mới nhất đã xác minh 120 thẻ, nhận 120 tên duy nhất, 0 tên chưa rõ; giữ nguyên 10 lựa chọn khung tay. Các kết quả này chứng minh số lượng đầu ra trên tài khoản đã thử. Độ chính xác tên trên tài khoản chưa dùng để bổ sung mẫu vẫn cần kiểm chứng riêng.

Rà soát lần này gồm mã nguồn, báo cáo máy, mã nội dung APK/bộ mẫu và hai bộ kiểm tra niêm phong. Các hạn chế quản lý dữ liệu dưới đây được xác định từ đường chạy trong mã; chưa thực hiện đổi tài khoản, duyệt mẫu hay cập nhật APK trên điện thoại để tái hiện chúng trong lần rà soát này. Không thay thuật toán hoặc dữ liệu khung tay.

## Trạng thái sáu phần ban đầu

| Phần | Trạng thái | Phạm vi đã có / việc còn lại |
|---|---|---|
| 1. Bổ sung mẫu tên đã xác nhận | Đã hoàn thành đợt hiện tại | Giữ 124 mẫu cũ, thêm 22 mẫu có ảnh đọc tên trực tiếp; tổng 146 mẫu/125 tên. Tài khoản vừa thử nhận đủ 120 tên. Chưa chứng minh bao phủ mọi diện mạo/tướng tương lai. |
| 2. Kiểm chứng thu đủ danh sách | Đã có và đã thử các nguồn chính | Python đã thử 48 tướng, danh sách lọc 6 và tài khoản lớn; Android đã đọc thật đủ 120, có kiểm tra đầu/cuối/chồng lấp và số tham chiếu. Danh sách thật hoàn toàn không cuộn vẫn thiếu; bản 1.17 chưa chạy thật lại tài khoản 48 trên Android. |
| 3. Hoàn thiện đánh giá khung | V2 đã triển khai | Mô hình giữ 29 mẫu học/14 validation. Bộ v2 niêm phong đạt 40/40 trong vòng trước, gồm 35 có/5 không khung; 90 thẻ cũ tiếp tục dùng hồi quy. 120 ảnh đại diện lượt cuối đủ vùng sao/viền. Cần thêm nguồn mới, đặc biệt lớp không khung, để mở rộng đánh giá. |
| 4. Quản lý mẫu học | Python đã có; Android còn việc | Đã có chờ duyệt, duyệt/loại, phiên bản, bảo vệ bộ kiểm tra và khôi phục có giới hạn. Còn tách dữ liệu tài khoản, thu hồi mẫu đã duyệt, chuyển mẫu cục bộ khi cập nhật và làm rõ phạm vi khôi phục. |
| 5. Đánh giá độc lập | Đã có cho khung ở vòng trước; chưa đủ cho toàn bộ bản cuối | Các bộ 50/40 vẫn nguyên vẹn. Ba lượt 48 ảnh/360 kết quả và lượt thật cuối thuộc cùng tài khoản phát triển. Cần một vòng mới cố định 1.17 trước khi chụp, gán chuẩn tên/khung/số lượng, không học từ bộ đó. |
| 6. Chuyển sang Android | Đã hoàn thành trên Tab S7 | Đã cài 1.17, đối chiếu JVM/Tab S7 qua 90 thẻ khung, 48 ảnh và 360 kết quả danh sách; đọc thật 120/120 tên. Chưa có kiểm tra thiết bị/độ phân giải khác. |

## Các việc nên làm tiếp, theo thứ tự

### 1. Tách dữ liệu khung theo tài khoản

Hiện khung tay, kết quả đọc và ảnh xác nhận được lưu chung trong thư mục ứng dụng, theo tên tướng; chưa có mã hồ sơ tài khoản. Mỗi lần đọc vẫn lấy cùng `khung_tay.json`, và lựa chọn tay luôn ghi đè kết quả tự đọc. Vì đã dùng nhiều tài khoản để thử, cần gắn dữ liệu này vào đúng hồ sơ trước khi sử dụng luân phiên lâu dài. Chưa kết luận 10 lựa chọn hiện tại bị sai.

Bằng chứng mã: `KhungTuong.kt` phần `TEP_TAY`, `docTay`/`ghiTay`; `Leo.kt:999` và `Leo.kt:1017`; `MainActivity.kt:269`. Nên giữ mẫu nhận diện dùng chung nhưng tách kết quả đọc, lựa chọn khung và xác nhận ảnh theo tài khoản. Khi chuyển tài khoản, hiển thị rõ hồ sơ đang dùng và yêu cầu đối chiếu lại số tướng.

### 2. Hoàn thiện quản lý mẫu tên trên Android

Có ba điểm cụ thể:

- **Thu hồi mẫu đã duyệt:** bỏ tích “Đúng tướng” gọi `review(id,false)`, nhưng hàm chỉ nhận mẫu trạng thái `pending`. Với mẫu đã `approved`, lỗi bị bỏ qua rồi ảnh xác nhận bị xóa; mẫu vẫn còn trong phiên bản nhận diện đang dùng. Cần tạo bản mới loại đúng mẫu đó, đồng thời giữ lịch sử và các mẫu khác. Bằng chứng: `MainActivity.kt:391` và `KhoMauAndroid.kt:40`.
- **Giữ mẫu cục bộ khi cập nhật bộ đóng gói:** khi `python_version` đổi, `current()` cài và chọn bộ mới trong APK. Các mẫu duyệt trên điện thoại ở bản cũ không tự gộp sang bộ mới; thư mục bản cũ vẫn được giữ. Cần chuyển các mẫu cá nhân còn hợp lệ, kiểm tra trùng/xung đột và nguồn bị bảo vệ trước khi kích hoạt. Bằng chứng: `KhoMauAndroid.kt:15`–`26`.
- **Phạm vi khôi phục:** `rollback()` chỉ nhận bản trước có cùng `python_version`. Nút đang hiển thị chung, nên không có nghĩa có thể quay từ bộ đóng gói 1.17 về bộ 1.16. Cần hiển thị rõ bản có thể khôi phục và giải thích trường hợp bị giới hạn, hoặc triển khai cơ chế khác có kiểm tra tương thích. Bằng chứng: `KhoMauAndroid.kt:51`–`53`, `MainActivity.kt:278`.

Kiểm thử kho mẫu hiện có đã thử duyệt, loại mẫu chờ, dữ liệu bị bảo vệ, tệp hỏng và khôi phục trong cùng bộ gốc. Chưa có ca kiểm tra chuyển bộ gốc sau cập nhật hay thu hồi một mẫu đã duyệt.

### 3. Kiểm chứng độc lập toàn bộ bản cuối

Cố định APK/bộ mẫu trước khi chụp nguồn mới. Gán tên, khung và số lượng chuẩn từ nguồn độc lập; chấm riêng đúng/sai/chưa rõ, bỏ sót và đếm trùng. Giữ đủ trường hợp có khung/không khung và diện mạo khác; không bổ sung các ảnh này vào mẫu học.

120/120 hiện là số tên máy nhận được. Đối chiếu Python–Android cho thấy hai bên cho cùng kết quả; phép đo đúng/sai tên cần nhãn chuẩn riêng. Bộ khung 40 thẻ vòng trước không đo độ chính xác tên hay độ phủ toàn bộ danh sách.

### 4. Bổ sung các trường hợp chưa có máy thật

- Tài khoản chỉ có vài tướng, thực sự không thể cuộn, để kiểm tra nhánh đang mới được giả lập.
- Chạy bản Android cuối trên nguồn 48 tướng và danh sách lọc ngắn; lần thử thật 48/6 trước là Python, còn Android đã có đối chiếu ảnh nhưng chưa đủ bằng chứng chạy thu thật các nhánh đó.
- Một thiết bị/độ phân giải khác Tab S7 1600×2560 trước khi xác nhận hỗ trợ rộng.

### Việc hoàn thiện sau các mục trên

Giao diện hiện chỉ liệt kê các tướng quan trọng cho bot; nên bổ sung tổng số thẻ/tên/chưa rõ và cách mở nhóm chưa rõ để người dùng tự kiểm tra. Bộ đối chiếu đang phụ thuộc dữ liệu cục bộ trong `debug/` và kho cá nhân ngoài Git; nếu cần chạy trên máy khác, cần gói dữ liệu kiểm thử có mã nội dung và hướng dẫn phục hồi, không đưa ảnh cá nhân vào mã nguồn một cách mặc định.

## Bằng chứng kiểm tra lại

APK, bộ đóng gói Android và bản Python hiện hành có cùng phiên bản; mã nội dung APK khớp báo cáo phát hành. Hai bộ kiểm tra niêm phong giữ nguyên. Quy tắc v1 lịch sử được kiểm tra niêm phong theo v1; không ép mã v2 thành v1. Quy tắc v2 giữ đúng mã đã cố định.

Báo cáo trước: [hoàn thiện tên tướng](chin-the-chua-ro.md), [Android](android-khung-v2.md), [danh sách ngắn](danh-sach-ngan-va-dien-mao.md). Bằng chứng mới nhất: `debug/9-the-chua-ro-20261109/sat-nguong/summary.json` và `live-117/`.

Đã đọc lại bằng Python đúng 16 PNG của lượt thật 1.17 cuối: cả hai bên đều có 120 thẻ/120 tên, 85 có khung/35 không khung; tên, gợi ý, lý do tên, khung và biên chọn ảnh đều khớp, không có sai khác. Bằng chứng: `debug/9-the-chua-ro-20261109/sat-nguong/live-117/python-comparison.json`. Đây vẫn là đối chiếu cùng ảnh/cùng tài khoản.
