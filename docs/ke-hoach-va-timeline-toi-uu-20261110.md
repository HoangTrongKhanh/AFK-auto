# Kế hoạch và timeline tối ưu AFK Auto

Ngày lập: 10/11/2026. Cơ sở: [báo cáo khảo sát mã nguồn](bao-cao-toi-uu-toan-ung-dung-20261109.md).

## 1. Mục tiêu và giả định

Ưu tiên trải nghiệm đơn giản, bot hoạt động ổn định, code dễ bảo trì; mọi tối ưu thuật toán phải được đo trước khi áp dụng.

Ước lượng cho một người quen dự án, làm tập trung, có quyền chạy môi trường Android và có máy thử khi cần. Một ngày là một ngày công; mỗi tuần tính 5 ngày làm việc. Ngày 1 là ngày thực sự bắt đầu triển khai, chưa phải ngày đã lên lịch. Thời gian chờ nguồn ảnh, thiết bị hoặc phản hồi người dùng không tính vào ngày công.

**Kế hoạch cơ sở: 30 ngày công, khoảng 6 tuần. Dự phòng thêm 5 ngày, tổng ngân sách lịch khoảng 7 tuần.** Phần nghiên cứu thuật toán nâng cao là gói tùy chọn thêm 10–15 ngày, chỉ thực hiện khi có dữ liệu đủ tốt.

Các khoảng thời gian trong báo cáo nghiên cứu trước là ước lượng cấp giai đoạn. Bản kế hoạch này dành riêng thời gian tích hợp, kiểm thử Android và chuẩn bị phát hành, nên dài hơn việc chỉ cộng thời gian sửa code.

## 2. Mức độ ưu tiên

- **P1 — làm trước:** xử lý nghẽn dữ liệu, lệch trạng thái thao tác và những điểm UI gây khó dùng. Là điều kiện cho bản cải tiến đầu tiên.
- **P2 — làm tiếp:** cấu trúc code, độ bền dữ liệu, quản lý bộ nhớ/lưu trữ, quy trình kiểm thử và phát hành. Cần hoàn thành trước khi coi đợt tối ưu đã kết thúc.
- **P3 — thử có điều kiện:** thuật toán nâng cao hoặc giảm kích thước APK. Chỉ nhận thay đổi khi có lợi ích đo được.

Chưa xác định sự cố P0 đang xảy ra. Nếu tái hiện lỗi làm mất dữ liệu hoặc thao tác sai nghiêm trọng, đưa việc khắc phục lên trước lịch dưới đây.

## 3. Kế hoạch từng phần

| Mã | Kế hoạch | Ưu tiên | Công sức | Lịch cơ sở | Phụ thuộc | Kết quả bàn giao |
|---|---|---|---|---|---|---|
| A | Đo hiện trạng và làm môi trường kiểm thử chạy được | P1 | 2 ngày | Ngày 1–2 | Không | Số đo nền, bộ dữ liệu cố định, danh sách ca thử, kết quả Python/Kotlin hiện hành |
| B | Tối ưu nạp dữ liệu và kho mẫu | P1 | 5 ngày | Ngày 3–7 | A | Snapshot kho đã kiểm chứng; đọc dữ liệu/ảnh nền; chỉ cập nhật danh sách khi cần; giảm cập nhật log khi ẩn |
| C | Sửa độ tin cậy thao tác và tương thích quyền | P1 | 3 ngày | Ngày 8–10 | A; tích hợp sau B | Cử chỉ thất bại không làm đổi trạng thái; kiểm tra kết quả chép đội; quyền thông báo theo phiên bản Android |
| D | Đơn giản hóa UI và bảng nổi | P1 | 5 ngày | Ngày 11–15 | B, C | Màn Chạy/Tướng gọn hơn; tìm/lọc; phân biệt chưa rõ tên/khung; trở về tự đọc; vùng chạm và trạng thái điều khiển rõ |
| E | Tách code theo trách nhiệm và tăng độ bền | P2 | 7 ngày | Ngày 16–22 | B, C; UI D đã ổn định | Tách chọn đội, đọc tướng, lưu dữ liệu; trạng thái có kiểu; cleanup ảnh khi lỗi/hủy; quota và kiểm thử quyết định Kotlin |
| F | Thử các tối ưu thuật toán ít rủi ro | P2 | 4 ngày | Ngày 23–26 | A, E | Cache mẫu nhiều tỷ lệ; thử chờ theo trạng thái; báo cáo đối chiếu tốc độ, số lần chụp và kết quả nhận diện |
| G | Tích hợp, kiểm thử và chuẩn bị bản phát hành | P2 | 4 ngày | Ngày 27–30 | B–F | Bộ kiểm thử tái lập, phiên bản thư viện được ghi/khóa, tài liệu cập nhật, APK thử và báo cáo nghiệm thu |
| H | Nghiên cứu thuật toán nâng cao | P3 | 10–15 ngày bổ sung | Sau ngày 30 nếu đủ nguồn | G và nguồn đánh giá độc lập | Thử ghép trang, ghép tên toàn cục, xếp hạng đội theo hiệu quả thời gian; quyết định giữ/loại từng phương án |

