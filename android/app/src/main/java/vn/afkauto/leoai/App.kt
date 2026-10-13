package vn.afkauto.leoai

import android.app.Application
import android.content.Context
import org.opencv.android.OpenCVLoader

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        AppLog.init(this)
        if (!OpenCVLoader.initLocal()) AppLog.i("Không nạp được thư viện OpenCV.")
    }
}

// Khoảng cho phép của các cài đặt (dùng ở màn hình chính).
val THU_LAI_RANGE = 1..20
val GIO_TOI_DA_RANGE = 0..48
val DUNG_O_AI_RANGE = 0..99999

/** Cài đặt, chỉnh ở màn hình chính. Bot đọc lại mỗi khi bắt đầu chạy (chế độ) và trước mỗi quyết định (số trận). */
class Prefs(context: Context) {
    private val p = context.getSharedPreferences("cai_dat", Context.MODE_PRIVATE)

    /** "ca_hai" | "afk" | "huyen_linh". */
    var cheDo: String
        get() = p.getString("che_do", "ca_hai") ?: "ca_hai"
        set(v) = p.edit().putString("che_do", v).apply()

    /** Số trận mỗi đội (đội có sẵn lúc bắt đầu, đội vừa chép) trước khi chép đội khác. */
    var thuLai: Int
        get() = p.getInt("thu_lai", 3).coerceIn(THU_LAI_RANGE)
        set(v) = p.edit().putInt("thu_lai", v).apply()

    /** Số trận của đội vừa thắng ải trước khi sang ải mới, trước khi chép đội của ải mới. */
    var thuLaiDoiCu: Int
        get() = p.getInt("thu_lai_doi_cu", 1).coerceIn(THU_LAI_RANGE)
        set(v) = p.edit().putInt("thu_lai_doi_cu", v).apply()

    /** Bỏ qua đội Cực Hạn (tỉ lệ thành công thấp) thay vì thử sau cùng. */
    var boCucHan: Boolean
        get() = p.getBoolean("bo_cuc_han", false)
        set(v) = p.edit().putBoolean("bo_cuc_han", v).apply()

    /** Dừng sau bấy nhiêu giờ, 0 = không giới hạn. */
    var gioToiDa: Int
        get() = p.getInt("gio_toi_da", 0).coerceIn(GIO_TOI_DA_RANGE)
        set(v) = p.edit().putInt("gio_toi_da", v).apply()

    /** Dừng khi tiến trình tới ải này, 0 = không. */
    var dungOAi: Int
        get() = p.getInt("dung_o_ai", 0).coerceIn(DUNG_O_AI_RANGE)
        set(v) = p.edit().putInt("dung_o_ai", v).apply()

    var saveImages: Boolean
        get() = p.getBoolean("save_images", false)
        set(v) = p.edit().putBoolean("save_images", v).apply()

    /** Hiện nút ⋯ (các bài thử) trên bảng nổi. */
    var showProbes: Boolean
        get() = p.getBoolean("show_probes", false)
        set(v) = p.edit().putBoolean("show_probes", v).apply()

    /** Bot đang chạy (▶): dịch vụ khởi động lại thì chạy tiếp. Tắt khi người dùng bấm ■. */
    var running: Boolean
        get() = p.getBoolean("running", false)
        set(v) = p.edit().putBoolean("running", v).apply()

    /** Người dùng đã đóng bảng nổi (nút ✕); mở lại bằng nút Hiện bảng nổi trong app. */
    var overlayClosed: Boolean
        get() = p.getBoolean("overlay_closed", false)
        set(v) = p.edit().putBoolean("overlay_closed", v).apply()

    /** Vị trí bảng nổi người dùng đã kéo tới, -1 = mặc định. */
    var overlayX: Int
        get() = p.getInt("overlay_x", -1)
        set(v) = p.edit().putInt("overlay_x", v).apply()

    var overlayY: Int
        get() = p.getInt("overlay_y", -1)
        set(v) = p.edit().putInt("overlay_y", v).apply()

    // Thống kê trong ngày (xem Status.kt).
    var statDate: String
        get() = p.getString("stat_date", "") ?: ""
        set(v) = p.edit().putString("stat_date", v).apply()

    var statWins: Int
        get() = p.getInt("stat_wins", 0)
        set(v) = p.edit().putInt("stat_wins", v).apply()

    var statBattles: Int
        get() = p.getInt("stat_battles", 0)
        set(v) = p.edit().putInt("stat_battles", v).apply()

    /** Tiến trình (số ải đang phải đánh) đọc được gần nhất. */
    var lastStage: Int
        get() = p.getInt("last_stage", 0)
        set(v) = p.edit().putInt("last_stage", v).apply()
}
