# Danh sách ngắn và tên theo diện mạo — Python, 09/11/2026

Cập nhật 10/11: bản đang dùng là Android 1.18 / Python `v-647cbc8e579f3e3d`, 146 mẫu mặt/125 tên. Đã thử thật danh sách 120/48 và lọc 6 thẻ; lọc 5 thẻ chưa xác minh được cuộn ngược nên giữ dữ liệu cũ. Xem [kết quả 1.18 và phần còn thiếu](ho-so-va-mau-android.md). Các mốc 1.14, 167 mẫu/123 tên và ghi chú “chưa chuyển Android” bên dưới thuộc lịch sử triển khai.

Đã thêm xác minh danh sách ngắn, sửa bỏ sót hàng chỉ có một thẻ tóc trắng và bổ sung 20 mẫu diện mạo đọc tên trực tiếp trên tài khoản 48 tướng, cùng 2 mẫu phẩm cao chụp mới trên tài khoản cấp 859. Báo cáo: `debug/danh-sach-ngan-dien-mao-20261109/bao_cao.html`.

## Xác minh danh sách ngắn

Hai ảnh đứng yên không tự đủ để kết luận đã đọc hết. Nhánh không cuộn chỉ chấp nhận khi có số tướng tham chiếu từ nguồn khác, thấy mốc đầu Hội Trường, đủ số thẻ và đủ biên, không đếm trùng, ảnh mặt giữ nguyên ở đầu/cuối và sau thử ngược chiều. Thiếu một điều kiện thì báo lỗi, giữ dữ liệu cũ. Nhánh này không cho bỏ kiểm tra hai chiều.

```bash
.venv/bin/python kiem_tra_hoi_truong.py --ra debug/phien-moi --so-tuong-du-kien 48
.venv/bin/python doc_tuong_cua_toi.py --thu-muc-ra debug/phien-moi --so-tuong-du-kien 48
```

Số tham chiếu là số tướng **duy nhất trong danh sách hiện tại**, kể cả nhóm cố định. Khi bỏ lọc trên tài khoản đang thử là 48. Khi lọc phe Thiên, nhóm cố định vẫn có 5 thẻ và lưới có thêm 1 thẻ: số tham chiếu là 6, không phải 1 hoặc 48. Không suy số tham chiếu từ chính bộ cắt đang cần kiểm tra. Sau gộp, kết quả khác số tham chiếu thì không xuất đè dữ liệu cũ.

Bằng chứng được lưu trong `xac_minh_phien.json`; lệnh thu phiên có thêm `phien.json` và ảnh gốc. Hai nhánh khác nhau: `cuon_nguoc_roi_quay_lai_anh_cuoi` cho danh sách có cuộn, `so_luong_nguon_va_hai_chieu_dung_yen` cho danh sách không cần cuộn.

Tài khoản 48 tướng đã thu 7 ảnh và gộp đúng 48 nhóm. Thanh nổi che tiêu đề từng làm bộ nhận màn báo sai khi về đầu; đã bổ sung cặp mốc `ht_dau` và `ht_nut_menu` để nhận Hội Trường.

## Hàng lưới một thẻ

Màn lọc thực tế có 5 thẻ cố định và một thẻ tóc trắng. Bộ cũ không tìm được hàng vì điểm chữ Cấp thấp và mặt/tóc trắng tách phần thân khỏi góc khung. Bộ bổ sung chỉ xét khi đã có đủ 5 thẻ cố định nhưng chưa có thẻ lưới, ghép các mảnh trong từng ô và chỉ bổ sung khi còn đúng một ứng viên. Phải kiểm tra kích thước, khoảng trống quanh thẻ, hai góc trên, hai cạnh, đáy, nhãn cấp và chi tiết vùng mặt. Không tự tạo cả hàng 6 ô.

Đã đối chiếu sau sửa đủ 6 thẻ với nhóm 1–5 và 27 của phiên 48; ảnh căn giữ đủ biên/sao. Không thay hàm cắt đã niêm phong của hai bộ kiểm tra khung. Bản tên v2 chọn bộ cắt bổ sung khi đọc danh sách. Các ảnh cũ giữ nguyên kết quả cắt trong kiểm thử hồi quy.

Mốc triển khai hiện kiểm tra trên Tab S7, ảnh gốc 1600×2560. Ảnh thu nhỏ thiếu mốc không được tự suy thêm thẻ. Tài khoản chỉ có vài tướng và hoàn toàn không cuộn được chưa được cung cấp; nhánh đó được kiểm thử bằng chuỗi giả lập, còn phép thử máy thật đã có danh sách 48 và danh sách lọc 6.

## Nhiều diện mạo cho cùng một tên