Thứ tự bảng là lịch tuần tự cho một người; không giả định nhiều người làm đồng thời. Trong B/D chỉ tách lớp tối thiểu để phục vụ thay đổi; E hoàn thiện cấu trúc còn lại, tránh tính hai lần cùng một việc. Mỗi phần đã gồm kiểm thử sát với thay đổi; G dành cho tích hợp và kiểm tra toàn luồng.

### A — đo và chuẩn bị

1. Giải quyết đường chạy Gradle trong môi trường cho phép ghi; chạy lại kiểm thử Kotlin. Lỗi quyền bộ nhớ đệm trước đây chưa phải lỗi sản phẩm.
2. Cố định APK, phiên bản mẫu, hồ sơ và bộ ảnh hồi quy.
3. Đo mở app, mở Tướng, số lần đọc/hash kho, thời gian từng pha của bot và bộ nhớ khi đọc lặp.
4. Chốt danh sách máy/Android có thể thử thật; các ca thiếu thiết bị ghi rõ chưa chạy.

Nghiệm thu: có số đo lặp, median/p95 và môi trường đi kèm; không dùng kết quả cũ làm kết quả hiện tại.

### B — hiệu năng dữ liệu

Nạp một snapshot kho cho mỗi tác vụ, lập trạng thái mẫu một lần, vô hiệu hóa cache sau duyệt/thu hồi/cập nhật/rollback. Chuyển đọc ảnh/JSON khỏi luồng giao diện; danh sách Tướng tái sử dụng hàng, cập nhật theo dữ liệu thay đổi. Hạn chế dựng lại log khi người dùng không mở nhật ký.

Nghiệm thu: không còn đọc/hash kho theo từng hàng hiển thị; thay bộ mẫu phản ánh đúng; không dựng toàn bộ mục Tướng mỗi lần quay về app. Nếu số đo A xác nhận nghẽn, đặt mục tiêu giảm p95 mở Tướng ít nhất 30%; đây là mục tiêu cần đo, chưa là kết quả cam kết.

### C — thao tác và tương thích

Phân biệt thao tác đã gửi, bị hủy, hết thời gian và hậu điều kiện thành công. Không đánh dấu đội đã chép khi thiếu bằng chứng; giới hạn thử lại và hiển thị lý do chờ. Sửa đường kiểm/xin thông báo theo API hỗ trợ.

Nghiệm thu: các ca cử chỉ trả false, màn chuyển chậm và screenshot timeout không làm bot cập nhật sai đội; thử thông báo bật/tắt trên các phiên bản Android có sẵn.

### D — UI sử dụng hằng ngày

Giữ bốn mục chính: Chạy, Tướng, Lịch sử, Cài đặt. Màn Chạy ưu tiên hồ sơ, trạng thái và Chạy/Dừng. Màn Tướng đưa kết quả/cần xác nhận lên đầu; tách quản lý mẫu dùng chung vào chi tiết. Thêm tìm kiếm, bộ lọc, nguồn kết quả và “Dùng kết quả tự đọc”. Nhớ tab/vị trí cuộn; đồng bộ chế độ bảng nổi với app; cải thiện vùng chạm.

Nghiệm thu: sau thiết lập có thể Chạy/Dừng trong 1–2 thao tác; tìm/sửa một tướng trong tối đa 3 thao tác sau khi vào Tướng theo luồng đã định; hiểu lý do chờ/dừng mà không cần đọc log. Kiểm tra font lớn và màn hình hẹp. Các chỉ tiêu thao tác cần thử thực tế với người dùng.

### E — code và độ bền

Tách lần lượt policy chọn đội, phiên đọc tướng và repository dữ liệu; giữ tương thích JSON hiện có. Chuẩn hóa trạng thái, cấu hình phiên và sở hữu ảnh. Ghi phiên nền có cleanup khi lỗi/hủy; giới hạn hàng đợi debug và dung lượng các phiên không còn tham chiếu. Bổ sung kiểm thử quyết định Android và các ca lỗi dữ liệu.

Nghiệm thu: hành vi hồi quy tương đương; dừng giữa phiên/lỗi ghi không phá kết quả cũ; dữ liệu tay vẫn thuộc đúng hồ sơ; mẫu kiểm tra được bảo vệ; không tăng bộ nhớ dần qua số phiên lặp đã định trước.

### F — thử tối ưu có đối chiếu

Ưu tiên chuẩn bị sẵn mẫu sao nhiều tỷ lệ, sau đó thử chờ theo trạng thái ở một vài chuyển màn thường gặp. Chỉ thêm top-3 khoảng cách nếu profiling cho thấy có ý nghĩa. Giữ phương án hiện hành để quay lại.

Nghiệm thu: tối ưu thuần hiệu năng giữ kết quả trong sai số đã thống nhất; không tăng lỗi thao tác. Đo cả số lần chụp và chi phí CPU/pin khi thử polling. Nếu không có lợi ích hoặc thiếu bằng chứng, bàn giao kết quả thử nghiệm và giữ cách cũ; phần F vẫn được coi là hoàn thành nghiên cứu.

