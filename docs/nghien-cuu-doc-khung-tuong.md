# Nghiên cứu đọc khung tướng — 30/10/2026

Cập nhật Android 09/11: bản 1.14 đã chuyển quy tắc khung/tên v2 và quản lý mẫu. Xem [báo cáo Android](android-khung-v2.md) để biết phạm vi đối chiếu và kiểm tra trên thiết bị. Các ghi chú “chưa chuyển Android” bên dưới thuộc mốc lịch sử trước đó.

Tài liệu ghi tiến trình cải thiện từ 30/10/2026. Hiện Python đã có căn biên, kho mẫu phiên bản và một vòng kiểm chứng tài khoản khác. Các mục mới nhất nằm trước; số liệu cũ được giữ để đối chiếu. Những cải tiến Python mới chưa chuyển sang Android.

## Hoàn thiện quản lý mẫu và kiểm chứng tài khoản khác — 08/11/2026

Đã triển khai kho phiên bản `quan_ly_mau.py`, chuyển 102 mẫu tên và 43 nhãn khung đã xác nhận vào kho; giữ 29 mẫu học và 14 mẫu validation. Có duyệt/loại/chờ, phát hiện trùng/xung đột, xét lô nguyên tử, kiểm tra revision, bộ phát hành bất biến, kiểm tra mã tệp, kích hoạt và khôi phục. Đã kiểm tra khôi phục thực tế và giữ nguyên 123 tên/trọng số mô hình. Mẫu tên mới qua CLI được đưa vào hàng chờ; chế độ quản lý không nạp mẫu viền cá nhân ngoài phiên bản.

Đã thu 16 ảnh tài khoản khác do người dùng mở, cố định mô hình trước khi chụp, chọn ngẫu nhiên 50 nhóm ảnh mặt trước dự đoán và niêm phong cả ảnh/dự đoán. Người dùng gán đủ 35 có/15 không qua bảng ẩn dự đoán. Kết quả **45 đúng, 1 sai, 4 chưa rõ**. Lỗi #38 là không khung bị nhánh sao nhận có khung; không sửa mô hình bằng chính bộ kiểm tra. Nhãn kiểm tra không nhập vào lựa chọn tay của tài khoản phát triển, ảnh nguồn/dẫn xuất được bảo vệ khỏi học. Kết quả gắn SHA mô hình/protocol/phiên bản nhãn; có lưu lịch sử nhãn.

Vòng kiểm chứng này đã hoàn thành, nhưng chỉ cùng Tab S7, tài khoản khác, các nhóm do bộ cắt/gom đề xuất. Chưa là phép đo độ phủ toàn bộ danh sách, chưa đánh giá độc lập riêng nhận tên và chưa kiểm tra thiết bị khác. Phần đánh giá khung vẫn còn 1 lỗi/4 trường hợp chưa rõ để phát triển tiếp; bản phát hành ghi các giới hạn này.

Chi tiết thao tác, số liệu và giới hạn ở [quan-ly-mau-va-kiem-chung.md](quan-ly-mau-va-kiem-chung.md). Báo cáo `debug/quan-ly-mau-20261108/kho_mau.html` và `debug/kiem-chung-doc-lap-20261108/ket_qua.html`.

## Chụp bổ sung và cải thiện bộ đọc Python sau xác nhận

Đã thu thành công **16 ảnh mới** trên Tab S7 trong `debug/anh-moi-khung-20261107-b/`, sau khi kết nối lại game và ẩn bảng nổi che tiêu đề. Lần thu đầu dừng an toàn do bảng nổi che nhận màn, giữ ảnh lỗi riêng ở `debug/anh-moi-khung-20261107/`. Ảnh mới có cấp 828/831 và thêm mục Khế Ước Linh Hồn; không dùng ảnh cũ giả làm ảnh chụp bổ sung.

**Bước 2:** Carolina #86 (ảnh 12) và Vala #88 (ảnh 13) đều có ảnh mới ở giữa màn hình, đủ viền/vùng phía trên. Nguyên nhân thất bại tìm biên là viền tím nhạt sáng, độ bão hòa dưới ngưỡng chung. Bổ sung riêng miền hue tím có S>=25, không hạ ngưỡng cho nền kem. Trên 15 ảnh cũ, 279/280 lượt đạt hình học (trước 275/280); **117/117 thẻ** có ít nhất một ảnh đủ biên (trước 115/117).

Phiên mới còn phát hiện trang cuối toàn phẩm thấp không có chữ Cấp khớp mẫu: trước chỉ có 5 thẻ cố định. `hoi_truong._hang_tu_bien` dự phòng bằng các component có kích thước thẻ và cùng lưới cột, cần >=2 cột hỗ trợ hàng rồi khôi phục bước hàng. Trang cuối mới nay thấy **18 ứng viên = 5 cố định + 6 + 6 + 1**. Không suy ra khung từ số lượng/ID.

**Bước 4:** `khung_can_python.py` lấy 70 đặc trưng màu/cấu trúc từ hai góc trên, hai cạnh và dải sao của object đã căn, bỏ vùng mặt trung tâm. So trung bình 3 láng giềng mỗi lớp, chỉ kết luận nếu khoảng cách tách biệt theo tỷ lệ 0,6 và nằm trong bán kính mẫu cùng lớp. Bán kính lấy từ khoảng cách bỏ chính mẫu, nhân 1,5; đây là quy tắc thử nghiệm, không phải xác suất đúng. Mẫu xa/không tách biệt giữ chưa rõ. Nếu mẫu viền nghiêng về không khung nhưng điểm sao mạnh kèm màu xanh sao thì giữ chưa rõ. Không dùng tên, ID hoặc lựa chọn tay làm đầu vào dự đoán; ID láng giềng chỉ ghi để kiểm tra nguồn.

Chia trước theo **tướng**: 29 học (9 có/20 không), 14 giữ lại (4 có/10 không). Indris, Carolina và Vala thuộc tập phát triển vì đã dùng để chẩn đoán lỗi. Bản `chia_tap.json` cố định trước đo; SHA-256 mã và mô hình nằm trong `dong_bang_truoc_kiem_tra.json`. Đã kiểm tra chúng không đổi sau phép đo. Bỏ một mẫu trên tập phát triển: 17 đúng/0 sai/12 chưa rõ. Chỉ dùng 29 mẫu này cho mô hình mặc định, chưa thêm 14 tướng kiểm tra vào mẫu học.

| Tập đánh giá (đúng / sai / chưa rõ) | Bộ cũ | Bộ cải tiến |
|---|---:|---:|
| 14 tướng giữ lại, ảnh cũ | 0 / 0 / 14 | 9 / 0 / 5 |
| 14 tướng giữ lại, ảnh mới | 0 / 0 / 14 | **9 / 0 / 5** |
| 43 tướng đã có nhãn, ảnh mới | 0 / 2 / 41 | **36 / 0 / 7** |
| 81 lượt xuất hiện của 43 tướng, ảnh mới | 0 / 3 / 78 | 67 / 0 / 14 |