Thêm mẫu mặt mới giữ các mẫu cũ. Mẫu có `appearance_id`, ảnh nguồn, vị trí thẻ, ảnh đọc tên và mã nội dung. Không học khung từ xác nhận tên. Những tên hiển thị dài/chính tả khác được ánh xạ tường minh vào tên thư viện đã dùng: `Smokey & Meerky` → `Smokey`, `Lily May` → `Lili May`.

Nhập các mẫu đã đọc tên trực tiếp:

```bash
.venv/bin/python nhap_dien_mao.py --manifest debug/phien-moi/dien_mao_da_doc_ten.json
```

Manifest có `session`, `items`; mỗi mục cần `ten`, `ten_doc_tren_man`, `dien_mao`, `source_image`, `source_position`, `source_sha256`, `evidence`, `evidence_sha256`. Công cụ tự cắt mặt từ đúng ảnh nguồn, yêu cầu thẻ đủ biên, kiểm tra xung đột cả lô và chặn nguồn/pixel thuộc bộ kiểm tra. Mẫu được tạo ở trạng thái chờ duyệt; duyệt, phát hành và kích hoạt mới áp dụng.

Nếu người dùng xác nhận từ báo cáo Python:

```bash
.venv/bin/python doc_tuong_cua_toi.py --thu-muc-ra debug/phien-moi --xac-nhan 18=Silvina --dien-mao pham-thap
```

Tên ảnh mẫu theo mã pixel nên hai diện mạo xác nhận cùng giây không ghi đè nhau. Trong kho quản lý, mẫu vẫn vào hàng chờ. Giữ nguyên nhãn khung và nguồn xác nhận trước đó.

Quy tắc tên v2 lưu `ten_chi_tiet` và lý do chưa rõ. Ảnh chưa đủ điểm không đẩy ứng viên đứng đầu thành gợi ý đơn; danh sách ba ứng viên chỉ để đối chiếu. Không hạ ngưỡng để ép nhận tên. Có phiên bản và mã kiểm tra riêng cho quy tắc tên/bộ đọc danh sách, cùng cơ chế khôi phục mẫu.

## Kết quả trên nguồn phát triển mới

20 tên được đọc trực tiếp: Koko, Phraesto, Smokey, Eironn, Sonja, Ludovic, Ulmus, Marilee, Thoran, Sinbad, Hugin, Silvina, Lili May, Damian, Valka, Lyca, Antandra, Lucca, Niru, Seth.

- Trước bổ sung: 1/20 tên được nhận, 19 chưa rõ; không có tên tự nhận sai trong nhóm 20 đã đọc trực tiếp.
- Sau bổ sung: nhận đúng 20/20 trên các thẻ cùng diện mạo được đối chiếu.
- Trên 16 ảnh quan sát khác có pixel khác mẫu học: trước 1 đúng, 15 chưa rõ; sau 16 đúng, 0 sai/chưa rõ. Loại 14 lượt ảnh trùng hệt mẫu học khỏi phép đo này.
- Máy gán tên trên toàn phiên từ 29 lên 48/48. Đây là độ phủ đầu ra; không coi là độ chính xác 48/48 vì chỉ 20 thẻ mới được đọc tên trực tiếp trong lượt này.
- Đây là kiểm tra phát triển cùng tài khoản, không phải bộ kiểm chứng độc lập mới.

Đã mở lại tài khoản cũ, chụp nguồn mới cấp 859 và đọc trực tiếp tên của cả hai chân dung: nhóm 68 là Isabella, nhóm 75 là Silvina. Bổ sung đúng hai mẫu mới giúp nhận Silvina với điểm 0,958 thay vì gợi ý Isabella; Isabella vẫn nhận đúng. Đây là hồi quy trường hợp đã biết sau học tên từ phiên mới, không phải phép đo độc lập. Không dùng ảnh cũ đã niêm phong để thêm mẫu; hai mẫu bổ sung chỉ học tên, không học khung.

Mẫu khung vẫn giữ 29 học/14 validation. 43 nhãn khung cá nhân không đổi. Hai bộ kiểm tra khung 50 và 40 thẻ được giữ nguyên và tiếp tục được bảo vệ khỏi học. Android chưa chuyển các thay đổi này.

Kho sau bổ sung có 167 mẫu đã duyệt: 124 mẫu mặt và 43 mẫu khung. 22 mẫu mặt mới không làm tăng số tên duy nhất (vẫn 123), mà bổ sung các diện mạo của tên đã có. Phát hành không ghi đè bản trước; mặc định giữ cả quy tắc tên và quy tắc khung của bản đang dùng, tránh hạ phiên bản khung khi chỉ cập nhật tên.

Bản đã kích hoạt: `v-bdcac19891f8515a`, khôi phục về bản trước được bằng cơ chế kho mẫu. 164 kiểm thử Python đều qua sau khi kích hoạt. Đã kiểm tra lại 90 ảnh khung niêm phong theo v2, giữ nguyên kết quả; đây là hồi quy các bộ đã biết nhãn.
