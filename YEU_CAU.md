# AFK Auto: bot leo ải tự động cho Hành Trình AFK

Tài liệu khảo sát, nghiệp vụ và yêu cầu. Viết ngày 12/10/2026, dựa trên:
- mã nguồn và kinh nghiệm từ dự án `hoa-vien-auto` (bản 1.0 đã phát hành),
- 2 bot mã nguồn mở cho AFK Journey (bản quốc tế),
- ảnh chụp thật từ máy Tab S7 của bạn.

---

## 1. Mục tiêu

Làm một app Android, giống Hoa Viên Auto, cho người chơi **Hành Trình AFK** (bản VN của AFK Journey). App tự **leo ải** (đánh liên tiếp các màn AFK) khi người chơi treo máy:
- thắng thì sang ải tiếp,
- thua thì đánh lại hoặc đổi đội hình,
- gặp sự cố thì tự xử lý hoặc báo cho người dùng.

Người dùng cuối không rành kỹ thuật, nên app chỉ cần cài APK, bật Trợ năng và bấm ▶. Không cần máy tính, ADB hay root.

### Đã chốt (12/10/2026)

| # | Quyết định |
|---|---|
| D1 | Chế độ tự đánh của game **dừng hẳn khi thua 1 trận**. Đã xác minh: trận thua thì dừng ở màn "BẠI" với nút "Thử Lại" (E14) |
| D2 | Làm **cả hai**: Màn AFK (nút Chiến Đấu) và Thách Đấu Huyền Linh |
| D3 | **Chép đội từ Thành Tích** (Ghi chép) khi thua, vì đó là những đội đã qua được ải |
| D4 | **App riêng**, không gộp vào Hoa Viên Auto |
| D5 | **Làm bản chạy trên máy tính qua ADB trước** (giống `xoa_nhiem_vu.py` đời đầu của Hoa Viên), sau đó mới chuyển sang app Android |
| D6 | Máy A54 có cài game, nên thử được trên cả 2 máy (A54 cần kết nối Gỡ lỗi không dây) |
| D7 | Được điều khiển game trên Tab S7 qua ADB để thu thập ảnh mẫu |

## 2. Bằng chứng đã thu thập