Phép đo gọi `danh_gia_khung`, **không dùng 43 lựa chọn tay**. Các tướng được liên kết với số thẻ gốc qua ảnh mặt (>=0,85, hơn ứng viên hai >=0,02); đã xem ảnh mới của đủ 43 tướng để đối chiếu tình trạng sao/viền không đổi. Nhãn khung do người dùng xác nhận ở ảnh cũ, chưa phải lượt xác nhận độc lập thứ hai trên ảnh mới. Tập 43 là các trường hợp từng khó/chưa rõ, không đại diện toàn bộ tướng; ảnh mới vẫn cùng máy/tài khoản. Chưa kiểm tra máy khác.

7 tướng bộ đọc tự động vẫn chưa rõ: **#84 Reinier, #89 Lumont, #90 Soren, #97 Gerda, #108 Saida, #109 Berial, #110 Nara**. Nhãn tay đã xác nhận của chúng vẫn được ưu tiên trong `SoKhung`. Đã chặn nhận nhầm tóc ở Indris và trường hợp tương tự Atalanta trên ảnh mới.

Đọc lại toàn bộ 15 ảnh cũ bằng mô hình mới: **83 có, 26 không, 8 chưa rõ**, giữ 117 ID/tên; không có kết luận đã biết nào mâu thuẫn với báo cáo sau xác nhận. 8 thẻ chưa rõ tự động là 7 thẻ trên cộng Estrilda #114. Đây là kiểm tra nhất quán, không gọi 74 nhãn máy còn lại là nhãn chuẩn độc lập. Báo cáo có xác nhận người dùng **84/33/0** trước đó được giữ nguyên.

Mô hình mặc định Python ở `thu_thap_tuong/khung_can_python.npz`, thông tin học ở tệp JSON cùng tên. `ThuVien(mau_khung_can=PATH)` hỗ trợ mẫu riêng; chỉ sử dụng bộ này cho ảnh có chất lượng căn biên, giữ nhánh ảnh cũ không kèm chất lượng. **106/106 kiểm thử đạt**, gồm hồi quy Indris, sao thật Bonnie, viền nhạt Carolina/Vala, ảnh mất biên, đặc trưng không đổi khi thay vùng mặt trung tâm, mẫu ngoài miền và trang cuối mới. Báo cáo ảnh/số liệu: `debug/cai-thien-khung-20261107/bao_cao.html`. Mã/phân loại mới chỉ áp dụng Python.

## Đã nhập 43 xác nhận khung của người dùng — 07/11/2026

Người dùng đã trả lời đủ 42 thẻ chưa rõ và #95 Indris: **13 có khung, 30 không khung**. Lumont #89 được đính chính từ `?` thành **0 (không khung)**; Indris #95 cũng được xác nhận **0**, thay kết luận máy khớp nhầm tóc.

Báo cáo mới `debug/da-xac-nhan-khung-20261107/tuong_cua_toi.html` và JSON giữ nguyên 117 ID/tên, ảnh mặt/thẻ và bằng chứng tự đọc. Tổng hợp: **84 có khung, 33 không khung, 0 chưa rõ**. Trong đó chỉ **43 nhãn khung được người dùng xác nhận**; 74 nhãn còn lại vẫn là kết quả máy, không gọi toàn bộ 117 là đã kiểm chứng.

- `khung_da_xac_nhan.json` ghi từng số thẻ, tên, nguồn nhãn người dùng, SHA-256 báo cáo/ảnh và thời điểm nhập. `khung_tu_doc` giữ kết luận cũ; `khung_nguoi_dung` lưu xác nhận tách khỏi điểm sao. Báo cáo HTML ưu tiên hiển thị xác nhận này.
- `thu_thap_tuong/khung_tay.json` lưu 43 nhãn theo tên; Python `SoKhung` dùng chúng ưu tiên khi so khung. Không thêm mẫu vào bộ phân loại sao/viền trong bước nhập nhãn.
- `nhap_khung_tuong.py` đối chiếu hash phiên, số thẻ, tên ghi chú và ảnh trước khi ghi; từ chối số trùng, tên lệch hoặc thẻ ngoài bảng. `?` giữ `null`, không chuyển thành 0 hoặc -1. Bộ nhập hỗ trợ bổ sung từng nhóm trong cùng phiên.
- **22 kiểm thử nhập/lưu/đánh giá khung đạt**. Kiểm tra thực tế xác nhận 117 tên và nhãn tên cũ giữ nguyên, ảnh không đổi, Lumont/Indris đều bằng 0, và 43 lựa chọn tay đã được Python đọc.

## Kiểm tra bằng mắt và bảng xác nhận — 07/11/2026

Đã xem 117 cặp ảnh trước/sau và ngữ cảnh ảnh nguồn; phóng to riêng 26 thẻ đổi kết luận. Các chóp trang trí bị nghi cắt ở lần xem tổng quan vẫn nằm trong ảnh khi phóng to. 115 ảnh được máy chấp nhận căn có sao/viền của chính thẻ nằm trong ảnh theo quan sát; một số ảnh có vệt bóng mờ hàng trên gần chóp. Kiểm tra vùng đệm đồng nhất bên ngoài object trước đây không tự chứng minh toàn bộ vùng bên trong không còn bóng hàng kế bên.

