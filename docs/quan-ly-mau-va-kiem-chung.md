# Quản lý mẫu và kiểm chứng độc lập — 08/11/2026

Cập nhật 10/11: bản đang dùng là Android 1.18 / Python `v-647cbc8e579f3e3d`, 146 mẫu mặt/125 tên. Đã tách hồ sơ tài khoản, bổ sung thu hồi mẫu và khôi phục qua cập nhật bộ mẫu; xem [kết quả 1.18 và phần còn thiếu](ho-so-va-mau-android.md). Các mốc 1.14, 167 mẫu/123 tên và ghi chú “chưa chuyển Android” bên dưới thuộc lịch sử triển khai.

Python đã kích hoạt bản v2 sau vòng kiểm tra mới **40 đúng, 0 sai, 0 chưa rõ / 40 thẻ** do người dùng gán nhãn. Đã đối chiếu đủ 121/121 tướng trên tài khoản kiểm tra. Kết quả vòng v1 **45 đúng, 1 sai, 4 chưa rõ / 50 nhóm thẻ** được giữ nguyên để tra cứu. Cả hai vòng dùng tài khoản thứ hai trên cùng Tab S7.

## Kho mẫu đang dùng

- Kho: `thu_thap_tuong/kho_mau/`.
- Hiện có 167 mẫu được duyệt: **124 mẫu mặt/tên** và **43 mẫu khung**. Lượt mới thêm 22 mẫu diện mạo được đọc tên trực tiếp, giữ các mẫu cũ.
- Mô hình khung vẫn chỉ học **29 mẫu thuộc 29 tướng**; **14 mẫu giữ lại** ở vai trò validation. Không đưa 50 ảnh kiểm tra độc lập vào mẫu học.
- Thư viện tên sau chuyển đổi vẫn có **123 tên** gồm thư viện nền và mẫu cá nhân. Chuyển phiên bản không làm đổi trọng số mô hình đã kiểm chứng.
- Trạng thái bản hiện hành: xem `quan_ly_mau.py current`. Mỗi bản có `manifest.json`, `dataset.json`, `faces.npz`, `model.npz`, mã kiểm tra nội dung và bằng chứng đánh giá.

`blobs/` lưu PNG theo mã nội dung; `revisions/` lưu trạng thái duyệt bất biến. `HEAD.json` trỏ tới dữ liệu đang biên tập; `current.json` trỏ tới bản đang chạy. Sửa dữ liệu duyệt không tự đổi bản đang chạy. Kích hoạt/khôi phục chỉ đổi con trỏ sau khi kiểm tra đủ tệp. Bản hỏng bị từ chối, không âm thầm quay sang đọc mẫu không được quản lý.

Các trạng thái mẫu: `pending`, `approved`, `rejected`. Vai trò: `train`, `validation`, `test`. Nhãn đoán của máy không được tự duyệt. Cùng ảnh mang nhãn khác phải được đối chiếu trước. Mẫu trùng được nhận ra theo pixel, giữ bổ sung nguồn thay vì thêm bản sao. Mẫu bị loại không tự quay lại từ thư mục mặt cũ hoặc ngân hàng mặt tùy chọn.

## Thao tác quản lý

```bash
.venv/bin/python quan_ly_mau.py current
.venv/bin/python xuat_kho_mau.py --ra debug/quan-ly-mau-20261108/kho_mau.html
```

Bảng HTML cho xem ảnh, nguồn, trạng thái và phiên bản. Có thể chọn trạng thái/lý do rồi xuất yêu cầu duyệt. Bảng chỉ xuất JSON; áp dụng bằng:

```bash
.venv/bin/python quan_ly_mau.py apply-review --file debug/yeu_cau_duyet.json
```

Yêu cầu gắn với revision, bị từ chối nếu dữ liệu đã đổi; kiểm tra cả lô trước khi ghi. Không để một nửa lô được lưu khi mẫu sau không hợp lệ. Có thể duyệt một mẫu bằng `review ID approved|rejected|pending --reason "Lý do"`.

