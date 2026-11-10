# Nhận diện khung v2 trên Android — 09/11/2026

Bản ứng dụng 1.14 chuyển quy tắc đang dùng trên Python sang Android. Bộ mẫu đóng gói lấy từ `v-bdcac19891f8515a`: 124 mẫu mặt đã duyệt, 29 mẫu khung để học; 14 mẫu khung validation được giữ riêng. Không chép 43 lựa chọn khung cá nhân của Python vào ứng dụng vì các lựa chọn đó thuộc tài khoản đã xác nhận.

## Hành vi

- Cắt theo biên thật, kiểm tra hai cạnh và vùng sao, đặt ảnh thẻ vào giữa khổ 130×205. Danh tính vẫn dùng ảnh mặt tham chiếu tương thích với mẫu cũ. Có bộ bổ sung cho hàng lưới chỉ một thẻ tóc trắng.
- Giữ nhiều diện mạo cho cùng tên. Chỉ tự gán khi điểm đủ và hơn tên đứng thứ hai 0,04; tên yếu được giữ ở trạng thái chưa rõ. Khi gộp chọn quan sát đủ biên rồi đến độ nét, thay cả ảnh mặt lẫn ảnh thẻ.
- Khung chưa rõ ghi JSON `null`; giao diện hiện “chưa rõ khung”. Không đưa trạng thái này vào danh sách thiếu khung. Hai quan sát chắc mâu thuẫn cũng trả chưa rõ. Lựa chọn tay vẫn ưu tiên.
- Cuộn xuống 300 px theo máy gốc, kiểm tra có thẻ lưới chung giữa hai trang (bỏ 5 thẻ cố định). Cuối danh sách phải cuộn ngược được rồi quay lại đúng ảnh cuối. Có ô nhập số tướng sở hữu để đối chiếu riêng cho mỗi lần đọc.
- Nhánh hoàn toàn không cuộn cần số lượng từ người dùng, mốc đầu, đủ biên, không trùng và ảnh mặt ổn định ở cả hai chiều. Nếu thiếu bằng chứng, danh sách rỗng, mất màn hoặc khác số đối chiếu thì giữ dữ liệu cũ.
- Ảnh nguồn của mỗi phiên, kết quả và bằng chứng được lưu trong thư mục ngoài của ứng dụng `vision-sessions/phien-…`. JSON chính vẫn được thay bằng `AtomicFile` sau khi ghi đủ ảnh phiên mới.

## Mẫu tên trên điện thoại

Tích “Đúng tướng” đưa ảnh mặt vào hàng chờ. Chỉ nút “Duyệt mẫu tên” mới phát hành và kích hoạt; “Loại mẫu” không thay bộ đang chạy. Mẫu cũ không bị ghi đè khi thêm diện mạo mới. Mỗi phiên bản có tệp ảnh, nguồn, trạng thái, vai trò và mã kiểm tra; chỉ đổi con trỏ sau khi ghi và kiểm tra xong. Có nút “Dùng lại bộ mẫu trước”. Lần đọc tiếp theo nạp lại phiên bản đã đổi.

Không tự học nhãn khung từ ảnh tự đọc hoặc lựa chọn tay. Mẫu khung chỉ cập nhật theo bộ phát hành từ Python. Hai bộ kiểm tra đã niêm phong được đóng gói danh sách bảo vệ nguồn/pixel để chặn nhập vào mẫu học. Mẫu chờ duyệt và mẫu loại không tham gia nhận diện. Các xác nhận kiểu cũ thiếu ảnh nguồn phải đọc lại trước khi thêm vào kho mới.

## Đối chiếu và tái hiện

`android/vision/xuat_mau_v2.py` xuất đúng bản Python đang kích hoạt thành `android/app/src/main/assets/vision-v2`. Tệp manifest ghim phiên bản, SHA của mô hình Python và từng tệp Android. `android/vision/tao_doi_chieu_v2.py` ghi đáp án mới vào `debug/vision-fixtures/<phiên-bản>/expected.json` và từ chối ghi đè bảng đã cố định. Bảng gốc của lượt 1.14 vẫn ở `debug/android-v2-20261109/expected.json`, không sửa mô hình hoặc bộ kiểm tra đã niêm phong.