### G — tích hợp và phát hành

Gói fixture có manifest/hash, ghi phiên bản runtime, khóa môi trường Python đã kiểm; cập nhật README/hướng dẫn và kiểm đường ký bản phân phối. Chạy lại hồi quy Python/Kotlin cùng luồng Android trên nguồn hiện có. So số đo trước/sau. R8 chỉ thử nếu còn thời gian và kiểm được JNI/OpenCV; có thể chuyển sang P3.

Nghiệm thu: có APK thử, danh sách thay đổi, kết quả kiểm thử, giới hạn hỗ trợ và hướng dẫn khôi phục. Ca không có thiết bị/nguồn phải ghi “chưa chạy”; không tuyên bố hỗ trợ rộng chỉ từ Tab S7. Lịch này kết thúc ở bản sẵn sàng phát hành; thời gian phân phối cho người dùng tùy kênh triển khai.

### H — nghiên cứu bổ sung

| Hạng mục | Công sức tham khảo | Điều kiện bắt đầu | Quyết định áp dụng |
|---|---|---|---|
| Ghép thẻ giữa các trang bằng vị trí + ảnh | 3–4 ngày | Có nhãn bỏ sót/trùng và ảnh cuộn đủ khó | Giảm so ảnh/thời gian mà không tăng gộp sai |
| Ghép tên toàn cục có lựa chọn không gán | 3–4 ngày | Nguồn độc lập có tên chuẩn và ca nhập nhằng | Tăng tên đúng, không tăng tên sai; giữ được trạng thái chưa rõ |
| Chọn đội theo xác suất thắng/thời gian | 4–7 ngày | Log đủ hồ sơ, chế độ, phiên và thời gian; có điều kiện so phiên thực | Có lợi ích qua phiên so sánh thực, không chỉ điểm offline |

Các hạng mục H có thể dừng sau bước đánh giá tính khả thi; không yêu cầu thay thuật toán bằng mọi giá. Thời gian thu dữ liệu bổ sung có thể kéo dài hơn thời gian nghiên cứu.

## 4. Timeline theo tuần và mốc bàn giao

| Tuần | Công việc chính | Mốc xem được |
|---|---|---|
| 1 | A + ba ngày đầu B | Số đo nền; bản thử nạp dữ liệu |
| 2 | Hoàn thành B, C | M1: dữ liệu nhẹ hơn, thao tác đáng tin cậy hơn |
| 3 | D | M2: bản thử UI Chạy/Tướng và bảng nổi |
| 4 | Năm ngày đầu E | Các phần chọn đội/đọc tướng đã tách, có kiểm thử |
| 5 | Hoàn thành E, ba ngày đầu F | M3: cấu trúc và độ bền hoàn chỉnh; số đo thuật toán ban đầu |
| 6 | Hoàn thành F, G | M4: APK sẵn sàng phát hành và báo cáo trước/sau |
| 7 | Dự phòng tối đa 5 ngày | Sửa phát sinh qua kiểm thử/tích hợp; không tự mở rộng phạm vi |
| Sau đó | H nếu đủ dữ liệu | Báo cáo quyết định từng thuật toán sau thêm 2–3 tuần công |

Nếu cần bàn giao sớm: ưu tiên M1 sau khoảng 10 ngày công, rồi M2 sau khoảng 15 ngày. Không cần chờ nghiên cứu H để hưởng lợi từ UI và hiệu năng dữ liệu.

## 5. Điểm có thể làm thay đổi lịch

- Chưa có máy Android khác hoặc nguồn độc lập: vẫn làm A–G theo dữ liệu có, giới hạn tuyên bố hỗ trợ; H phụ thuộc dữ liệu được lùi.
- Mã đang có nhiều thay đổi chưa commit: khi bắt đầu phải xác định mốc mã được phép sửa và giữ nguyên thay đổi có sẵn.
- Nếu kiểm thử nền phát hiện lỗi cũ: ghi riêng phạm vi và điều chỉnh lịch, không âm thầm tính là lỗi mới của đợt tối ưu.
- Nếu đo nền cho thấy chờ game chiếm đa số thời gian: ưu tiên tối ưu luồng thao tác/chờ, giảm thời gian dành cho các phép tính ảnh nhỏ.
- Nếu hết dự phòng: đánh giá lại phạm vi và ước lượng trước khi tiếp tục; ưu tiên độ đúng và dữ liệu, lùi các thử nghiệm P3.

## 6. Trạng thái hiện tại

**Đã hoàn thành:** báo cáo khảo sát và kế hoạch này. Lần khảo sát trước chạy 170 unittest Python đạt; kiểm thử Kotlin chưa khởi động được vì thư mục Gradle chỉ đọc.

**Chưa triển khai A–H.** Chưa có số đo Android mới hoặc phần trăm cải thiện thực tế. Lịch là dự kiến theo công sức, không phải lịch chạy tự động hoặc ngày hoàn thành đã cam kết.