Thêm mẫu mới:

```bash
.venv/bin/python quan_ly_mau.py add --image ANH.png --kind face --label TEN --source NGUON.json
.venv/bin/python quan_ly_mau.py add --image THE.png --kind frame --label 0 --source NGUON.json --quality CHAT_LUONG.json
```

Nguồn cần ít nhất `session`, `label_source`. Nhãn tin cậy dùng `user_confirmed` hoặc `on_screen_name`; nhãn suy đoán để `model_guess` và không tự duyệt. Với mẫu khung, ghi thêm `hero_id`, `group`, `source_sha256` của ảnh nguồn; chất lượng cần ảnh đã xác minh biên và `bien_chuan`. Chọn `--role validation|test` khi giữ riêng cho đánh giá. Mẫu mới mặc định chờ duyệt.

`nhap_ten_tuong.py` và `doc_tuong_cua_toi.py --xac-nhan` đưa mẫu tên mới vào hàng chờ khi dùng kho quản lý. Tên người dùng vẫn được lưu vào báo cáo, nhưng mẫu mới chưa tự vào bộ nhận dạng đang chạy. Xác nhận tên không tự học khung. Nhãn khung cá nhân trong `khung_tay.json` tiếp tục được ưu tiên khi so khung; đây là dữ liệu tài khoản, tách khỏi mẫu học.

Khi cần học mô hình khung ứng viên:

```bash
.venv/bin/python quan_ly_mau.py train --output debug/mau_ung_vien.npz
.venv/bin/python quan_ly_mau.py publish --model debug/mau_ung_vien.npz --training-ids debug/mau_ung_vien.training.json
```

Chỉ mẫu đã duyệt ở vai trò train được học; mỗi nhóm lấy một ảnh để không coi nhiều ảnh cùng tướng là nhiều mẫu độc lập. Bộ giữ lại và nguồn ảnh đã bảo vệ bị chặn **trước khi học**, đồng thời được kiểm tra lại khi phát hành. Sidecar ghi revision và đúng ID mẫu đã dùng; dữ liệu đổi sau học thì cần tạo lại ứng viên. Bằng chứng đánh giá có `model_sha256` phải khớp chính mô hình phát hành.

Nếu chỉ thay mẫu tên, có thể dùng lại `model.npz` của bản hiện hành và `training_ids.json`, không cần học lại mô hình khung. Mọi bản mới vẫn cần được kiểm tra trước khi kích hoạt:

```bash
.venv/bin/python quan_ly_mau.py activate MA_PHIEN_BAN
.venv/bin/python quan_ly_mau.py rollback
```

Đã kiểm tra chuyển bản và khôi phục thực tế với dữ liệu cá nhân, cùng kiểm thử lỗi ghi con trỏ/tệp bị sửa. Bản mới nhất ghi đầy đủ lỗi phát hiện trong phép kiểm chứng; có manifest hợp lệ không có nghĩa mô hình đạt độ chính xác tuyệt đối.

Khi kho đang kích hoạt, `ThuVien()` ưu tiên bản đó. `mau_khung_can=PATH` chọn mô hình riêng để thử nghiệm; `kho_mau=False` chỉ dùng khi cần kiểm thử chế độ cũ/tập tạm. Ngân hàng mặt ngoài chỉ bổ sung mẫu cá nhân đã thuộc bản được duyệt; `vien_them.npz` không được nạp ngoài phiên bản trong chế độ quản lý. Thư viện nền đóng gói vẫn giữ nguyên.

## Bộ kiểm chứng độc lập

Bộ `test-dfc2131ee610994a` ở `debug/kiem-chung-doc-lap-20261108/`:

1. Người dùng mở tài khoản khác trên cùng Tab S7.
2. Cố định mô hình, hàm phân loại/cắt ảnh và các mẫu nền trước khi chụp (`protocol.json`).
3. Thu 16 ảnh mới. Gom 121 nhóm ảnh mặt do bộ cắt đề xuất; chọn ngẫu nhiên 50 nhóm với seed cố định, không chọn theo dự đoán/nhãn.
4. Lưu ảnh, dự đoán và mã nội dung vào `seal.json` trước khi có nhãn.
5. Bảng gán nhãn không hiển thị dự đoán. Người dùng cung cấp đủ 50 nhãn: **35 có khung, 15 không khung**.
6. Chấm dự đoán đã niêm phong, không dùng `khung_tay.json`. Những lần thay nhãn được giữ trong `labels_history`; chấm lại cùng nhãn không tạo một lần sửa nhãn giả.

| Nhãn người dùng | Máy có khung | Máy không khung | Máy chưa rõ |
|---|---:|---:|---:|
| Có khung: 35 | 35 | 0 | 0 |
| Không khung: 15 | 1 | 10 | 4 |

- Đúng 45, sai 1, chưa rõ 4 trên 50 nhóm.
- Độ phủ kết luận: **46/50 = 92%**.
- Đúng trong các thẻ đã kết luận: **45/46 ≈ 97,8%**; tính trên toàn bộ 50 thẻ là **90%**. Không dùng 97,8% để diễn đạt độ chính xác trên mọi thẻ.
- Lỗi **#38**: người dùng xác nhận không khung, máy báo có khung. Mẫu sao khớp vùng tóc/mũ, điểm khoảng 0,809; mẫu viền chưa tách biệt nhưng nhánh sao vẫn kết luận dương tính. Ghi lỗi để phát triển tiếp bằng dữ liệu phát triển riêng, không sửa mô hình trên chính ảnh kiểm tra này.
- Các thẻ máy còn chưa rõ: **#37, #41, #45, #48**. Đây là số của bộ độc lập, khác số thẻ tài khoản phát triển.

Ảnh bộ kiểm tra được đăng ký bảo vệ theo mã pixel và mã tệp ảnh nguồn/dẫn xuất. Không nhập 50 nhãn này thành lựa chọn tay của tài khoản cũ, không thêm chúng vào mô hình đang học. Mã mô hình, protocol và bản nhãn tham chiếu được ghi vào kết quả; SHA ảnh/dự đoán bị đổi thì công cụ từ chối chấm.

Lệnh chấm lại/xuất báo cáo:

```bash
.venv/bin/python kiem_chung_doc_lap.py --folder debug/kiem-chung-doc-lap-20261108 score --nhan debug/kiem-chung-doc-lap-20261108/tra_loi_nguoi_dung.txt
.venv/bin/python xuat_ket_qua_doc_lap.py --folder debug/kiem-chung-doc-lap-20261108
```

Bộ mới dùng quy trình `freeze` trước chụp, sau đó `prepare` và nhận nhãn có dòng `BO_KIEM_TRA=...`. Không tái dùng số thẻ/bảng cũ cho bộ mới.

**Giới hạn:** bộ ảnh độc lập theo phiên/tài khoản so với đợt phát triển gần đây, vẫn cùng thiết bị. Các nhóm do ảnh mặt tự gom, chưa phải danh sách tướng chuẩn được gán thủ công từ đầu. Phép đo chỉ đánh giá khung trên các thẻ bộ cắt đề xuất, không đo khả năng tìm đủ toàn bộ danh sách, không đánh giá riêng độ chính xác tên, không chứng minh hỗ trợ máy khác.

Báo cáo trực quan: `debug/quan-ly-mau-20261108/kho_mau.html` và `debug/kiem-chung-doc-lap-20261108/ket_qua.html`.

## Kiểm tra triển khai