- **13/42 thẻ chưa rõ vẫn thấy sao khung**: #11, #27, #38, #40, #52, #60, #65, #66, #71, #72, #74, #83, #84. Đây chủ yếu là giới hạn bộ khớp mẫu/ngưỡng sau chuẩn hóa, không phải sao bị cắt mất.
- **29/42 thẻ chưa rõ không thấy hàng sao khung**, cần người dùng xác nhận có/không trước khi dùng làm nhãn. Scarlita #112 có ngôi sao trên đầu nhân vật, phải phân biệt với sao khung.
- **#95 Indris nghi nhận sai**: máy báo có khung với điểm sao khoảng 0,757; kiểm tra vị trí các đỉnh khớp thấy chúng nằm trên tóc trắng. Đã thêm ngoài 42 thẻ chưa rõ vào bảng xác nhận. Chưa sửa nhãn máy hoặc tự coi quan sát của trợ lý là nhãn người dùng.
- **#86 Carolina, #88 Vala**: ảnh nguồn có thân thẻ và viền tím nhạt xem được. Máy thất bại tìm biên là lỗi thuật toán; chưa thấy cần chụp lại chỉ vì cờ lỗi này. Ảnh sau của hai thẻ vẫn là ảnh tạm, chưa xác minh căn biên.
- 26 thay đổi chia thành: 4 thẻ chuyển sang có khung và nhìn thấy sao; 1 nghi nhận nhầm (#95); 7 chuyển về chưa rõ dù thấy sao; 14 chuyển về chưa rõ không thấy sao.

`docs/kiem-tra-bang-mat-khung-20261107.json` ghi nhận xét theo từng ID và SHA-256 báo cáo nguồn. Công cụ `tao_bang_xac_nhan_khung.py` kiểm tra nguồn không đổi rồi xuất bảng `debug/kiem-tra-khung-20261107/xac_nhan_khung.html`, biên bản `ket_qua_kiem_tra.md`, JSON và mẫu trả lời. Bảng có 43 ô xác nhận trống (42 + Indris), bộ lọc, ảnh nguồn phóng to, xuất câu trả lời TXT/JSON; nhãn chỉ lấy từ thao tác chọn của người dùng. Bộ tên, mẫu khung và kết quả máy cũ được giữ nguyên trong đợt kiểm tra này.

## Căn biên thực tế và đọc lại 15 ảnh gốc

Đã sửa Python để không dùng tâm cột suy ra làm biên cuối cùng. `can_khung_tuong.py` tìm miền có biên trong vùng ứng viên, tách ở khe ngang/dọc khi trang trí vàng của các thẻ chạm nhau, loại biểu tượng nâng cấp khỏi việc tìm biên, kiểm tra vị trí trong vùng không bị che và hỗ trợ của hai cạnh. Ảnh giữ nguyên tỷ lệ, đặt giữa canvas 130×205; ngoài object là nền đồng nhất, không lấy hàng bên cạnh.

- `cat_the_hoi_truong(..., kem_chat_luong=True)` giữ ứng viên lỗi để theo dõi danh tính nhưng gắn `day_du=False`. `can_bien=False` chỉ để đối chiếu ảnh nhận tên/các phép thử cũ. Chế độ mặc định chỉ trả ảnh căn biên đạt điều kiện.
- Bộ đọc khung từ chối ảnh không xác minh được đủ biên/sao. Ảnh mặt dùng nhận tên bám tham chiếu cũ và được lưu riêng trong JSON (`mat`), còn `anh` là thẻ căn biên để đọc khung. Không đổi 117 mã/tên hoặc 97 tên người dùng đã cung cấp.
- Việc chuẩn hóa toàn khung làm đổi kích thước sao. Đã so mẫu sao ở nhiều tỷ lệ, đồng thời kiểm tra hàng sao hoặc mức khớp đơn mạnh để tránh cực đại giả trên tóc/mũ (có kiểm thử Nara/Gerda). Không dùng phiếu viền dương của mô hình cũ để khẳng định có khung trên ảnh căn nếu bằng chứng sao yếu. Trường hợp sao lưng chừng cũng không lấy bỏ phiếu viền âm làm kết luận không khung.
- Đây là kiểm tra hình học/ảnh theo quy tắc, không phải chứng nhận tuyệt đối mọi sao hoặc góc trang trí đều được nhận đúng. Mẫu viền và ngưỡng vẫn cần đánh giá trên bộ nhãn khung độc lập; việc tăng số chưa rõ là chủ động giữ kết quả thiếu bằng chứng.

Kết quả chạy lại `01.png` đến `15.png`:

| Chỉ số | Kết quả |
|---|---:|
| Thẻ giữ nguyên số/tên | 117 |
| Lượt xuất hiện liên kết được với thẻ tham chiếu | 280/280 |
| Lượt đủ điều kiện hình học | 275 |
| Lượt biên bị cắt/che hoặc chưa tìm được | 5 |
| Thẻ có ít nhất một lượt đủ biên | 115/117 |
| Chưa có ảnh đủ biên | #86 Carolina, #88 Vala |
| Kết luận cũ: có / không / chưa rõ | 74 / 17 / 26 |
| Kết luận mới: có / không / chưa rõ | **72 / 3 / 42** |
| Thẻ đổi kết luận | 26 |

Báo cáo mới nằm riêng ở `debug/can-lai-khung-20261030/`: `so_sanh.html` xem ảnh trước/sau, `truoc_sau.json` kiểm tra từng thay đổi và `nguon/` xem biên đánh dấu trên ảnh đầy đủ. Những thẻ không tìm được biên vẫn có ảnh tạm để giữ số/đối chiếu, nhưng không dùng ảnh đó để kết luận khung. Ảnh gốc, bộ tên và báo cáo tham chiếu trước đó được giữ nguyên.

Lệnh tái hiện bằng `doc_lai_khung_tuong.py` có trong README. **94/94 kiểm thử Python qua**; kiểm tra bổ sung xác nhận 117 tên và 97 nhãn người dùng giữ nguyên, 115 ảnh chọn đạt biên có vùng đệm sạch không lẫn hàng kế tiếp. Chưa chuyển thay đổi căn biên sang Android.

## Nhập 97 tên do người dùng cung cấp

- Nhập đủ 97 tên theo snapshot `ad79fa881c4bf56c`; không thiếu/trùng số thẻ, 97 tên khác nhau. Giữ nguyên cách viết của người dùng, gồm `Lili May`, `Salazer` và các tên mới.
- `nhap_ten_tuong.py` kiểm tra mã snapshot, danh sách ID và toàn bộ ảnh trước khi ghi mẫu. Lưu nguồn nhãn người dùng, mã thẻ, mã phiên và SHA-256 ảnh trong `ten_da_xac_nhan.json`. Chỉ bổ sung mẫu mặt; không suy ra khung từ tên. Tên sửa lại của cùng thẻ/phiên không để mẫu nhãn cũ cùng tồn tại.
- Chạy lại trên ảnh tham chiếu: **97/97 khớp**, không có xung đột. 20 tên đã tự nhận trước đó giữ nguyên. Báo cáo có tên cho **117/117 thẻ**, trong đó 97 được người dùng xác nhận; không gọi toàn bộ 117 là nhãn đã được người dùng xác nhận.
- Kiểm tra ảnh khác: loại ảnh mặt trùng hoàn toàn với mọi mẫu học và loại ảnh lặp; chỉ gắn nhãn tham chiếu khi tương đồng >=0,85 và hơn ứng viên thứ hai >=0,04. **83/83 lượt ảnh khác cùng phiên** đủ điều kiện đối chiếu khớp tên; 96 lượt không gắn chắc được với một trong 97 nhãn tham chiếu được bỏ qua. Việc liên kết nhãn dựa tương đồng ảnh nên đây là kiểm tra nhất quán, chưa phải benchmark gán nhãn độc lập.
- Thư viện Python sau nhập có 123 tên (bao gồm các tên thư viện cũ không nằm trong 117 thẻ của phiên này). Dữ liệu gốc và bảng ảnh yêu cầu nhập vẫn được giữ nguyên để đối chiếu số thẻ.
- Bảng ảnh có tên: `debug/da-bo-sung-ten-20261030/ten_da_doi_chieu.html`; báo cáo đầy đủ `tuong_cua_toi.html`, bằng chứng số liệu `doi_chieu.json` cùng thư mục.
- Thêm 6 kiểm thử nhập nhãn và kiểm tra 54 trường hợp liên quan đều qua; đã cố định thư viện nền cho kiểm thử gợi ý tỷ lệ để việc thêm mẫu cá nhân không làm thay đổi giả định của phép thử đó.

## Triển khai phần 1 và 2 — có kiểm tra máy thật

### Mẫu tên bổ sung

- Từ 2.100 lượt mặt thuộc 40 nhóm đã đặt tên trong dữ liệu cũ, chọn 94 mẫu theo độ đa dạng, tối đa 6 mỗi nhóm, loại mẫu gần trùng. Tên nhóm do người đặt; thành viên nhóm do thuật toán gom ảnh nên vẫn có giới hạn về độ tin cậy nhãn.
- Đã mở chi tiết bốn tướng trên Tab S7, đọc trực tiếp tên hiển thị **Estrilda, Karma, Hammie, Chippy**, đối chiếu chân dung với bốn thẻ cuối danh sách. Lưu ảnh mặt và bằng chứng tên trong `tests/fixtures/tuong_da_xac_nhan/`; ảnh chi tiết đầy đủ và manifest trong `debug/xac-nhan-ten-truc-tiep/`. Không dùng tên suy đoán để xác nhận.
- `bo_sung_mau_tuong.py` tạo ngân hàng NPZ có nguồn cho từng mẫu. Ngân hàng hiện có 99 ảnh/32 tên: 94 chọn từ nhóm và 5 mẫu xác nhận (gồm Damian trước đây). `ThuVien` nạp bằng `--thu-vien-mat`, loại ảnh trùng chính xác với thư viện đang có. Chưa thay thư viện Android.
- Trên ba ảnh mẫu cũ, thêm ngân hàng giúp tên tự nhận 4→5 (Silven). Trên phiên máy thật 15 ảnh: bộ cũ nhận 13 tên; bổ sung nhóm nhận 16; thêm bốn mẫu xác nhận trực tiếp nhận **20 tên**. Kết quả 20 có dùng mẫu học từ chính phiên chụp, không phải độ chính xác trên tập độc lập. Thư viện vẫn chưa đủ tên/mẫu cho phần lớn thẻ còn lại.

Kiểm chứng sau các thay đổi: **82/82 kiểm thử Python qua**, gồm hồi quy nhận màn, ảnh hàng cuối, chồng lấp không tính nhóm cố định, kiểm tra cuộn ngược, mẫu bổ sung và bốn tên có ảnh chữ làm bằng chứng. `git diff --check` sạch.

### Cuộn và độ phủ trên Tab S7

- Phát hiện một lỗi nhận màn thực tế: Chế Độ Chiến Đấu có cả nút Hội Trường và mũi tên quay lại, nên nhánh nhận màn chỉ dựa hai biểu tượng này bị nhầm. Đã bỏ nhánh đó trong Python; dùng tiêu đề Hội Trường hoặc cặp Di Vật/Trang Bị. Có ảnh âm tính `samples/tab_s7_che_do_chien_dau.png` và kiểm thử hồi quy.
- Phát hiện thêm lỗi thẻ phẩm thấp: bộ lọc bão hòa của mép trên loại nhiều thẻ không sao. Nay dùng độ biến thiên vùng mặt và lưới hàng từ nhãn Cấp, không bắt từng hàng phải có nhãn khớp. Loại hàng bị nhóm 5 thẻ/tiêu đề che. Ảnh hàng cuối thật đọc được **21 thẻ đầy đủ** (5 thẻ cố định + 16 thẻ lưới), thay vì 12 trước sửa.
- Lượt vuốt dài thu 9 ảnh nhưng có nhiều cặp lưới không chồng lấp. Đổi sang bước 300 px chuẩn trong 1.000 ms, thay vì 600 px trong 700 ms; giữ vuốt về đầu nhanh hơn.
- Lượt cuối thu **15 ảnh**: mọi cặp ảnh liên tiếp có lưới đều có **5–11 thẻ lưới chung**. Cặp đầu từ cảnh đầu 5 thẻ sang trang có lưới được ghi không áp dụng. Đã bỏ nhóm 5 thẻ cố định khỏi phép kiểm tra để tránh chồng lấp giả.
- Ở cuối, đã cuộn ngược để thấy nội dung thay đổi rồi cuộn xuôi quay lại ảnh cuối. Bộ đọc nay từ chối phiên khi thao tác ngược không phản hồi, không trở lại được ảnh cuối hoặc lưới không nối tiếp. Đây là bằng chứng tốt hơn ảnh đứng yên đơn thuần, nhưng chưa chứng minh tuyệt đối không bỏ sót từng ô trên mọi tài khoản.
- Phiên chuẩn: `debug/hoi-truong-buoc-nho-20261030/`, gồm ảnh gốc, báo cáo HTML, `phien.json`, `do_phu.json`, `tong_ket.json`. Sau gộp có **117 thẻ và 20 tên được gán**, không khẳng định 117 tướng duy nhất vì việc gộp còn dựa tương đồng ảnh mặt.
- Script tái hiện: `kiem_tra_hoi_truong.py --serial SERIAL --ra THU_MUC_MOI --thu-vien-mat debug/mau-bo-sung-python.npz`. Chỉ điều hướng/cuộn, không nâng phẩm, đổi trang bị hay đánh trận. Đã trở lại Hội Trường sau bước đọc tên chi tiết.

## Đối chiếu ứng viên tên — Python

Thử nghiệm tìm ảnh mặt ở các tỷ lệ 0,90/0,95/1/1,05/1,10 cho thấy Eironn tăng từ 0,690 lên 0,802 và Faramor từ 0,742 lên 0,848. Các điểm vẫn dưới ngưỡng tự nhận 0,85; một số thẻ khác đổi ứng viên đứng đầu sau biến đổi. Do đó chưa dùng điểm thử để tự gán tên.

Đã triển khai:

- `--goi-y-da-ty-le`: xếp tối đa 3 ứng viên tham khảo cho thẻ chưa có tên, lưu tên, điểm gốc, điểm thử tốt nhất và tỷ lệ tương ứng trong `ung_vien_ten` của JSON. Mỗi tên chỉ xuất hiện một lần trong danh sách này.
- Giữ độc lập tên tự nhận với ứng viên tham khảo. Kể cả điểm thử rất cao, tên không được tự gán lại chỉ vì thử nhiều tỷ lệ. Tên đã nhận không tính lại gợi ý nhiều tỷ lệ.
- Báo cáo HTML có khu vực xác nhận cho cả 18 thẻ chưa nhận tên (trước chỉ hiện nhóm vượt ngưỡng gợi ý). Mỗi thẻ có số thứ tự ổn định, tối đa 3 ảnh mặt mẫu phù hợp nhất ở tỷ lệ đã thử và điểm để đối chiếu. Tướng có thể chưa có trong thư viện; ảnh tham khảo không phải nhãn xác thực.
- `--thu-muc-ra`: xuất JSON/HTML/ảnh riêng để thử nghiệm; dùng cùng `--xac-nhan SO=TEN` để đọc lại báo cáo riêng khi xác nhận. Việc xác nhận vẫn bổ sung mặt vào thư viện dùng chung, còn kết quả đọc được lưu trong thư mục đã chọn.

Báo cáo minh họa: `debug/kiem-tra-ten-python/tuong_cua_toi.html`. Có 22 thẻ, 4 tên tự nhận, 18 thẻ cần xác nhận; kết quả khung vẫn là 18 có khung và 4 chưa rõ. Chưa thêm tên tự nhận mới từ phép thử này. Cần thêm mẫu đã xác nhận và tập nhãn độc lập trước khi thay thuật toán tự nhận.

Lệnh tái hiện có trong README. Thêm kiểm thử điểm thử không tự gán tên, lưu cả điểm gốc, không tính lại thẻ đã nhận, hiển thị thẻ điểm thấp và xác nhận báo cáo xuất riêng. Bộ kiểm thử ảnh/khung cùng kiểm thử mới đã được kiểm tra; lượt hồi quy cuối có **44/44 qua**, gồm 5 kiểm thử mới (4 ứng viên tên, 1 xác nhận thư mục riêng), 5 kiểm thử lưu cũ và 34 kiểm thử nhận diện/leo ải. `git diff --check` sạch.

## Trạng thái khung chưa xác định — Python

Đã thêm `ThuVien.danh_gia_khung()` để dùng cho danh sách Hội Trường và kiểm tra khung của bản ghi khi so đội. `khung_tin()` cũ giữ nguyên cho bộ đội hình dự phòng và các đối chiếu thuật toán cũ.

- Ảnh sai kích thước/kiểu dữ liệu hoặc thiếu chi tiết trên toàn thẻ/vùng mặt: trả khung chưa rõ.
- Điểm sao >=0,75: nhận có khung. Khi điểm sao thấp hơn, cần ít nhất 6/7 mẫu viền đồng thuận; nếu sao dưới 0,62 nhưng viền nghiêng về có khung thì giữ chưa rõ.
- Khoảng cách mẫu gần nhất được lưu làm bằng chứng; chưa dùng ngưỡng loại theo khoảng cách vì chưa có tập kiểm chứng ngoài phân phối. Các ngưỡng chất lượng ảnh và 6/7 là quy tắc thử nghiệm, không phải độ tin đã hiệu chuẩn.
- Khi gộp quan sát, bỏ phiếu chưa rõ không tính thành 0. Các quan sát đã kết luận 0 và 1 mà mâu thuẫn nhau sẽ cho kết quả chưa rõ, thay vì lấy đa số che mất xung đột.
- JSON dùng `khung: null` và danh sách `khung_chi_tiet`. HTML/CLI ghi rõ chưa xác định; bộ so đội bỏ qua các khung chưa rõ, và vẫn dùng lựa chọn khung thủ công khi có.

Ba thẻ trên ảnh `cuon` (chỉ số 0-based 9, 13, 14 trong thứ tự cắt hiện tại) được kiểm tra bằng mắt có hàng sao, nhưng bộ cũ trả 0; bộ mới trả chưa rõ. Sau gộp ba ảnh: **22 thẻ = 18 có khung + 4 chưa rõ**, 4 tên được nhận. Đây là sửa cách xử lý thiếu chắc chắn; chưa chứng minh mọi thẻ còn lại được phân loại đúng trên các tài khoản khác.

Đã xuất báo cáo minh họa riêng ở `debug/kiem-tra-khung-python/tuong_cua_toi.html` và JSON cùng thư mục, không thay dữ liệu tài khoản trong `thu_thap_tuong/`. Tổng cộng **67 kiểm thử Python qua** (65 trường hợp trong lượt hồi quy chung, sau đó chạy lại nhóm lưu/đánh giá khung với 2 trường hợp mới và kiểm tra thêm CLI). Thêm 10 kiểm thử về ảnh lỗi, thẻ khung bị đọc sai trước đây, mẫu âm thực tế trong Thành Tích, tổng hợp quan sát, JSON/HTML, bỏ qua khung chưa rõ khi so đội và ưu tiên khung thủ công.

## Cập nhật triển khai tiếp theo — chỉ Python

Đã sửa bộ cắt `hoi_truong.py`:

- Nhận mốc `ht_dau` để dùng giới hạn đáy riêng cho màn đầu: lấy được đủ hàng 5 thẻ. Khi đã cuộn vẫn giữ giới hạn tránh thanh Di Vật/Trang Bị và nút lọc che thẻ.
- Thay điều kiện loại theo tỷ lệ nền kem bằng độ biến thiên vùng mặt, giữ được Frieren/Faramor tóc/lông trắng. Vẫn giữ kiểm tra độ bão hòa và độ biến thiên toàn thẻ để loại ô trống.
- Kiểm tra bằng mắt các dải ảnh cắt. Trên ba ảnh thật: `tren_cung` **0→5**, `dau` **8→10**, `cuon` **16→17** thẻ. Kiểm tra thu về rộng 800/1080, giữ nguyên tỷ lệ, đều giữ số thẻ 5/10/17. Chưa phải phép thử thiết bị khác tỷ lệ.

Đã sửa tổng hợp và nhận tên trong `doc_tuong_cua_toi.py`:

- Ghép với thẻ có mặt giống nhất vượt ngưỡng, thay vì thẻ đầu tiên vượt ngưỡng.
- Với Hội Trường, chọn ảnh mặt theo độ nét Laplacian trên vùng mặt chuẩn hóa; thay đồng thời mặt và ảnh thẻ để dữ liệu hiển thị/xác nhận cùng quan sát. Khung vẫn tổng hợp bằng đa số như cũ. Chỉ số độ nét là tiêu chí chọn ảnh tương đối, chưa được hiệu chuẩn để phát hiện mọi loại ảnh lỗi.
- Chỉ tự gán tên đứng đầu khi đạt 0,85 và hơn tên thứ hai ít nhất 0,04; không gán tên hạng hai chỉ vì tên đầu đã được dùng cho thẻ khác. Trường hợp nhập nhằng chỉ gợi ý. Ngưỡng chênh 0,04 là cấu hình thử nghiệm bảo thủ, cần đánh giá trên tập nhãn lớn hơn.
- Sau gộp ba ảnh: **22 thẻ, 4 có tên, 5 chỉ gợi ý** (trước là 20/3/6). Tên thứ tư là Frieren, được giữ lại sau sửa bộ lọc tóc trắng. Số tên tăng không tự chứng minh độ chính xác; thư viện vẫn thiếu nhiều tên/mẫu phù hợp.

Đã sửa thu chuỗi ảnh: lưu ảnh khi bắt đầu đọc và khi danh sách thực sự thay đổi, gồm trang cuối; không đưa các ảnh đứng yên lặp lại vào bỏ phiếu khung. Giới hạn cuộn có tham số `toi_da` để kiểm thử. Vẫn giữ cơ chế từ chối phiên cuộn không phản hồi; chưa tự nhận biết chắc chắn danh sách ngắn hoàn toàn không cần cuộn.

Kiểm thử: `test_doc_hoi_truong.py` có 11 trường hợp (gồm kiểm tra ảnh thu nhỏ); cùng 7 kiểm thử Hội Trường cũ và 5 kiểm thử lưu dữ liệu là **23 trường hợp**. Các chuỗi cuộn dùng ADB giả lập và ảnh tổng hợp, chưa chạy điều khiển máy thật. Kiểm tra hồi quy `test_nhan_dien`, `test_so_ai`, `test_leo_ai`: **34/34 qua**. Android chưa nhận những thay đổi cắt thẻ/chọn mặt/nhận tên của đợt này, vì đang thử nghiệm trên Python theo yêu cầu.

Các kết quả 0/8/16 và 20 thẻ ở phần dưới là mốc trước đợt cải thiện Python này.

## Luồng hiện tại

1. Android đọc riêng từ Hội Trường: mở từ nút trên bản đồ/Màn AFK, hoặc quay lại từ đội hình rồi tìm nút Hội Trường. Khi bắt đầu leo, không còn tự đọc danh sách đội hình; dùng dữ liệu đã lưu/lựa chọn tay. Python CLI mặc định dùng Hội Trường, `--doi-hinh` giữ bộ đọc cũ; hàm `doc()` khi gọi trực tiếp vẫn mặc định `hoi_truong=False`.
2. `catTheHoiTruong()` / `cat_the_hoi_truong()` tìm nhãn “Cấp” ở 5 tỷ lệ (0,95; 1; 1,15; 1,2; 1,25), gom hàng, suy ra nhóm 5 thẻ lớn hoặc lưới 6 cột theo tọa độ chuẩn. Lọc ô trống bằng độ biến thiên, độ bão hòa và tỷ lệ nền kem; chuẩn hóa về 130×205. Không dùng cách dò cột nền kem của bộ đọc đội hình.
3. `diemSao()` dùng OpenCV `TM_CCOEFF_NORMED`, so hai mẫu sao trên phần y=5..70. Điểm <0,62: không khung; >=0,75: có khung.
4. Vùng giữa hai ngưỡng: lấy đặc trưng bão hòa/độ sáng của mép trên và hai cạnh, chuẩn hóa 892 chiều, bỏ phiếu 7 mẫu gần nhất theo khoảng cách Euclid bình phương.
5. Nhận tên bằng ảnh mặt 48×48, cho phép dịch chuyển nhỏ; thẻ thường cần điểm >=0,85. Thẻ phủ xanh cần >=0,50 và hơn ứng viên thứ hai >=0,12. Thư viện hiện có 28 tên, 216 ảnh mặt và 600 mẫu viền (300 mỗi loại).
6. Gộp thẻ giữa các ảnh nếu mặt giống >=0,85; khung lấy đa số, hòa lấy lần có “độ tin” cao nhất. Luồng Hội Trường gán `trong_doi=False`, tránh loại tướng đang trong đội như bộ đọc cũ. Lựa chọn thủ công ưu tiên hơn tự đọc.

“Khung” hiện chỉ là nhãn nhị phân có/không, chưa đọc cấp phẩm cụ thể hay số sao.

## Thay đổi đã giải quyết và giới hạn còn lại

- Android đã chặn lưu khi danh sách rỗng, rời Hội Trường, không có dịch chuyển hoặc hết 60 lần cuộn chưa đạt điều kiện dừng. Nhận xét cũ “Android ghi đè bằng danh sách rỗng” không còn áp dụng.
- Dừng sau hai lần chênh lệch ảnh <2, yêu cầu đã có dịch chuyển; lúc về đầu có thêm mốc `ht_dau`. Đây là cải thiện so với một lần ảnh không đổi, nhưng chưa chứng minh đã thu đủ mọi thẻ.
- Bỏ việc đọc thẻ phủ xanh ở màn đội hình khỏi luồng mặc định. Các vấn đề nhận tên/khung và gộp quan sát vẫn dùng thuật toán cũ. Mẫu viền từ xác nhận nay chỉ được thêm khi có lựa chọn khung thủ công.
- Lỗi `acc2` bên dưới chỉ còn là bằng chứng của bộ đọc dự phòng `--doi-hinh`, không phải lỗi đã tái hiện trên Hội Trường.

## Mốc kiểm tra Hội Trường trước đợt cải thiện Python

Lệnh kiểm thử: `.venv/bin/python -m unittest test_hoi_truong -v` — **7/7 qua**. Bao gồm nhận màn, hai kiểu nút, tên/khung của Rolan–Mehira–Eryndor trên ảnh mẫu, không thêm thẻ khi lặp cùng ảnh, loại nền trắng và không bấm ở màn lạ. Bộ này chưa mô phỏng đầy đủ chuỗi cuộn và ghi dữ liệu.

Kiểm tra Android/JVM: `./gradlew :vision:test --offline` — **BUILD SUCCESSFUL**, các tác vụ báo `UP-TO-DATE` nên lần này không chạy lại thân test. Báo cáo XML hiện có ghi 10 test, 0 lỗi; đây là kết quả được Gradle tái sử dụng, không phải phép chạy mới trên thiết bị Android.

Sau triển khai: biên dịch `:app:compileDebugKotlin` **thành công** bằng JDK 17; `:vision:test` vẫn `UP-TO-DATE`. Lần chạy với JDK mặc định ban đầu thất bại do JDK 21 thiếu compiler, đã xử lý bằng chọn JDK 17 cho lệnh kiểm tra, không đổi cấu hình dự án.

Kiểm thử bổ sung `test_luu_khung.py`: **5/5 qua**, gồm đọc rỗng, lỗi ghi ảnh thứ hai, lỗi thay JSON, thành công với ảnh phiên riêng và điều kiện học viền qua CLI. Các test dùng thư mục tạm, không sửa dữ liệu tài khoản.

Đo trực tiếp bằng `cat_the_hoi_truong()` và `D.doc(..., hoi_truong=True)`:

| Ảnh Hội Trường | Thẻ tách | Sau gộp | Có tên | Chỉ gợi ý | Điểm sao giữa hai ngưỡng |
|---|---:|---:|---:|---:|---:|
| tren_cung | 0 | 0 | 0 | 0 | 0 |
| dau | 8 | 8 | 3 | 3 | 2 |
| cuon | 16 | 16 | 3 | 4 | 5 |

Gộp ba ảnh theo thứ tự trên: **20 thẻ, 3 có tên, 6 chỉ gợi ý**; 11 thẻ còn lại không được gán tên/gợi ý. Ba tên được gán là Rolan, Mehira, Eryndor, đều khung=1. Đây là độ phủ đầu ra trên các ảnh mẫu, không phải tỷ lệ chính xác hay tổng số tướng tài khoản. Cần phân tích riêng ảnh mặt khác mẫu, tên chưa có thư viện và crop sai trước khi kết luận nguyên nhân.

Ở mốc trước sửa, ảnh `tren_cung` nhìn thấy hàng 5 thẻ ở sát đáy nhưng bộ cắt trả 0. Ngưỡng loại thẻ gần thanh đáy có thể khiến chúng phải được đọc sau khi cuộn lên. Chưa đủ bằng chứng để kết luận mất 5 tướng trong cả phiên; cần kiểm tra từng thẻ xuất hiện trở lại và được thu nhận ở ảnh sau.

## Kiểm tra bộ đọc đội hình cũ (giữ để đối chiếu)

Chạy bản Python tương ứng thuật toán Kotlin trên bốn ảnh `samples/tab_s7_doi_hinh_*.png`:

| Ảnh | Thẻ tách được | Thẻ phủ xanh | Điểm sao nằm giữa hai ngưỡng | Thẻ được gán tên |
|---|---:|---:|---:|---:|
| acc2 | 0 | 0 | 0 | 0 |
| da_sao_chep | 13 | 5 | 2 | 7 |
| huyen_linh | 13 | 5 | 3 | 6 |
| man_afk | 13 | 5 | 2 | 6 |

Số tên được gán không phải số tên đúng: chưa có nhãn kiểm chứng độc lập cho từng thẻ trong phép đo này.

**Lỗi tách thẻ trên acc2:** xem ảnh xác nhận có hàng thẻ và hàng dưới phần lớn trống. Bộ dò cột chỉ trả về `(250,446)`, không đạt yêu cầu ít nhất ba cột, nên bỏ toàn bộ ảnh. Nguyên nhân trực tiếp là dùng tỷ lệ nền kem tính trên toàn chiều cao vùng danh sách: nhiều ô trống làm biến mất các cột có thẻ. Thử truyền vị trí bảy cột từ ảnh man_afk cũng chỉ lấy được hai thẻ; do đó không thể chỉ cố định cột rồi coi đã sửa xong, cần kiểm tra cả cách tìm hàng/cắt thẻ.

**Thử độ ổn định:** 24 lượt thẻ không phủ xanh từ ba ảnh còn lại (có thể trùng tướng/ảnh gần giống, không phải 24 mẫu độc lập):

- Thu chiều rộng thẻ 130 xuống 100, 80, 65 bằng INTER_AREA, rồi đưa về 130×205 bằng INTER_LINEAR: 0/24 đổi nhãn ở mỗi mức.
- GaussianBlur kernel 5×5, sigma 0,6; 1,0; 1,5: 0/24 đổi nhãn ở mỗi mức.
- Đây là kiểm tra độ ổn định so với đầu ra gốc, không chứng minh nhãn gốc đúng, không thay cho kiểm tra toàn màn hình trên điện thoại khác.

## Điểm cần cải thiện theo ưu tiên

### 1. Kiểm chứng độ phủ và hoàn tất phiên Hội Trường

- Gán nhãn các thẻ thấy được ở nhóm 5 thẻ lớn, lưới 6 cột, đoạn chuyển tiếp và hàng cuối chỉ còn 1–2 thẻ. Kiểm tra các thẻ bị loại ở `tren_cung` được thu lại sau khi cuộn.
- Hiện tâm cột vẫn cố định theo màn rộng 1600; vị trí hàng dựa nhãn Cấp nhưng chiều ngang chưa được suy ra từ các mốc thực tế. Cần ảnh máy khác tỷ lệ trước khi khẳng định hỗ trợ tốt.
- Điều kiện `moved=False` rồi hai ảnh không đổi sẽ từ chối danh sách ngắn thực sự không cần cuộn. Đây là rủi ro từ mã, chưa tái hiện bằng ảnh/thiết bị tài khoản ngắn; bổ sung phép thử phân biệt danh sách ngắn với thao tác cuộn thất bại.
- Hai ảnh đứng yên sau khi đã di chuyển có thể là cuối danh sách hoặc cuộn bị kẹt. Cần bổ sung dấu hiệu cuối danh sách/số thẻ mới; không coi sự đứng yên đơn thuần là chứng cứ đầy đủ.
- **Đã sửa bảo toàn dữ liệu:** Python từ chối lưu rỗng, kiểm tra ghi từng ảnh và thay JSON bằng `os.replace` sau khi flush/fsync. Android dùng thư mục ảnh phiên riêng và `AtomicFile` cho JSON. Cả hai giữ ảnh phiên cũ; lỗi trong bước ghi ảnh/JSON xóa phiên mới, giữ dữ liệu cũ. Các phiên cũ hiện chưa tự dọn; HTML Python là báo cáo phụ, được tạo sau khi lưu dữ liệu.
- Đã cập nhật log `napSoKhung()` và chú thích luồng đọc để hướng dẫn mở Hội Trường.

### 2. Có trạng thái chưa xác định và điểm chất lượng phù hợp

- `khungTin()` hiện luôn trả 0/1. “Độ tin” là `abs(diemSao - 0,685)`, kể cả khi nhãn do kNN quyết định. Một ảnh hỏng làm điểm sao thấp có thể được coi là rất chắc chắn không khung.
- Trả kết quả có cấu trúc: nhãn có/không/chưa xác định, điểm sao, số phiếu viền, khoảng cách mẫu gần nhất, chất lượng ảnh, lý do chưa xác định.
- Kiểm tra chất lượng ảnh trước khi dùng ngưỡng sao. Với kNN, xét đồng thời độ đồng thuận và khoảng cách; thử trọng số khoảng cách và so với bỏ phiếu đều trên tập kiểm chứng. Không diễn giải tỷ lệ phiếu là xác suất đã được hiệu chuẩn.
- Chỉ đánh dấu đội thiếu khung khi có bằng chứng đủ chắc ở cả hai phía. Trạng thái chưa rõ cần đi xuyên suốt lưu JSON, UI và `SoKhung`; không dùng -1 một cách tùy tiện vì -1 đang có nghĩa “chưa sở hữu”.

### 3. Tách xác nhận tên khỏi xác nhận khung — đã triển khai điều kiện học

- Android vẫn giữ định dạng `xac_nhan.json` để tương thích, nhưng `apDungXacNhan()` chỉ dùng lựa chọn khung 0/1 trong `khung_tay.json` để thêm viền, bỏ qua thẻ phủ xanh. Nhãn tự đoán trong thẻ xác nhận không còn được dùng làm nhãn học viền. Python `--xac-nhan` áp dụng cùng điều kiện.
- Đã bổ sung hướng dẫn trong UI/README và test CLI: chưa chọn khung hoặc “Chưa có” không tạo mẫu viền; khung tay 0 được học đúng dù dự đoán trên thẻ là 1.
- Thay đổi không xóa các mẫu viền đã học sai từ trước trong `vien_them.npz`, cũng không loại mẫu đã thêm vào bộ nhớ trước khi thay đổi lựa chọn. Cần quản lý nguồn mẫu/khả năng thay thế mẫu nếu bổ sung vòng đời học trong cùng phiên.
- Viền mới vẫn chỉ tham gia khi điểm sao nằm giữa hai ngưỡng; chưa sửa được trường hợp điểm sao đã rơi vào nhánh kết luận sai trực tiếp.

### 4. Nhận tên và tổng hợp nhiều lần thấy

- Thẻ thường cũng cần khoảng cách điểm giữa ứng viên hạng nhất và hạng hai; ngưỡng tuyệt đối 0,85 chưa mô tả độ nhập nhằng.
- Gộp thẻ theo mặt kết hợp cột/vị trí và độ dịch chuyển cuộn, tránh chỉ lấy thẻ đầu tiên vượt 0,85.
- Android `DocDanhSach.them()` vẫn thay ảnh thẻ khi lần mới chắc hơn nhưng giữ nguyên ảnh mặt từ lần đầu; ở luồng đội hình cũ còn giữ cả trạng thái phủ xanh. Nên chọn quan sát tốt nhất cho tên, khung và trạng thái che phủ theo tiêu chí riêng.
- Thêm mẫu đa dạng cho tướng/skin chưa có, chọn mẫu đại diện thay vì tối đa 12 ảnh đầu tiên. Chỉ cần gọi bước nhận tên một lần cho mỗi thẻ tốt, tái sử dụng điểm cho lưu ứng viên để giảm tính toán lặp.

## Lựa chọn thuật toán

| Hướng | Đánh giá cho dự án |
|---|---|
| Giữ OpenCV, sửa cắt thẻ, kiểm soát chất lượng, thêm trạng thái chưa rõ | Ưu tiên triển khai đầu tiên; tận dụng mã và dữ liệu hiện có |
| So sao ở vài tỷ lệ nhỏ, nhiều mẫu khung; phối hợp với viền | Đáng thử khi có lỗi scale/khung mảnh được gán nhãn; nhiều mẫu cũng có thể tăng khớp nhầm |
| kNN trọng số khoảng cách hoặc bộ phân loại nhỏ trên đặc trưng sao/viền | Thử offline, chọn theo kết quả kiểm chứng; không cần mang scikit-learn vào APK |
| Detector/CNN nhỏ cho thẻ và khung | Giai đoạn sau nếu layout/skin quá đa dạng và có đủ nhãn; chưa có bằng chứng cần thay toàn bộ pipeline |
| OCR | Có thể bổ sung nếu có màn chi tiết hiển thị phẩm bằng chữ; ảnh danh sách đang dùng chưa cung cấp trường đó rõ ràng |

## Đánh giá trước khi phát hành

1. Gán nhãn thủ công hộp thẻ, tên, khung, che phủ trên ảnh danh sách lẫn Thành Tích; ưu tiên Hội Trường với nhóm 5/lưới 6 cột, ít tướng, khung mảnh, ảnh đang cuộn, cuối danh sách và thiết bị khác tỷ lệ. Ảnh acc2 chỉ dùng kiểm thử bộ đọc đội hình dự phòng.
2. Tách tập phát triển/kiểm chứng theo phiên chụp hoặc thiết bị; các lần thấy cùng một thẻ và ảnh biến đổi của nó phải ở cùng tập để tránh rò rỉ.
3. Đo riêng: tỷ lệ phát hiện thẻ, tên đúng trên các thẻ tự nhận, nhầm có→không và không→có, tỷ lệ chưa rõ, số đội bị đánh dấu thiếu khung sai, thời gian và bộ nhớ trên Android.
4. Giữ bài kiểm tra Python–Kotlin để bảo đảm hai bản đồng nhất, bổ sung bộ nhãn người kiểm chứng. Kết quả hiện tại trong `PythonParityTest` lấy từ Python nên không tự chứng minh thuật toán đúng. `thu_thap_tuong/khung.json` cũng được sinh bởi bộ phân loại trong `thong_ke_tuong.py`, không mặc định coi là ground truth độc lập.

## Vị trí mã chính

- `android/vision/src/main/kotlin/vn/afkauto/leoai/vision/TheTuong.kt`: `diemSao` dòng 111, `dacTrungVien` 120, `khungTin` 176, `catTheDanhSach` 266, `ganTen` 350, `DocDanhSach.them` 385.
- `android/app/src/main/java/vn/afkauto/leoai/Leo.kt`: `apDungXacNhan()`, `docDanhSachTuong()`, `napSoKhung()`.
- `android/vision/src/main/kotlin/vn/afkauto/leoai/vision/HoiTruong.kt` và `hoi_truong.py`: bộ cắt mới, nhận nút và luồng chụp Python.
- `test_hoi_truong.py`, `PythonParityTest.danhSachHoiTruong()`: kiểm thử mới. Các số dòng khác có thể đổi khi tiếp tục chỉnh mã.
- `android/app/src/main/java/vn/afkauto/leoai/MainActivity.kt`: `ganDung`, lấy nhãn khung dòng 358.
- Python tương ứng: `doc_tuong_cua_toi.py`, `thong_ke_tuong.py`, `tao_thu_vien_tuong.py`.

## Tài liệu đối chiếu

- [OpenCV matchTemplate và công thức TM_CCOEFF_NORMED](https://docs.opencv.org/4.13.0/df/dfb/group__imgproc__object.html): điểm tương quan ảnh, không phải xác suất phân loại. Việc mở rộng nhiều tỷ lệ là đề xuất thử nghiệm cho dự án.
- [scikit-learn KNeighborsClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsClassifier.html): hỗ trợ bỏ phiếu đều hoặc trọng số nghịch đảo khoảng cách; chưa có kết quả cho thấy loại nào tốt hơn với dữ liệu dự án.
- [scikit-learn Probability calibration](https://scikit-learn.org/stable/modules/calibration.html): nguyên tắc kiểm tra/hiệu chuẩn xác suất bằng dữ liệu phù hợp, tách khỏi dữ liệu huấn luyện.

## Lượt v2 tiếp phần 2–5 (08/11/2026)

Đã tạo quy tắc nhận khung v2 và bản ứng viên riêng, giữ nguyên trọng số học. Kết quả phát triển 43/43 và hồi quy bộ đã biết 50/50; chưa xem hai kết quả này là bằng chứng độc lập mới. Vòng mới đã chụp 16 ảnh, loại nhóm cũ và chọn 40/71 nhóm còn lại, mã `test-2d9de2fc4f0046c5`; đã được người dùng gán nhãn, đạt 40 đúng / 0 sai / 0 chưa rõ và đã kích hoạt trên Python. Chi tiết và quy trình khôi phục nằm trong `quan-ly-mau-va-kiem-chung.md`. Đã bổ sung đối chiếu độ phủ qua màn Bộ Sưu Tập (131 ô, 10 chưa sở hữu, 121 đang có), tách biệt với phép đo khung.

Chốt ngày 09/11: người dùng đã xác nhận đủ 40 thẻ của vòng mới, kết quả 40 đúng / 0 sai / 0 chưa rõ. Bản v2 đã kích hoạt trên Python với cùng 29 mẫu học; không học từ bộ kiểm tra. Đã chốt đối chiếu một-một 121/121 tướng sở hữu của tài khoản kiểm tra.

## Danh sách ngắn và tên theo diện mạo — 09/11/2026

Đã triển khai nhánh không cuộn có số tham chiếu, kiểm tra biên/đếm trùng/ảnh mặt hai chiều. Máy thật đã kiểm tra tài khoản 48 tướng và bộ lọc 6 thẻ; phát hiện và sửa bỏ sót thẻ tóc trắng ở hàng chỉ có một ô. Nhánh hoàn toàn không cuộn hiện có kiểm thử giả lập, không gọi phép thử 48/6 là kiểm chứng nhánh đó trên máy thật.

Thêm 22 mẫu tên từ ảnh chụp mới, đọc tên trực tiếp trong game; giữ các diện mạo cũ và lưu phiên bản quy tắc tên riêng. Đã giải quyết Silvina từng bị gợi ý Isabella sau khi đọc trực tiếp cả hai. 16 ảnh khác mẫu học trong cùng phiên phát triển nhận đúng, không coi là đánh giá độc lập. Báo cáo và giới hạn trong `danh-sach-ngan-va-dien-mao.md`. Android chưa chuyển các thay đổi này.