Bộ đối chiếu có 90 ảnh thẻ, 42 ảnh gốc với 717 lượt thẻ và 4 danh sách gộp thành 296 kết quả. Nó so số thẻ, biên gốc/canvas, chất lượng, quyết định/lý do khung, đặc trưng, điểm sao, gộp thẻ, tên và lý do chưa rõ. Kiểm tra JVM đạt; sai khác điểm sao tối đa 0,000021, đặc trưng tối đa 0,000000060. Việc khớp Python không tự chứng minh mọi tên là đúng; độ chính xác tên vẫn theo phạm vi đã xác nhận trong báo cáo Python.

```bash
.venv/bin/python android/vision/xuat_mau_v2.py
.venv/bin/python android/vision/tao_doi_chieu_v2.py
cd android
JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 ./gradlew :vision:test --offline
JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 ./gradlew :app:assembleValidation :app:assembleValidationAndroidTest phatHanh --offline
```

Bản `validation` cài riêng, không dùng dữ liệu/Trợ năng của ứng dụng chính. `V2Instrumentation` chạy chính bộ đối chiếu Kotlin trên OpenCV Android; báo cáo nằm trong thư mục ngoài `vn.afkauto.leoai.validation/files/parity/result.json`. Bộ kiểm tra kho mẫu xác nhận hàng chờ không tác động bản đang dùng, bảo vệ nguồn kiểm tra, từ chối tệp hỏng, duyệt tên không sửa mô hình khung và khôi phục phiên bản.

## Kết quả Tab S7

Bộ đối chiếu chạy bằng OpenCV Android 4.12 trên SM-T870 đạt 90 thẻ, 42 ảnh gốc/717 lượt thẻ và 296 kết quả sau gộp. Quyết định khung, lý do và tên khớp Python; sai khác điểm sao tối đa 0,001197, đặc trưng tối đa 0,0000172. Đây là sai khác số học trong mức dung sai 0,003 và 0,000020, không đổi quyết định. Cuối lượt, heap native khoảng 30,1 MB, heap Java khoảng 46,0 MB; đây là số đo cuối lượt, không phải đỉnh.

Toàn bộ bài hồi quy trên thiết bị mất 656,8 giây, bao gồm đọc lại các trang để kiểm tra cả thẻ riêng lẻ lẫn gộp danh sách. Một phần lượt đầu chạy ở nền, sau đó chuyển ứng dụng thử ra trước; không dùng con số này làm thời gian của một lần đọc Hội Trường thực tế. Lấy mẫu 15 giây ở bước gộp/nhận tên cho thấy phần lớn thời gian nằm trong phép so mẫu OpenCV, không phải đọc tệp.

APK phát hành ký cùng chứng chỉ với 1.13, cài đè lên 1.14 thành công. Các báo cáo máy nằm tại `debug/android-v2-20261109/device.json`, `jvm.json`, `build.json` và `device-instrumentation.txt`. 12 kiểm thử hồi quy/kho mẫu/danh sách ngắn đều chạy lại và qua; kiểm tra v2 riêng đã chạy và qua, gồm chạy lại sau khi dùng lại điểm tên để bỏ xử lý lặp.

## Giới hạn

Mốc ảnh thật vẫn là Tab S7 1600×2560; chưa có phép đo trên thiết bị khác. Danh sách hoàn toàn không cuộn trên tài khoản chỉ vài tướng vẫn chưa có nguồn máy thật; không coi phép thử danh sách lọc 6 thẻ là bằng chứng cho trường hợp không cuộn. Hai bộ khung 50/40 và các phiên tên đã được dùng ở giai đoạn phát triển trước, nên lượt đối chiếu Android là kiểm tra chuyển đổi và hồi quy, không phải bộ kiểm chứng độc lập mới.

### Lượt đọc trực tiếp đầu tiên