Bộ hồi quy đầy đủ: **129 kiểm thử qua**. Sau bổ sung nhánh CLI nhận sidecar phát hành, chạy lại **36 kiểm thử chuyên biệt qua**, gồm kiểm thử mới cho nhánh này. Tổng cộng 130 trường hợp liên quan đã được kiểm tra qua các lượt chạy. Đã kiểm tra thực tế trình duyệt: kho có 145 mẫu, lọc đúng 102 mặt/43 khung, bắt buộc lý do khi duyệt và xuất JSON đúng revision; báo cáo độc lập lọc đúng 45 đúng/1 sai/4 chưa rõ. Mã niêm phong, mô hình, nhãn tham chiếu và 43 lựa chọn tay tài khoản phát triển vẫn khớp sau kiểm thử.

## Tiếp phần 2, 3, 4, 5 — lượt v2 ngày 08/11/2026

- Quy tắc `v2` kết hợp mẫu viền đã học với màu sao xanh, góc viền vàng và cạnh thẻ. Một điểm khớp sao xám trên tóc/mũ không còn tự đủ để kết luận có khung. Bằng chứng mâu thuẫn tiếp tục trả về chưa rõ.
- Giữ nguyên 29 mẫu học và 14 mẫu validation. Bộ phát triển 43 thẻ: 43 đúng, 0 sai, 0 chưa rõ. Đọc lại bộ 50 thẻ đã biết nhãn: 50 đúng, 0 sai, 0 chưa rõ; bản v1 vẫn tái hiện đúng dự đoán đã niêm phong 45/1/4. Phép đọc lại 50 thẻ là hồi quy, không phải vòng độc lập mới.
- Bản v2 `v-6a0b286d3088d2f0` lưu cả `inference_policy` và mã nội dung quy tắc; đổi mã quy tắc làm bản đó bị từ chối. Bằng chứng của v1 không được đính vào bản v2. Khôi phục phiên bản được kiểm thử cả quy tắc lẫn mẫu. Sau khi nhận đủ nhãn, bản v2 đã được kích hoạt trên Python; bản trước là `v-3f19c612458d1683`.
- Chụp mới 16 ảnh trên tài khoản thứ hai, cùng Tab S7, sau khi cố định v2. Loại các nhóm khớp mặt với 50 nhóm cũ trước chọn ảnh, còn 71 nhóm; chọn ngẫu nhiên 40 nhóm trước dự đoán. Bộ `test-2d9de2fc4f0046c5` tại `debug/kiem-chung-v2-20261108/`. Đã nhận đủ nhãn người dùng: 35 có khung, 5 không khung; chấm dự đoán niêm phong đạt 40 đúng, 0 sai, 0 chưa rõ. Đây là vòng mới trên cùng tài khoản kiểm tra, không phải thêm thiết bị/tài khoản chưa từng thấy.
- Bảng `gan_nhan.html` vẫn ẩn dự đoán, có ảnh căn và ảnh nguồn. Đã kiểm tra 40 thẻ, 80 ảnh không hỏng, xuất đúng mã bộ và nhãn đã chọn. Mã pixel/ảnh gốc/ảnh cắt của vòng mới được bảo vệ khỏi tập học.
- Chấm dự đoán cũ chỉ cần niêm phong dữ liệu và mô hình đúng; không yêu cầu mã hiện tại phải trùng mã đọc cũ. Chạy dự đoán mới vẫn kiểm tra mã trước khi thực hiện.

Nguồn đối chiếu độ phủ bổ sung là màn **Bộ Sưu Tập**, chụp riêng 15 ảnh. Kiểm tra trực quan 27 hàng thấy 131 ô, 10 ô xám chưa sở hữu, 121 tướng có màu. Các hàng/vùng ảnh, mã ảnh gốc và ảnh đối chiếu được lưu tại `debug/tiep-2345-20261108/bo_suu_tap/`. Không dùng viền trang trí trong Bộ Sưu Tập làm nhãn khung; nguồn này chỉ phục vụ kiểm tra danh sách tướng. Đối chiếu từng tướng được xuất riêng trong báo cáo độ phủ.