| # | Bằng chứng | Nguồn | Kết luận |
|---|---|---|---|
| E1 | Máy Tab S7 (SM-T870, 1600x2560, Android 13) có cài `com.farlightgames.igame.gp.vn`, bản **1.8.11**, cập nhật ngày 10/10/2026 | `adb shell pm list packages` / `dumpsys package` | Đây là package của game VN, khác bản quốc tế `com.farlightgames.igame.gp` |
| E2 | Ảnh màn hình đang mở **Màn AFK**: ải 750 → **751** (đang ở) → 752…757, có 🔒 ở cuối đường ải. Thấy các chữ: nút **"Chiến Đấu"** (1947M), nút **"Thách Đấu Huyền Linh SV"** (2478M), nhãn "Giai Đoạn 1 · Màn Chơi Đỉnh Cao", "Định Đoạt Giai Đoạn 1: 12 ngày 19 giờ", "Cấp Độ Hiệu Ứng Có Lợi Giai Đoạn 1: 10", đồng hồ AFK 00:24:31, nút ← và "Yêu Cầu Của Tôi" | [samples/tab_s7_man_afk_bi_game_booster_khoa.png](samples/tab_s7_man_afk_bi_game_booster_khoa.png) | Giao diện tiếng Việt nên **phải tự làm ảnh mẫu tiếng Việt**: ảnh mẫu tiếng Anh của bot nước ngoài không dùng được. Đang có mùa giải chia giai đoạn |
| E3 | Màn hình trên bị phủ tối (độ sáng trung bình 29/255). `dumpsys window` có cửa sổ **"GameBooster Lock Screen"** (`com.samsung.android.game.gametools`) | `adb shell dumpsys window` | Samsung tự khóa màn hình khi treo game lâu. `GameBooster.kt` của hoa-vien-auto đã xử lý được việc này, **dùng lại được** |
| E4 | AutoAFK2 (Fortigate) có cờ `-s vn`, đổi sang package `.gp.vn`. Luồng của nó: mở Màn AFK → **Records → Copy** đội hình → **Battle** → kết quả **Next** (thắng) / **Retry** (thua). Cứ thua `defeat_limit` lần thì chép đội hình thứ N+1 | [github.com/Fortigate/AutoAFK2](https://github.com/Fortigate/AutoAFK2), `automation/afkj_automation.py` | Có sẵn mô hình nghiệp vụ. Bot này chỉ chạy ở 1080x1920, giao diện tiếng Anh, qua ADB |
| E5 | AdbAutoPlayer (cập nhật 11/10/2026) có các chế độ AFK Stages, **Season AFK Stages**, Legend Trial, Dura's Trials. Cài đặt gồm: `Attempts` (5), `Formations` (10), `Suggested Formations`, `Start with current Formation`, `Spend Gold` (tắt), `Skip Manual Formations`, `Run Manual Formations Last`, `Exclude Heroes` | [github.com/AdbAutoPlayer/AdbAutoPlayer](https://github.com/AdbAutoPlayer/AdbAutoPlayer), `games/afk_journey/base.py`, `settings.py` | Bộ cài đặt đã được cộng đồng kiểm chứng. Nút trái ở màn mùa giải là "Season AFK Stages (Phantimal Challenge)", tức **"Thách Đấu Huyền Linh"** |
| E6 | Các màn hình kết thúc trận mà AdbAutoPlayer phải nhận ra: `Next`, `Victory Rewards`, `Retry`, `Confirm` (lỗi mạng hoặc dữ liệu lệch), `Power Up` (thua), `Result`, `Tap to close` (ải cuối). Trận bị coi là **treo** nếu góc trên trái không đổi suốt 60s | `base.py: _get_battle_over_templates, _wait_for_battle_over_template` | Danh sách trạng thái cần nhận diện, xem mục 5 |
| E7 | Hộp thoại có thể gặp: "Skip this battle?", "Your formation is incomplete", "You haven't activated any Season Faction Talent" / "No hero is placed on the Talent Buff Tile" (có ô *không nhắc lại*), "Spend … to challenge", lỗi mạng, "Are you sure you want to exit the game?" | `popup_message_handler.py` | Phải có bộ xử lý hộp thoại. Tên tiếng Việt cần lấy từ ảnh thật |
| E8 | Bản vá 1.1.16 thêm **Auto Progress** cho Màn AFK: game tự đánh tiếp trong khi người chơi đi làm việc khác, nhưng **game vẫn phải mở**. Game cũng có nút **Auto Battle** | Patch notes Farlight 1.1.16; AutoAFK2 `start_autoprogress()` | Game đã tự đánh liên tiếp được khi đủ mạnh. Bot có ích ở những việc game **không** làm: đổi đội hình khi thua, mở khóa Game Booster, xử lý hộp thoại, báo cho người dùng (mục 4) |
| E9 | Mùa giải chia **3 giai đoạn** (2 giai đoạn đầu mỗi cái 5 tuần). Mỗi giai đoạn có **giới hạn số ải** | Prydwen, "Talk with Designers" (3/2025) | Leo tới giới hạn giai đoạn thì phải **dừng và báo**, không đánh mãi. Ở E2 có nhãn "Màn Chơi Đỉnh Cao" và 🔒, cần kiểm tra thêm |
| E11 | Phía sau lớp khóa Samsung còn **màn hình nghỉ của game**: nhân vật ngủ "Z", chữ "Nhấn để tiếp tục". Chạm vào thì về lại màn đang mở | [samples/tab_s7_game_booster_hien_o_khoa.png](samples/tab_s7_game_booster_hien_o_khoa.png), [tab_s7_game_tiet_kiem_pin_nhan_de_tiep_tuc.png](samples/tab_s7_game_tiet_kiem_pin_nhan_de_tiep_tuc.png) | Phải gỡ **2 lớp**: lớp khóa Samsung (chạm, rồi kéo 🔒 lên ~320px), sau đó chạm "Nhấn để tiếp tục". Cách mở khóa của Hoa Viên chạy tốt ở cả 2 lần thử |
| E12 | Ổ khóa trên đường ải hiện: *"Màn AFK Giai Đoạn 2 sẽ mở khóa sau 12 ngày. Màn Chơi Đỉnh Cao Giai Đoạn 1 sẽ đóng sau khi giai đoạn 2 bắt đầu."* | [tab_s7_tooltip_giai_doan_2.png](samples/tab_s7_tooltip_giai_doan_2.png) | Bạn đã qua giới hạn thường của giai đoạn 1 và đang ở **"Màn Chơi Đỉnh Cao"** (ải 751 Màn AFK, ải 515 Huyền Linh). Chế độ này đóng khi sang giai đoạn 2, nên bot phải nhận ra khi nó đóng |
| E13 | **Màn đội hình** (sau khi bấm Chiến Đấu): góc trên trái là lực chiến đội mình (338,210K), góc trên phải là lực địch (1947M), tiêu đề "Màn Chơi Đỉnh Cao Mùa Giải 238", bảng hiệu ứng thời tiết. Dưới cùng có các nút **←, Thành Tích, Chiến Đấu Tự Động, Chiến Đấu**. Màn đội hình của Huyền Linh **giống hệt** (tiêu đề "…Huyền Linh Sinh Vật 515") | [tab_s7_doi_hinh_man_afk.png](samples/tab_s7_doi_hinh_man_afk.png), [tab_s7_doi_hinh_huyen_linh.png](samples/tab_s7_doi_hinh_huyen_linh.png) | Một luồng dùng cho cả 2 chế độ (D2). Tên VN của "Records" là **"Thành Tích"** |
| E14 | Bấm **"Chiến Đấu Tự Động"** là **bắt đầu trận ngay**, không có hộp xác nhận ("Trận Chiến Bắt Đầu", "Tự Động Chiến Đấu…"). Trận thua (lần này rất nhanh) thì dừng ở màn **"BẠI"**: có "Lời Khuyên Chiến Trận", "Tăng Sức Mạnh", "Hiệp Đồng Tác Chiến AFK (1/1)", và các nút **← / thống kê / Thử Lại**. Ải giữ nguyên ở 751 | [tab_s7_tran_bat_dau_tu_dong.png](samples/tab_s7_tran_bat_dau_tu_dong.png), [tab_s7_ket_qua_bai_thu_lai.png](samples/tab_s7_ket_qua_bai_thu_lai.png) | Xác nhận D1. Thua không mất gì. Bot nhận ra thua nhờ chữ "BẠI" hoặc nút "Thử Lại" |
| E15 | Để yên **~3 phút** sau trận là **Game Booster khóa lại** (độ sáng giảm còn ~27/255) | [tab_s7_ket_qua_bai_bi_phu_toi.png](samples/tab_s7_ket_qua_bai_bi_phu_toi.png) | Lớp khóa xuất hiện thường xuyên khi treo. Bot phải kiểm tra trước mỗi thao tác. Nên khuyên người dùng tắt tính năng khóa trong Game Booster |
| E16 | **Thành Tích**: có đúng **10 đội** (mũi tên ‹ ›, tới đội 10 thì hết ›). Mỗi đội có tên người chơi, lực chiến (289M–384M), nhãn **"Chưa Xếp Hạng"** hoặc **"Cực Hạn"** (= *"Tỷ lệ thành công thấp. Hãy sử dụng thận trọng."*), sơ đồ ô, 5 tướng + cổ vật, nút **"Sao chép"**, nút thống kê, chữ "Nhấn để đóng". Ô **"Chỉ hiển thị đội hình đã sở hữu"** ở góc trên trái | [tab_s7_thanh_tich_10_doi_tong_hop.jpg](samples/tab_s7_thanh_tich_10_doi_tong_hop.jpg), [tab_s7_thanh_tich_cuc_han_giai_thich.png](samples/tab_s7_thanh_tich_cuc_han_giai_thich.png) | Bot bật ô lọc thì khỏi lo đội có tướng chưa sở hữu. Thử đội "Chưa Xếp Hạng" trước, **đội "Cực Hạn" để cuối**. Nhiều đội qua ải với **lực chiến thấp hơn đội bạn** (300M so với 338M), nên chép đội rất có lợi |
| E17 | Vào Màn AFK từ bản đồ thế giới (nút "Màn Chơi Đỉnh Cao 751" góc dưới trái) thì bật **bảng phần thưởng AFK** ("Nhận"). **Chạm ra ngoài bảng cũng nhận thưởng luôn** (đồng hồ AFK về 00:00:01) | [tab_s7_ban_do_the_gioi.png](samples/tab_s7_ban_do_the_gioi.png), [tab_s7_bang_phan_thuong_afk.png](samples/tab_s7_bang_phan_thuong_afk.png) | Bot cần một đường về Màn AFK khi game đang ở bản đồ. Có bảng phần thưởng thì cứ nhận (có lợi, không tốn gì) |
| E18 | **Thứ tự 10 đội trong Thành Tích thay đổi giữa các lần mở**: đội #1 (CG•Linus) lần trước thành #2 lần sau, WTF lên #1 | Bạn chỉ ra; xác minh bằng 2 lần chụp danh sách | **Không chọn đội theo vị trí.** Nhận ra đội theo nội dung (tên người chơi, lực chiến, nhãn) và nhớ các đội đã thử ở từng ải |
| E19 | Bấm **Sao chép** thì đội được thay ngay, không có hộp xác nhận. Game hiện dòng **"Đã sao chép đội hình."** giữa màn hình, và lực chiến góc trên trái đổi theo (338,2M lúc đầu → 257,9M đội CG•Linus) | `tab_s7_doi_hinh_da_sao_chep.png` | Dùng dòng thông báo hoặc lực chiến đổi để xác nhận đã chép xong |
| E20 | **Đang đánh**: góc trên phải có đồng hồ **đếm ngược "88giây"** (trận tối đa ~90 "giây"), các nút **⏸ x4 x2 ⚙**, 5 thẻ tướng có thanh máu. Thua có 2 kiểu: **bị diệt sạch** (~30s) và **hết giờ** (đồng hồ về "0giây", rồi mới hiện BẠI) | `tab_s7_dang_danh.png`, `tab_s7_dang_danh_het_gio_0giay.png`, `tab_s7_ket_qua_bai_het_gio.png` | Chờ trận tối đa ~90s ÷ tốc độ + dư. Hôm nay đồng hồ chạy gần đúng giờ thực (x1?). Phẩm tướng của bạn kém người ghi Thành Tích thì đội chép vẫn có thể thua (bạn chỉ ra) |
| E21 | Thành Tích **Huyền Linh** có thêm nhãn: **"Lý Tưởng"** (tag trên tên), **"Phù Hợp Với Tướng"** (thay chỗ "Chưa Xếp Hạng"), **"✕ Chiến Đấu Thủ Công"** (dưới tên, nghĩa là đội cần đánh tay) | `tab_s7_thanh_tich_huyen_linh_*.png/jpg` | Thứ tự ưu tiên: Lý Tưởng / Phù Hợp Với Tướng → Chưa Xếp Hạng → Cực Hạn. **Bỏ qua Chiến Đấu Thủ Công** |
| E22 | **THẮNG** (Huyền Linh 515, đội HebiZ "Lý Tưởng · Phù Hợp Với Tướng" 287M). Màn thắng có chữ **"THẮNG"**, "Đã Tăng Phần Thưởng AFK", **"Tiến Trình Màn Chơi Đỉnh Cao 751 → 752"**, thu nhập theo giờ, "ⓘ Đã đạt giới hạn hiệu suất AFK hôm nay", các nút **← / thống kê / "Chiến Đấu 2433M"** (ải kế). **Không có nút "Tiếp"**. Về Màn AFK thì đường ải ở **752**, nút Huyền Linh 2433M | `tab_s7_ket_qua_thang.png`, `tab_s7_chuyen_canh_thang.png`, `tab_s7_man_afk_sau_khi_thang_752.png` | **Hai chế độ chung một Tiến Trình Màn Chơi Đỉnh Cao**: thắng bên nào cũng tăng. Bot đọc số "A → B" để ghi nhận qua ải. Đánh tiếp thì bấm "Chiến Đấu" ở màn thắng |
| E23 | Kết quả các trận thử ngày 12/10: Màn AFK 751, đội gốc thua; CG•Linus 300M thua (bị diệt); WTF 305M thua (hết giờ). Huyền Linh 515, HebiZ 287M **thắng** | Nhật ký thử | Ải Màn AFK có thể khó hơn ải Huyền Linh. Chế độ "cả hai" (kẹt bên này thì sang bên kia) rất có ích |
| E24 | **Chạy thật bản máy tính (bước 2)**, Tab S7 ngày 12/10. Lần chạy thứ 3: 36 phút, 47 trận, chép đội 12 lần, **thắng 8 ải liên tiếp 754 → 762**, không lỗi, không cần can thiệp | `leo_ai.log` | Luồng leo ải chạy được thực tế |
| E25 | "Thử Lại" ở màn BẠI dẫn về **màn đội hình** (không vào trận ngay). "Chiến Đấu" ở màn THẮNG dẫn tới **màn đội hình của ải kế**. Số trong ô đỏ trên đường ải và số sau trong "A → B" là **ải đang phải đánh** | Nhật ký lần chạy | Đã dùng trong `leo_ai.py` |
| E26 | Kết quả trận có yếu tố ngẫu nhiên: đội WTF thua (hết giờ) rồi thắng ở lần sau. Ở ải 755–761, đội mang từ ải trước sang thua cả 3 trận, rồi **bản ghi Thành Tích của chính ải đó thắng ngay trận đầu**, kể cả khi là bản ghi của cùng người chơi, vì cách xếp vị trí khác | Nhật ký lần chạy | Đội mang sang chỉ đánh `--thu-lai-doi-cu` trận (mặc định 1) rồi chép. Không coi đội cùng tên + lực chiến ở ải khác là "đã thử" |
| E27 | Nhãn trong Thành Tích có thể đổi: ở ải 754, lần đầu đọc thấy 301M không nhãn, 320M Chưa Xếp Hạng; sau ~25 trận thua thì cả 10 đội đều đọc thành Cực Hạn. Chưa có ảnh chụp để xác minh đây là game đổi nhãn hay bot đọc sai | Nhật ký lần chạy | Cần chụp lại khi gặp. Chỉ ảnh hưởng thứ tự thử |
| E28 | Sau khi bấm mũi tên trong Thành Tích, **thanh thẻ tên vẫn trượt** một lúc sau khi lực chiến đã đứng yên; game đôi khi **bỏ qua một lần bấm mũi tên**. Bảng vừa mở cũng còn trượt vào | Nhật ký lần chạy 1–2 | Chỉ nhận một lần đọc khi 2 ảnh liên tiếp giống nhau. Sau khi di chuyển thì đọc lại vị trí và bấm bù |
| E29 | **Cấu trúc giai đoạn** (bạn cung cấp 12/10): mỗi mùa giải có 3 giai đoạn. Mỗi giai đoạn có "Màn chơi thường" rồi tới "Màn Chơi Đỉnh Cao". Mỗi loại có 2 phần, **Thách Đấu Huyền Linh** (thường nhiều ải hơn) và **Chiến Đấu**, mỗi phần có số ải giới hạn. Hết ải phần nào thì Màn AFK chỉ còn **1 nút ngang** của phần kia. Giai đoạn mới mở thì Màn AFK vẫn hiển thị như cũ | Bạn | Bot nhận ra Màn AFK theo tiêu đề. Thiếu nút của một phần 3 lần liền thì coi phần đó đã hết ải và chuyển phần. Gặp nút ngang chưa có mẫu thì lưu ảnh, báo, dừng. **Cần ảnh mẫu nút ngang** khi gặp |
| E30 | **Đội mang sang** thắng 2/15 lần ở các ải 752–769, vì đây là đoạn khó cuối giai đoạn. Ở đầu giai đoạn, đội mang sang thường leo được nhiều ải. **Mở bùa mới** làm tăng lực chiến, nên ải đang kẹt có thể qua được sau đó. Bản ghi thua khi chép là do **chênh lệch hạng tướng / bùa**, thể hiện qua chênh lệch lực chiến giữa bản ghi và đội của bạn sau khi chép. Số xanh "+179" chỉ là điểm thưởng nhỏ, bỏ qua | Bạn | Quy tắc "đội mang sang đánh 1 trận" hợp cả giai đoạn dễ lẫn khó. Bot ghi lực chiến đội sau khi chép vào `tran.csv` để tìm ngưỡng chênh lệch. Kẹt cả hai phần: dừng và báo (giữ như cũ) |
| E31 | Ở 13/14 ải, **đội đứng đầu Thành Tích thắng ngay trận đầu**. Thứ tự đổi theo kết quả của tài khoản (đội vừa thua tụt xuống) | Phân tích `leo_ai.log` 12/10 | Chép nhanh đội 1 mà không đọc cả danh sách. Các đội sau giữ đúng thứ tự của game |
| E32 | **Khung thẻ tướng = phẩm** (bạn): thẻ có khung là phẩm chuẩn, đủ theo bản ghi; thẻ không khung là yếu so với bản ghi. Trong 420 bản ghi (13/10): Saida, Silven, Frieren, Rolan, Alna có khung ~100%, Mehira chỉ 26%. Tướng của bạn không khung: Saida, Mehira, Talene, Berial. Đội chép (trận đầu): bản ghi có Saida có khung thắng 1/14, có Mehira có khung 3/5, không thiếu khung 15/20 | `thu_thap_tuong/thong_ke.html`, `tuong_cua_toi.html`, `tran.csv` | Bot so khung khi chọn đội, chỉ xét tướng bản ghi dùng có khung >= 50%; bản ghi thiếu khung để sau cùng |
| E10 | Hoa Viên Auto: AccessibilityService `takeScreenshot()` mất ~314ms/ảnh, chạm/kéo bằng `dispatchGesture()`, OpenCV, bảng nổi, thông báo, nhật ký, phát hành APK có ký riêng. Đã chạy thật trên Tab S7 và A54 | `hoa-vien-auto/android/` | Khung kỹ thuật dùng lại gần hết, xem mục 8 |

## 3. Nghiệp vụ game liên quan

| Khái niệm (VN) | Tiếng Anh | Ý nghĩa với bot |
|---|---|---|
| **Màn AFK** | AFK Stages | Chế độ chính. Đánh đội 5 người với máy. Thắng thì lên ải và tăng thu nhập treo máy. Ải tăng dần (hiện ở 751) |
| **Chiến Đấu** (nút) | Battle | Vào màn chuẩn bị đội hình, bấm lần nữa để bắt đầu trận. Số bên dưới (1947M) là **lực chiến đề xuất** của ải |
| **Thách Đấu Huyền Linh** | Season AFK Stages / Phantimal Challenge | Đường ải riêng của mùa giải (lực đề xuất 2478M). Có thể có hộp thoại về Thiên phú phe / ô tăng sức mạnh |
| **Giai Đoạn N** | Season phase | Có hạn chót ("Định Đoạt Giai Đoạn 1: 12 ngày 19 giờ") và giới hạn ải. Đạt giới hạn thì không đánh tiếp được |
| **Thành Tích** (đã xác nhận, E16) | Records | 10 đội của người chơi khác đã qua ải này, có nút **Sao chép**. Có ô lọc **"Chỉ hiển thị đội hình đã sở hữu"**. Nhãn **"Cực Hạn"** nghĩa là tỷ lệ thành công thấp, nên thử sau cùng. *Chưa thấy nhãn "đánh tay" như bản quốc tế* |
| **Chiến Đấu Tự Động** | Auto Battle | Bắt đầu trận **ngay** và tự đánh tiếp các ải sau. **Dừng khi thua** (E14) |
| **Màn Chơi Đỉnh Cao** | Peak stages | Các ải sau giới hạn thường của giai đoạn. Đóng khi giai đoạn sau bắt đầu (E12) |
| **BẠI** + **Thử Lại** (đã xác nhận) / **Tiếp** *(chưa thấy)* | Defeat + Retry / Next | Màn kết quả thua có ←, thống kê, Thử Lại. Màn thắng chưa chụp được |
| Tăng tốc x2/x3, Tự động chiêu cuối | Speed / Auto ult | Phải luôn bật để trận ngắn và không cần chạm tay |
| Thử Thách Huyền Thoại (4 tháp phe) | Legend Trial | Leo tầng theo phe: Ánh Sáng, Tự Nhiên, Bất Tử, Ý Chí. Có ngày chỉ mở một số tháp. Để **giai đoạn sau** |
| Phần thưởng AFK (đồng hồ 00:24:31) | AFK Rewards | Có thể nhận định kỳ. Là việc phụ, không ưu tiên |

**Luật an toàn:** bot **không bao giờ** tiêu Kim cương hoặc Vàng để mua lượt (mặc định giống `Spend Gold = false`). Bot không bấm nút mua hay nạp nào. Gặp hộp thoại tốn tiền thì luôn bấm Hủy. Nguyên tắc này giống "không bao giờ bấm Nhận nhiệm vụ" bên Hoa Viên.

## 4. App thêm được gì so với tính năng tự đánh có sẵn của game

| Tình huống | Game tự làm (Auto Battle / Auto Progress) | App AFK Auto |
|---|---|---|
| Thắng liên tiếp | ✅ tự sang ải | ✅ (hoặc chỉ cần giữ cho Auto Progress chạy) |
| Thua 1 trận do may rủi | ❌ dừng hẳn ở màn BẠI (D1, E14) | ✅ đánh lại tối đa N lần |
| Thua mãi với đội hiện tại | ❌ | ✅ lần lượt chép đội hình từ Ghi chép, bỏ đội "Đánh tay" và đội có tướng bị loại trừ |
| Samsung Game Booster khóa màn hình (E3) | ❌ (kẹt) | ✅ mở khóa như Hoa Viên |
| Hộp thoại lạ, lỗi mạng, mất kết nối | ❌ | ✅ xử lý hoặc báo |
| Tới giới hạn giai đoạn hoặc ải cuối | dừng | ✅ dừng, gửi thông báo, ghi lại ải đạt được |
| Thống kê (đã qua bao nhiêu ải, thua bao nhiêu trận) | ❌ | ✅ |

👉 **Cách làm đã chọn:** bot bấm **"Chiến Đấu Tự Động"** để game tự đánh liên tiếp các ải khi còn thắng. Khi trận thua và game dừng ở màn BẠI, bot tiếp quản:
1. bấm Thử Lại tối đa N lần,
2. hết N lần thì chép đội kế tiếp từ Thành Tích,
3. rồi bật lại Chiến Đấu Tự Động.

Cách này đỡ phải nhận diện từng màn thắng, vì game tự lo phần thắng.

## 5. Luồng nghiệp vụ (máy trạng thái)

```
                ┌──────────────── (màn hình tắt / bị che) ──► CHỜ ── thử lại sau 20s, báo sau ~1 phút
                ▼
 [KIỂM TRA] ─ không thấy game ──► CHỜ (báo "mở lại game ở Màn AFK"; không tự mở game, như Hoa Viên)
     │ thấy GameBooster Lock ──► MỞ KHÓA (chạm + kéo 🔒) ──► KIỂM TRA          (E3, E11, E15: ~3 phút là khóa)
     │ thấy màn nghỉ "Nhấn để tiếp tục" ──► chạm ──► KIỂM TRA                 (E11)
     │ thấy bản đồ thế giới ──► chạm nút Màn AFK góc dưới trái → bảng thưởng → Nhận (E17)
     │ thấy hộp thoại ──► XỬ LÝ HỘP THOẠI (bảng luật; lạ → Hủy/← + lưu ảnh)
     ▼
 [MÀN AFK]  đọc số ải; Màn Chơi Đỉnh Cao đã đóng / ải bị khóa ──► DỪNG + báo
     │ bấm Chiến Đấu (Màn AFK) hoặc Thách Đấu Huyền Linh (tùy chế độ hoặc luân phiên)
     ▼
 [ĐỘI HÌNH] lần đầu: đội hiện tại; thua đủ N lần: CHÉP ĐỘI #k từ Thành Tích
     │        (bật "Chỉ hiển thị đội hình đã sở hữu"; "Chưa Xếp Hạng" trước, "Cực Hạn" sau)
     │ bấm Chiến Đấu Tự Động ──► hộp thoại (đội chưa đủ, chưa bật Thiên phú…) → Xác nhận theo cài đặt
     ▼
 [ĐANG ĐÁNH] game tự đánh tiếp khi thắng; bot chụp mỗi 2–3s, đọc số ải để đếm số ải đã qua
     │ vùng trận đứng yên 60s → TREO → ← / báo
     ▼
 [KẾT QUẢ]
   ├─ BẠI / Thử Lại          → thua++ ; thua < N → Thử Lại (rồi bật lại Chiến Đấu Tự Động)
   │                            thua = N → ← về ĐỘI HÌNH, CHÉP ĐỘI #k+1 (hết 10 đội → DỪNG + báo "kẹt ở ải X")
   ├─ THẮNG (đánh thường)      → đọc "Tiến Trình … A → B", bấm "Chiến Đấu" ở màn thắng để đánh ải kế (E22)
   ├─ ải cuối / hết Màn Đỉnh Cao → DỪNG + báo
   └─ Xác nhận (lỗi mạng)     → bấm, lưu ảnh, quay lại KIỂM TRA
```

## 6. Yêu cầu chức năng

Mức ưu tiên: **P0** = MVP, **P1** = bản 1.1, **P2** = để sau.

### 6.1 Leo ải
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| F1 | Chọn chế độ: **Màn AFK**, **Thách Đấu Huyền Linh**, hoặc **cả hai** (kẹt bên này thì chuyển sang bên kia) | P0 (D2) |
| F2 | Từ Màn AFK: vào đội hình, bắt đầu trận, chờ kết quả, nhận ra **thắng / thua / ải cuối / lỗi**, sang ải tiếp hoặc đánh lại | P0 |
| F3 | Đánh lại tối đa **N lần mỗi đội** (mặc định 5, khoảng 1–50) | P0 |
| F4 | **Chép đội từ Thành Tích**: bật ô "Chỉ hiển thị đội hình đã sở hữu", đọc cả 10 đội (tên, lực chiến, nhãn), xếp theo ưu tiên ở E21, **nhớ các đội đã thử theo tên** vì thứ tự thay đổi (E18). Thắng thì xóa danh sách đã thử cho ải sau | **P0** (D3) |
| F5 | Tùy chọn **"Bắt đầu bằng đội hiện tại"** (mặc định bật): chỉ chép đội khi đội của mình thua đủ N lần | P1 |
| F6 | **Bỏ qua** đội "Chiến Đấu Thủ Công". Để cuối (hoặc bỏ qua, tùy cài đặt) đội "Cực Hạn" | P0 |
| F7 | Danh sách **tướng loại trừ** (không chép đội có tướng đó) | P2 |
| F8 | **Đọc số ải** hiện tại (750, 751…) bằng mẫu chữ số, như cách đọc điểm ở Hoa Viên. Dùng để ghi nhật ký, thống kê, kiểm tra ải có tăng thật sau khi thắng, và để cài **"Dừng ở ải X"** | P0 (đọc) / P1 (dừng) |
| F9 | Nhận ra **giới hạn giai đoạn** hoặc ải bị khóa thì dừng và báo | P0 |
| F10 | Giới hạn an toàn: **dừng sau X trận thua liên tiếp** (tổng mọi đội) hoặc **sau Y giờ** | P0 |
| F11 | Đảm bảo **tốc độ trận cao nhất** và **tự động chiêu cuối** đang bật (kiểm tra mỗi trận, bật nếu tắt) | P1 |
| F12 | Bỏ qua trận (Skip) nếu game cho phép | P2 |
| F13 | Leo **Thử Thách Huyền Thoại**: chọn tháp, bỏ qua tháp không mở hôm nay | P2 |
| F14 | Nhận phần thưởng AFK định kỳ | P2 |

### 6.2 Bền bỉ khi treo lâu
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| R1 | **Mở khóa Samsung Game Booster** (E3). Dùng lại `GameBooster.kt`, nhưng thay "độ sáng tab Nhiệm Vụ" bằng độ sáng của một vùng mốc trong game AFK | P0 |
| R2 | **Bộ xử lý hộp thoại** theo bảng luật (chữ hoặc ảnh mẫu → Xác nhận / Hủy / Dừng). Không bao giờ xác nhận hộp thoại tốn tiền | P0 |
| R3 | Phát hiện **trận bị treo** (vùng trận không đổi 60s) và **game bị thoát** (không thấy mốc nào). Chờ, báo, rồi thử lại khi ổn | P0 |
| R4 | Lỗi mạng hoặc "dữ liệu không khớp": bấm Xác nhận, lưu ảnh, kiểm tra lại từ đầu | P0 |
| R5 | Nhớ trạng thái đang chạy; dịch vụ Trợ năng khởi động lại thì **chạy tiếp** (giống `prefs.running`) | P0 |
| R6 | Không thao tác nếu màn hình tắt; cảnh báo pin yếu khi không sạc (có sẵn) | P0 |
| R7 | Không tự mở lại game (giữ quyết định của Hoa Viên); chỉ báo cho người dùng | P0 |

### 6.3 Giao diện và thông báo (dùng lại từ Hoa Viên)
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| U1 | Bảng nổi: ▶ Chạy / ■ Dừng / Thử 1 trận, thu gọn, kéo di chuyển, ✕ đóng. **Vị trí mặc định không đè lên các nút của game** (nút Chiến Đấu, Tiếp, Thử lại ở dải dưới, chữ ở dải trên) | P0 |
| U2 | Dòng trạng thái: "Ải 751 · thua 2/5 · đội #1 · hôm nay qua 12 ải" | P0 |
| U3 | Màn hình chính: các bước cài đặt (Trợ năng, thông báo, cài đặt bị hạn chế), các cài đặt ở mục 6.1, nút Mở game, nhật ký, Sao chép nhật ký | P0 |
| U4 | Thông báo hệ thống: tới giới hạn giai đoạn, kẹt ở ải X, game bị thoát, lỗi | P0 |
| U5 | Thống kê theo ngày: số ải đã qua, số trận, tỉ lệ thắng, ải cao nhất | P1 |
| U6 | Lưu ảnh để tra lỗi (tối đa 100 ảnh), các bài thử ⋯ (Chụp, Chạm, Mốc giao diện, Game Booster) | P0 |
| U7 | Trang hướng dẫn cài đặt (sửa lại từ `huong_dan/` của Hoa Viên) | P1 |

## 7. Yêu cầu phi chức năng

- **Thiết bị**: Android 11 trở lên (cần `takeScreenshot`). Phải chạy được trên **Tab S7 1600x2560** (máy có game, tỉ lệ 10:16) và điện thoại **1080x2340** (A54, 9:19.5). Bot nước ngoài chỉ hỗ trợ 1080x1920, nên đây là **điểm khó mới** (mục 9).
- **Ngôn ngữ game**: tiếng Việt. Thiết kế để sau này thêm tiếng Anh được (ảnh mẫu tách thư mục `vi/`, `en/`).
- **Chịu được bản cập nhật game**: ảnh mẫu là dữ liệu, không viết cứng trong code. Không nhận ra màn hình thì lưu ảnh và báo, **không bấm bừa**.
- **An toàn tài khoản**: chỉ bấm vào những vùng đã nhận diện được. Có danh sách vùng cấm bấm (nút mua, nạp, kim cương), như `ACCEPT_BTN_ZONE` của Hoa Viên.
- **Riêng tư**: không gửi dữ liệu ra ngoài, không đọc app khác (giữ mô tả Trợ năng như Hoa Viên).
- **Hiệu năng và pin**: khi đang đánh chỉ chụp mỗi 1–2 giây, vì trận dài 30–90 giây. Khuyên người dùng cắm sạc, đồ họa thấp, tắt chữ sát thương trong trận (theo khuyến nghị của AdbAutoPlayer).
- **Kiểm thử được**: phần nhận diện nằm ở module `vision` thuần Kotlin, có unit test chạy trên ảnh mẫu (giống `PythonParityTest` của Hoa Viên).

## 8. Dùng lại gì từ hoa-vien-auto

| Thành phần Hoa Viên | Cách dùng |
|---|---|
| `BotService.kt` (chụp màn hình, chạm, kéo, giới hạn thời gian chờ, tác vụ, lưu ảnh) | **Giữ nguyên**, chỉ đổi tên gói |
| `Overlay.kt`, `Status.kt` (Notifier), `AppLog.kt`, `MainActivity.kt` + layout các bước cài đặt | **Giữ nguyên**, sửa chữ và các cài đặt |
| `GameBooster.kt` | **Sửa**: thay hàm đo độ sáng bằng mốc của game AFK |
| `Prefs` | **Sửa**: chế độ, số lần đánh lại, số đội, đội hiện tại trước, dừng ở ải, giới hạn thua, giới hạn giờ |
| `Bot.kt` (quét danh sách, xóa nhiệm vụ) | **Viết mới** thành `Leo.kt` theo máy trạng thái ở mục 5. Giữ các kiểu `poll` / `pollStable` / `waitStill` |
| `vision/Vision.kt` (Templates, Ui quy đổi tọa độ, khớp mẫu 2 bước MATCH_SCALE) | **Giữ khung**, viết lại phần riêng của game: các màn hình, nút, vùng |
| `vision/Digits.kt` (đọc chữ số bằng mẫu) | **Dùng lại** để đọc số ải. Cần bộ mẫu chữ số mới theo font của AFK |
| `Probes.kt` | Giữ Chụp, Chạm, Game Booster. Thêm bài thử **"Nhận diện màn hình hiện tại"** |
| Phát hành: khóa ký riêng, `./gradlew phatHanh`, minSdk 30 | **Tạo khóa ký mới** (app khác applicationId, ví dụ `vn.afkauto.leoai`) |
| `xoa_nhiem_vu.py` (lớp `Adb`: chụp gzip/raw tự chọn cách nhanh hơn, chạm, kéo; ghi nhật ký xoay vòng) và `ket_noi.py` (dò cổng Gỡ lỗi không dây) | **Dùng lại cho bản máy tính** (D5). Sau đó bản Python làm **chuẩn đối chiếu** khi chuyển sang Kotlin, như Hoa Viên đã làm |

Đề xuất: **app riêng** (khác applicationId, tên "AFK Auto"), chép các file lõi sang và chưa tách thư viện chung. Lý do: hai game khác nhau hoàn toàn, mỗi app phát hành riêng qua Zalo, và chép code đơn giản hơn tách module. Nếu sau này làm app thứ 3 thì tách `core` ra một module dùng chung.

## 9. Nhận diện màn hình nhiều độ phân giải

Hoa Viên giả định game co giãn theo chiều ngang và lấy độ lệch dọc từ **một** mốc (tab Nhiệm Vụ). AFK Journey trên Tab S7 tỉ lệ 10:16 và trên A54 tỉ lệ 9:19.5 sẽ bố trí khác nhau:
- các nút ở dải dưới bám mép dưới,
- thanh trên bám mép trên,
- phần giữa giãn ra.

Cách làm đề xuất:
1. Hệ số co giãn `s` = rộng màn hình / 1080 (cần kiểm chứng trên cả 2 máy).
2. **Mỗi vùng có mốc riêng**: dải dưới (nút Chiến Đấu, Tiếp, Thử lại) tính tọa độ từ mép dưới, dải trên từ mép trên. Hoặc đơn giản hơn: **tìm mẫu trong cả nửa màn hình** (như AdbAutoPlayer cắt `top=0.5`), rồi bấm vào tâm chỗ khớp, không dùng tọa độ cố định.
3. Khớp mẫu ở nhiều tỉ lệ (s ± 5%) cho chắc. Ngưỡng khớp ≥ 0.80, như Hoa Viên.
4. Chữ trên nút có viền và bóng. Khớp màu hoặc khớp mức xám trên ảnh thu nhỏ `MATCH_SCALE = 0.5` (đã nhanh hơn ~7 lần ở Hoa Viên).
5. Số ải: cắt ô số dưới mốc ải đang chọn (nền cam, chữ trắng, xem E2), phân ngưỡng, so với mẫu chữ số.
6. Hộp thoại: nhận diện bằng ảnh mẫu tiêu đề hoặc nút. **OCR tiếng Việt (ML Kit)** chỉ cân nhắc nếu có quá nhiều loại hộp thoại; nó làm app nặng thêm khoảng 5–10MB.

## 10. Rủi ro

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| **Vi phạm điều khoản của nhà phát hành**, có thể bị khóa tài khoản vì dùng công cụ tự động | Cao, ngoài tầm kỹ thuật | Người dùng tự chịu trách nhiệm (ghi rõ trong hướng dẫn). Thao tác giống người: có độ trễ ngẫu nhiên, không đánh 24/24 nếu không cần. Có giới hạn giờ (F10) |
| Game cập nhật làm đổi giao diện hoặc chữ | Cao (game ra bản thường xuyên, mới cập nhật 10/10) | Ảnh mẫu là dữ liệu. Có bài thử "Nhận diện màn hình". Không nhận ra thì dừng và báo |
| Bố cục khác nhau giữa máy tính bảng và điện thoại | Trung bình | Mục 9. Lấy ảnh mẫu trên cả 2 máy |
| Đội chép từ Ghi chép cần tướng chưa có, hoặc cần đánh tay | Trung bình | F4, F6. Bỏ qua và ghi nhật ký |
| Đánh trúng nút tốn tiền | Thấp nhưng hậu quả lớn | Vùng cấm bấm; hộp thoại có chữ "Kim cương / Vàng / Mua" thì luôn Hủy |
| Game Booster, chống chạm nhầm, màn hình tắt | Đã gặp (E3) | Dùng lại cách xử lý của Hoa Viên |
| Trận dài và nóng máy, hết pin | Trung bình | Cảnh báo pin. Khuyên đồ họa thấp, cắm sạc |
| Cài đè lên Hoa Viên Auto hoặc nhầm app | Thấp | applicationId riêng, khóa ký riêng |

## 11. Kế hoạch triển khai (đã sửa theo D5: làm bản máy tính trước)

### Bản máy tính (Python + OpenCV + ADB)

Thư mục dự kiến:

```
AFK-Auto/
  leo_ai.py          # chương trình chính: máy trạng thái ở mục 5, tham số dòng lệnh
  nhan_dien.py       # ảnh màn hình -> tên màn hình + vị trí nút (không phụ thuộc ADB, test được bằng ảnh)
  adb.py, ket_noi.py # chép từ hoa-vien-auto
  templates/vi/      # ảnh mẫu nút và chữ cắt từ samples/ (theo máy gốc 1600x2560, tự co giãn)
  samples/ + samples/nhan.txt   # ảnh mẫu và tên màn hình đúng của từng ảnh
  test_nhan_dien.py  # chạy nhận diện trên mọi ảnh mẫu, so với nhan.txt
```

Tham số dự kiến:

| Tham số | Ý nghĩa |
|---|---|
| `--che-do afk\|huyen-linh\|ca-hai` | Chế độ leo (F1) |
| `--thu-lai 5` | Số lần đánh lại mỗi đội (F3) |
| `--so-doi 10` | Số đội tối đa chép từ Thành Tích (F4) |
| `--cuc-han cuoi\|bo` | Đội "Cực Hạn" để cuối hoặc bỏ qua (F6) |
| `--dung-o-ai N`, `--gio-toi-da H`, `--thua-toi-da X` | Các điều kiện dừng (F8, F10) |
| `--from-image anh.png` | Chỉ nhận diện một ảnh, không cần máy |
| `--mot-tran` | Đánh đúng 1 trận rồi dừng |
| `--serial` | Chọn máy |

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| **0. Thu thập ảnh mẫu** | ✅ Phần lớn đã xong trên Tab S7 (mục 12). Còn thiếu: màn **thắng**, luồng **Sao chép → Chiến Đấu**, các hộp thoại, ảnh trên A54 | Có ≥ 1 ảnh cho mỗi trạng thái ở mục 5 |
| **1. Nhận diện** | `nhan_dien.py` nhận ra: Màn AFK, đội hình (AFK / Huyền Linh), Thành Tích, đang đánh, BẠI, thắng, bản đồ thế giới, bảng phần thưởng, khóa Game Booster, màn nghỉ. Đọc số ải. Chạy được ở 1600x2560 và 1080x2340 | `test_nhan_dien.py` đúng 100% ảnh mẫu. ✅ **Xong 12/10 trên Tab S7** (xem README.md), đã chạy thử trên máy thật. Máy 1080x2340 (A54) chưa kiểm tra bằng ảnh thật |
| **2. Leo ải cơ bản** | `leo_ai.py`: KIỂM TRA, mở khóa, Chiến Đấu Tự Động, theo dõi trận, BẠI thì Thử Lại N lần, điều kiện dừng, nhật ký. Chạy thử trên Tab S7 **khi bạn cho phép đánh thật** | Treo 1–2 giờ không kẹt. Nhật ký ghi đúng số ải đã qua. ✅ **Xong 12/10** (cùng bước 3 Chép đội): thắng 8 ải liên tiếp trong 36 phút |
| **3. Chép đội** | Thành Tích: bật lọc đã sở hữu, đội #k, bỏ hoặc để cuối Cực Hạn, Sao chép. Luân phiên AFK và Huyền Linh khi một bên bị kẹt | Thua N lần thì tự chép đội #2 và đánh tiếp. ✅ **Xong 12/10** (`leo_ai.py`). Chuyển AFK ↔ Huyền Linh khi kẹt: đã viết, chưa gặp tình huống kẹt thật |
| **4. Thử trên A54** | Kết nối Gỡ lỗi không dây (`ket_noi.py`), chỉnh bố cục 1080x2340 | Chạy được 1 giờ trên A54 |
| **5. Chuyển sang app Android** | Chép lõi Hoa Viên (mục 8), port `nhan_dien.py` sang Kotlin, đối chiếu với Python bằng ảnh mẫu (như `PythonParityTest`), bảng nổi, thông báo, phát hành APK có khóa ký mới | Bản 1.0 cài được trên máy của người quen |

## 12. Ảnh mẫu đã có và còn thiếu

Đã thu thập trên Tab S7 ngày 12/10/2026, xem thư mục `samples/`:

| Trạng thái | File | |
|---|---|---|
| Màn AFK bình thường | `tab_s7_man_afk.png`, `…_sau_khi_nhan_thuong.png`, `…_sau_tran_thua.png` | ✅ |
| Màn AFK bị Game Booster khóa | `tab_s7_man_afk_bi_game_booster_khoa.png`, `tab_s7_ket_qua_bai_bi_phu_toi.png` | ✅ |
| Lớp khóa đang hiện 🔒 | `tab_s7_game_booster_hien_o_khoa.png` | ✅ |
| Màn nghỉ của game "Nhấn để tiếp tục" | `tab_s7_game_tiet_kiem_pin_nhan_de_tiep_tuc.png` | ✅ |
| Giải thích Giai Đoạn 2 / Màn Chơi Đỉnh Cao | `tab_s7_tooltip_giai_doan_2.png` | ✅ |
| Bản đồ thế giới | `tab_s7_ban_do_the_gioi.png` | ✅ |
| Bảng phần thưởng AFK | `tab_s7_bang_phan_thuong_afk.png` | ✅ |
| Đội hình Màn AFK / Huyền Linh | `tab_s7_doi_hinh_man_afk.png`, `tab_s7_doi_hinh_huyen_linh.png` | ✅ |
| Thành Tích (đội 1, 2, cuối, Cực Hạn, lọc đã sở hữu, tổng hợp 10 đội) | `tab_s7_thanh_tich_*.png/jpg` | ✅ |
| Bắt đầu trận tự động | `tab_s7_tran_bat_dau_tu_dong.png` | ✅ |
| Kết quả BẠI / Thử Lại | `tab_s7_ket_qua_bai_thu_lai.png` | ✅ |
| Đang đánh, hết giờ, bắt đầu trận | `tab_s7_dang_danh*.png`, `tab_s7_tran_chien_bat_dau.png` | ✅ |
| Màn **thắng** | `tab_s7_ket_qua_thang.png`, `tab_s7_chuyen_canh_thang.png` | ✅ (đánh thường) |
| Màn chuyển ải khi đang **Chiến Đấu Tự Động** mà thắng | | ❌ |
| Sau khi Sao chép | `tab_s7_doi_hinh_da_sao_chep.png` | ✅ (không có hộp thoại) |
| Thành Tích Huyền Linh (Lý Tưởng, Phù Hợp Với Tướng, Thủ Công) | `tab_s7_thanh_tich_huyen_linh_*` | ✅ |
| Hộp thoại: đội chưa đủ, chưa bật Thiên phú, lỗi mạng, thoát game | | ❌ gặp lúc nào thì lưu lúc đó |
| Mọi ảnh trên **A54** (1080x2340) | | ❌ cần kết nối máy |

## 13. Còn cần bạn quyết định

1. **Cho phép đánh thật để chụp nốt ảnh mẫu.** Màn thắng và hộp thoại Sao chép chỉ chụp được khi chép một đội từ Thành Tích và đánh thật. Việc chép sẽ **thay đội hình hiện tại** của bạn ở Màn AFK.
2. **Người dùng cuối:** chỉ bạn dùng, hay sau này gửi người quen như Hoa Viên? Câu này chưa có trả lời. Nó ảnh hưởng tới giai đoạn 5, chưa ảnh hưởng bản máy tính.
3. **Có nên tắt khóa của Game Booster** trên Tab S7 khi chạy bản máy tính không? Bot vẫn tự mở khóa được, nhưng tắt đi thì ít thao tác thừa hơn.

---

### Nguồn tham khảo
- [AutoAFK2 (Fortigate)](https://github.com/Fortigate/AutoAFK2): bot ADB cho AFK Journey, có hỗ trợ server VN
- [AdbAutoPlayer](https://github.com/AdbAutoPlayer/AdbAutoPlayer) và [tài liệu AFK Journey](https://adbautoplayer.github.io/AdbAutoPlayer/games/afk-journey.html)
- [BlueStacks: các chế độ PvE/PvP trong Hành Trình AFK](https://www.bluestacks.com/vi/blog/game-guides/afk-2-journey/afkj-pve-pvp-instances-guide-vi.html)
- [Sportskeeda: mẹo leo Màn AFK, Records, auto-challenge](https://www.sportskeeda.com/esports/afk-journey-best-tips-team-progress-faster-afk-stages)
- [Prydwen: Talk with Designers, mùa giải 3 giai đoạn](https://blog.prydwen.gg/2025/03/17/afk-journey-chains-of-eternity-talk-with-designers/)
- [Di Động Việt: Hành Trình AFK là AFK Journey bản VN](https://didongviet.vn/dchannel/code-hanh-trinh-afk/)