Phiên mới trên tài khoản đang mở (cấp cộng hưởng 858) thu 16 ảnh và gộp 120 thẻ ở cả Python lẫn Android, khác mốc tham chiếu 121. Ứng dụng đã dừng đúng điều kiện, không ghi đè kết quả. `previous_result_sha256` bằng `current_result_sha256` và mã lựa chọn tay trước/sau cũng bằng nhau. Đã chụp riêng 12 ảnh Bộ Sưu Tập, ghép vị trí 27 hàng và kiểm tra trực quan 131 ô: 11 ô xám chưa sở hữu, 120 ô có màu. Hai thẻ cơ bản Chippy/Hammie có màu nhưng không có trang trí vàng vẫn được tính sở hữu; loại các ô nền trống cuối hàng. Không dùng chính số đếm Hội Trường làm số chuẩn. Bằng chứng: `collection-858/ownership-verified.json` và `ownership-review.jpg`.

### Lượt đọc theo nguồn đã xác minh

Đã chạy lại ứng dụng chính với mốc 120 lấy từ Bộ Sưu Tập. Thu 16 ảnh, xác minh đầu/cuối và chồng lấp lưới; lưu 120 nhóm thẻ thành công. Python đọc lại đúng 16 PNG do Android ghi: số nhóm, tên/gợi ý/lý do tên, khung và biên cắt/canvas của toàn bộ 120 nhóm đều khớp. Có 111 tên tự nhận, 9 tên chưa rõ; khung tự đọc gồm 85 có và 35 không. Không coi 111 tên là độ chính xác đã được người dùng xác nhận. Đối chiếu số lượng phù hợp Bộ Sưu Tập, chưa phải kiểm tra thủ công một-một toàn bộ danh tính của 120 nhóm mới.

Thời gian tới khi lưu JSON chính là 184,7 giây ở lượt này (bao gồm về đầu từ cuối danh sách); tạo danh sách ảnh xác nhận còn tốn thêm một lượt so tên. Đã sửa dùng lại điểm tên vừa tính để bỏ phép so lặp đó. Kết quả/lựa chọn tay trước và sau vẫn có mã kiểm tra trong `live-120/session.json`; 10 lựa chọn tay trong ứng dụng được giữ nguyên. Bằng chứng so sánh: `live-120/python-comparison.json`. Bản thử dùng mốc sai trước đó vẫn giữ nguyên JSON cũ và lựa chọn tay theo mã nội dung.

Đọc lại một phiên đã kéo về máy:

```bash
.venv/bin/python android/vision/doi_chieu_phien_android.py debug/android-v2-20261109/live-120
```

Bản APK cuối đã bỏ lượt so tên lặp và chạy lại kiểm tra v2 thành công. Đã cài đè bản cuối lên Tab S7; dữ liệu phiên 120 tướng và lựa chọn tay vẫn giữ nguyên. Kết quả tổng hợp và mã APK nằm trong `debug/android-v2-20261109/summary.json`/`build.json`.

Đã sửa bảng ảnh để ưu tiên ảnh thẻ mới vừa đọc. Xác nhận kiểu cũ không có mã mẫu được giữ lại nhưng không che ảnh mới hoặc tạo dấu xác nhận nhầm cho ảnh mới.

Cập nhật 9 tên trên bản 1.15: xem [kết quả xác nhận tên](chin-the-chua-ro.md). Bộ mẫu mới có 133 ảnh mặt/125 tên; đọc lại đúng 120 thẻ nhận đủ tên, giữ 111 tên cũ, toàn bộ khung và biên.

Cập nhật 1.17: thêm mẫu cho SS, Gunnar, Gwyneth và nhóm sát ngưỡng; 146 ảnh mặt/125 tên. Đối chiếu 90 thẻ khung, 48 ảnh gốc, 360 kết quả danh sách của ba lượt cùng tài khoản đều khớp Python trên JVM và Tab S7. Chi tiết và bằng chứng tại [báo cáo bổ sung tên](chin-the-chua-ro.md).