Kết quả đối chiếu đã chốt: **121/121 tướng một-một**, không thiếu nhóm, không gán trùng. Xem `debug/tiep-2345-20261108/do_phu.html`. Máy ghép sai 6 cặp chân dung; các cặp được kiểm tra riêng trước khi chốt. Đã đọc tên trong game cho các ô nguồn #32 Cyran, #117 Silvina, #120 Valka. Gợi ý tên từ thư viện không được dùng thay bằng chứng này (ví dụ mặt Silvina đổi diện mạo có thể bị gợi ý Isabella). Chưa thay mẫu tên bằng ảnh kiểm tra.

Mã kiểm tra bổ sung ngăn việc coi hai danh sách bằng số lượng nhưng bị ghép trùng là đã thu đủ. Tổng cộng 138 trường hợp kiểm thử Python đã qua; gồm kiểm tra hiện có và các ca mới về phiên bản quy tắc, chấm dự đoán lịch sử, bằng chứng mâu thuẫn và đối chiếu nguồn.

### Chốt nhãn ngày 09/11/2026

Bộ `test-2d9de2fc4f0046c5`: **40/40 đúng**, gồm 35/35 có khung và 5/5 không khung, không nhận thừa/thiếu khung, không còn trường hợp chưa rõ. Xem `debug/kiem-chung-v2-20261108/ket_qua.html`. Không chỉnh quy tắc theo 40 nhãn này. Bản v2 đã kích hoạt; mẫu học vẫn 29, mẫu validation vẫn 14, kho vẫn 145 mẫu duyệt và thư viện 123 tên, nhãn cá nhân vẫn 43. Ảnh kiểm tra và Bộ Sưu Tập được giữ riêng khỏi học.

Dấu vân tay v2 kiểm tra cả mã quyết định, mã cắt/căn, mã tìm sao, đặc trưng, hàm dự đoán và nội dung mẫu sao/mốc trang. Ứng viên sơ bộ cũ được lưu để tra cứu nhưng không kích hoạt. Bản hiện hành có đầy đủ bằng chứng của vòng mới; dùng `quan_ly_mau.py rollback` để khôi phục bản Python trước khi cần. Phần Android chưa được chuyển trong lượt này.

## Bản tên v2 và danh sách ngắn — 09/11/2026

Bản đang dùng trên Python là `v-bdcac19891f8515a`, quy tắc khung v2 và tên v2. Đã thu đủ 48 tướng trên tài khoản người dùng cung cấp và 6 thẻ của danh sách lọc. Hàng chỉ có một thẻ tóc trắng được bổ sung bằng kiểm tra biên/góc/đáy và nhãn cấp; phần thu danh sách không cuộn yêu cầu số tham chiếu độc lập, ảnh đủ biên, không trùng và xác minh hai chiều. Trường hợp không cuộn hoàn toàn đã được kiểm tra bằng giả lập; máy thật đã thử danh sách 48 và lọc 6, đều có dịch chuyển.

Thêm 20 mẫu diện mạo phẩm thấp trên tài khoản cấp 241 và 2 mẫu chụp mới cấp 859. Đã đọc trực tiếp Isabella và Silvina trên chính hai chân dung cần đối chiếu; mẫu Silvina mới giải quyết trường hợp trước gợi ý Isabella. Mẫu chỉ học tên; mô hình khung vẫn 29 học/14 validation, 43 nhãn cá nhân giữ nguyên, thư viện vẫn 123 tên.

16 ảnh quan sát khác, không trùng hệt mẫu học, đều nhận đúng sau cập nhật. Đây là kiểm tra phát triển cùng tài khoản, không gọi là bộ độc lập mới. Các ảnh kiểm tra khung đã niêm phong được giữ riêng; chỉ dùng lại để kiểm tra hồi quy.

Chi tiết và cách sử dụng: [Danh sách ngắn và diện mạo](danh-sach-ngan-va-dien-mao.md). Báo cáo ảnh: `debug/danh-sach-ngan-dien-mao-20261109/bao_cao.html`. Kho hiện tại: `debug/danh-sach-ngan-dien-mao-20261109/kho_mau.html`.
