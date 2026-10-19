package vn.afkauto.leoai

import android.Manifest
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.view.Gravity
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.RadioButton
import java.io.File
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.view.WindowInsets
import android.widget.CheckBox
import android.widget.EditText
import android.widget.RadioGroup
import android.widget.TextView
import android.widget.Toast
import kotlin.reflect.KMutableProperty0

private const val DONE_COLOR = 0xFF2E7D32.toInt()
private const val TODO_COLOR = 0xFF212121.toInt()

class MainActivity : Activity() {
    private lateinit var prefs: Prefs
    private lateinit var botStatus: TextView
    private lateinit var logView: TextView
    private val logListener: () -> Unit = { logView.text = AppLog.recent(200).joinToString("\n") }
    private val statusListener: () -> Unit = { showStatus() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        prefs = Prefs(this)
        botStatus = findViewById(R.id.botStatus)
        logView = findViewById(R.id.log)
        findViewById<View>(R.id.scroll).setOnApplyWindowInsetsListener { v, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars())
            v.setPadding(bars.left, 0, bars.right, bars.bottom)
            insets
        }

        findViewById<View>(R.id.openA11y).setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        findViewById<View>(R.id.openAppInfo).setOnClickListener {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null)))
        }
        findViewById<View>(R.id.allowNotify).setOnClickListener { askNotifications() }
        findViewById<View>(R.id.reopenOverlay).setOnClickListener {
            BotService.instance?.reopenOverlay()
            Toast.makeText(this, "Bảng nổi sẽ hiện khi bạn rời màn hình này", Toast.LENGTH_SHORT).show()
            showSteps()
        }
        findViewById<View>(R.id.openGame).setOnClickListener {
            val launch = packageManager.getLaunchIntentForPackage(GAME_PACKAGE)
            if (launch != null) startActivity(launch)
            else Toast.makeText(this, "Không tìm thấy Hành Trình AFK trên máy này", Toast.LENGTH_SHORT).show()
        }

        val cheDo = findViewById<RadioGroup>(R.id.cheDo)
        cheDo.check(when (prefs.cheDo) {
            "afk" -> R.id.cheDoAfk
            "huyen_linh" -> R.id.cheDoHuyenLinh
            else -> R.id.cheDoCaHai
        })
        cheDo.setOnCheckedChangeListener { _, id ->
            prefs.cheDo = when (id) {
                R.id.cheDoAfk -> "afk"
                R.id.cheDoHuyenLinh -> "huyen_linh"
                else -> "ca_hai"
            }
        }
        val thieuKhung = findViewById<RadioGroup>(R.id.thieuKhung)
        thieuKhung.check(when (prefs.thieuKhung) {
            "bo" -> R.id.thieuKhungBo
            "thu" -> R.id.thieuKhungThu
            else -> R.id.thieuKhungCuoi
        })
        thieuKhung.setOnCheckedChangeListener { _, id ->
            prefs.thieuKhung = when (id) {
                R.id.thieuKhungBo -> "bo"
                R.id.thieuKhungThu -> "thu"
                else -> "cuoi"
            }
        }
        bindNumber(R.id.nguongLuc, prefs::nguongLuc, NGUONG_LUC_RANGE)
        bindNumber(R.id.soVong, prefs::soVong, SO_VONG_RANGE)
        bindNumber(R.id.thuLai, prefs::thuLai, THU_LAI_RANGE)
        bindNumber(R.id.thuLaiDoiCu, prefs::thuLaiDoiCu, THU_LAI_RANGE)
        bindNumber(R.id.gioToiDa, prefs::gioToiDa, GIO_TOI_DA_RANGE)
        bindNumber(R.id.dungOAi, prefs::dungOAi, DUNG_O_AI_RANGE)
        bindCheck(R.id.boCucHan, prefs::boCucHan)
        bindCheck(R.id.tuDong, prefs::tuDong)
        bindCheck(R.id.leoHo, prefs::leoHo)
        bindCheck(R.id.saveImages, prefs::saveImages)
        bindCheck(R.id.showProbes, prefs::showProbes)

        val advanced = findViewById<View>(R.id.advanced)
        val toggle = findViewById<TextView>(R.id.toggleAdvanced)
        toggle.setOnClickListener {
            val show = advanced.visibility != View.VISIBLE
            advanced.visibility = if (show) View.VISIBLE else View.GONE
            toggle.text = if (show) "Nâng cao ▴" else "Nâng cao ▾"
        }
        findViewById<TextView>(R.id.filesDir).text =
            "Ảnh (tối đa 100 ảnh mới nhất) và nhật ký lưu tại: ${getExternalFilesDir(null)} (thư mục debug/ và nhat_ky.txt)"
        findViewById<View>(R.id.copyLog).setOnClickListener {
            getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Nhật ký", AppLog.all()))
            Toast.makeText(this, "Đã sao chép nhật ký", Toast.LENGTH_SHORT).show()
        }
        findViewById<View>(R.id.clearLog).setOnClickListener { AppLog.clear() }
        val version = packageManager.getPackageInfo(packageName, 0).versionName
        findViewById<TextView>(R.id.version).text = "AFK Auto $version"
    }

    override fun onResume() {
        super.onResume()
        BotService.instance?.setAppScreenOpen(true)
        veKhungTuong()
        showSteps()
        showStatus()
        AppLog.addListener(logListener)
        BotStatus.addListener(statusListener)
        logListener()
    }

    override fun onPause() {
        BotService.instance?.let {
            it.refreshOverlay()
            it.setAppScreenOpen(false)
        }
        AppLog.removeListener(logListener)
        BotStatus.removeListener(statusListener)
        super.onPause()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        showSteps()
    }

    private fun showStatus() {
        botStatus.text = if (BotService.instance == null) "Chưa bật Trợ năng - làm theo các bước bên dưới."
                         else BotStatus.text
    }

    /** Đánh dấu ✓ các bước đã xong, ẩn nút của bước đã xong. */
    private fun showSteps() {
        val a11y = BotService.instance != null
        val notify = Notifier.allowed(this)
        mark(R.id.step1, a11y)
        for (id in listOf(R.id.step1Hint, R.id.openA11y)) findViewById<View>(id).visibility = if (a11y) View.GONE else View.VISIBLE
        // "Cài đặt bị hạn chế" chỉ có từ Android 13, với app cài từ file APK.
        val restricted = !a11y && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
        for (id in listOf(R.id.restrictedHint, R.id.openAppInfo)) findViewById<View>(id).visibility = if (restricted) View.VISIBLE else View.GONE
        findViewById<View>(R.id.reopenOverlay).visibility = if (a11y && prefs.overlayClosed) View.VISIBLE else View.GONE
        mark(R.id.step2, notify)
        findViewById<View>(R.id.allowNotify).visibility = if (notify) View.GONE else View.VISIBLE
    }

    private fun mark(id: Int, done: Boolean) {
        val v = findViewById<TextView>(id)
        val text = v.text.toString().removePrefix("✓ ")
        v.text = if (done) "✓ $text" else text
        v.setTextColor(if (done) DONE_COLOR else TODO_COLOR)
    }

    /** Xin quyền thông báo; đã từ chối hẳn thì mở trang cài đặt thông báo của app. */
    private fun askNotifications() {
        if (shouldShowRequestPermissionRationale(Manifest.permission.POST_NOTIFICATIONS) || !prefsAskedNotify()) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        } else {
            startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName))
        }
    }

    /** Lần đầu bấm thì xin quyền bằng hộp thoại; các lần sau (đã bị từ chối hẳn) mở trang cài đặt. */
    private fun prefsAskedNotify(): Boolean {
        val p = getSharedPreferences("cai_dat", MODE_PRIVATE)
        val asked = p.getBoolean("asked_notify", false)
        p.edit().putBoolean("asked_notify", true).apply()
        return asked
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    /** Mục "Khung tướng của bạn": mỗi tướng quan trọng một dòng (ảnh mặt, %, thẻ ứng viên, Đúng tướng, khung). */
    private fun veKhungTuong() {
        val box = findViewById<LinearLayout>(R.id.khungTuong)
        box.removeAllViews()
        val ds = KhungTuong.quanTrong(this)
        val tay = KhungTuong.docTay(filesDir)
        val tuDoc = KhungTuong.docTuDoc(filesDir)
        val ungVien = KhungTuong.docUngVien(filesDir)
        val xacNhan = KhungTuong.docXacNhan(filesDir)
        for (q in ds) box.addView(dongTuong(q, tay, tuDoc[q.ten], ungVien[q.ten].orEmpty(), xacNhan))
    }

    private fun matThuVien(ten: String): Bitmap? = runCatching {
        val tam = assets.open("vi/tuong/$ten.png").use { BitmapFactory.decodeStream(it) }
        Bitmap.createBitmap(tam, 0, 0, minOf(48, tam.width), minOf(48, tam.height))
    }.getOrNull()

    private fun dongTuong(
        q: KhungTuong.TuongQuanTrong, tay: MutableMap<String, Int>, tuDoc: Int?,
        ungVien: List<KhungTuong.UngVien>, xacNhan: MutableMap<String, KhungTuong.XacNhan>,
    ): View {
        val ten = q.ten
        val dong = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0, dp(8), 0, dp(8)) }
        val tren = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        tren.addView(ImageView(this).apply {
            matThuVien(ten)?.let { setImageBitmap(it) }
            layoutParams = LinearLayout.LayoutParams(dp(44), dp(44))
        })
        val chuTuDoc = when (tuDoc) {
            1 -> "có khung"; 0 -> "không khung"; KhungTuong.TRONG_DOI -> "đang trong đội, chưa đọc được"; else -> "không thấy"
        }
        tren.addView(TextView(this).apply {
            text = "$ten · ${"%.0f".format(q.phan * 100)}% bản ghi\nTự đọc: $chuTuDoc"
            setPadding(dp(10), 0, dp(6), 0)
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        })
        val anhThe = ImageView(this).apply {
            scaleType = ImageView.ScaleType.FIT_CENTER
            layoutParams = LinearLayout.LayoutParams(dp(58), dp(92))
        }
        val dung = CheckBox(this).apply { text = "Đúng\ntướng" }
        tren.addView(anhThe)
        tren.addView(dung)
        dong.addView(tren)

        val fileXn = File(filesDir, "${KhungTuong.THU_MUC_XAC_NHAN}/$ten.png")
        var chiSo = 0
        fun hien() {
            val f = if (xacNhan[ten] != null && fileXn.exists()) fileXn else ungVien.getOrNull(chiSo)?.let { File(filesDir, it.anh) }
            val bmp = f?.takeIf { it.exists() }?.let { BitmapFactory.decodeFile(it.path) }
            anhThe.visibility = if (bmp != null) View.VISIBLE else View.GONE
            // Thẻ đang trong đội bị phủ xanh: không dùng làm mẫu.
            val phuXanh = xacNhan[ten] == null && ungVien.getOrNull(chiSo)?.trongDoi == true
            dung.visibility = if (bmp != null && !phuXanh) View.VISIBLE else View.INVISIBLE
            bmp?.let { anhThe.setImageBitmap(it) }
        }
        dung.isChecked = xacNhan[ten] != null && fileXn.exists()
        hien()
        anhThe.setOnClickListener {
            if (ungVien.isEmpty()) return@setOnClickListener
            if (xacNhan.remove(ten) != null) {             // đang xem thẻ đã xác nhận: chuyển sang các thẻ ứng viên
                fileXn.delete()
                KhungTuong.ghiXacNhan(filesDir, xacNhan)
                dung.setOnCheckedChangeListener(null); dung.isChecked = false; ganDung(dung, ten, tay, ungVien, xacNhan, fileXn) { chiSo }
            } else chiSo = (chiSo + 1) % ungVien.size
            hien()
        }
        ganDung(dung, ten, tay, ungVien, xacNhan, fileXn) { chiSo }

        val nhom = RadioGroup(this).apply { orientation = RadioGroup.HORIZONTAL }
        val chon = listOf(KhungTuong.CO to "Có khung", KhungTuong.KHONG to "Không khung", KhungTuong.CHUA_CO to "Chưa có")
        val nut = chon.map { (v, chu) -> RadioButton(this).apply { text = chu; id = View.generateViewId(); tag = v } }
        nut.forEach { nhom.addView(it) }
        tay[ten]?.let { v -> nut.firstOrNull { it.tag == v }?.isChecked = true }
        nhom.setOnCheckedChangeListener { g, id ->
            val v = g.findViewById<RadioButton>(id)?.tag as? Int ?: return@setOnCheckedChangeListener
            tay[ten] = v
            KhungTuong.ghiTay(filesDir, tay)
            xacNhan[ten]?.let { x -> if (v != KhungTuong.CHUA_CO) { xacNhan[ten] = x.copy(khung = v); KhungTuong.ghiXacNhan(filesDir, xacNhan) } }
        }
        dong.addView(nhom)
        return dong
    }

    /** Tích "Đúng tướng": lưu thẻ đang xem làm thẻ xác nhận của tướng đó (khung theo lựa chọn của bạn, chưa chọn thì theo
     *  kết quả tự đọc của thẻ); bỏ tích thì xoá. Bot áp dụng ở lần chạy hoặc lần đọc khung sau. */
    private fun ganDung(
        dung: CheckBox, ten: String, tay: Map<String, Int>, ungVien: List<KhungTuong.UngVien>,
        xacNhan: MutableMap<String, KhungTuong.XacNhan>, fileXn: File, chiSo: () -> Int,
    ) {
        dung.setOnCheckedChangeListener { _, checked ->
            if (checked) {
                val uv = ungVien.getOrNull(chiSo()) ?: return@setOnCheckedChangeListener
                fileXn.parentFile?.mkdirs()
                File(filesDir, uv.anh).copyTo(fileXn, overwrite = true)
                val k = tay[ten]?.takeIf { it != KhungTuong.CHUA_CO } ?: uv.khung
                xacNhan[ten] = KhungTuong.XacNhan("${KhungTuong.THU_MUC_XAC_NHAN}/$ten.png", k)
            } else {
                xacNhan.remove(ten)
                fileXn.delete()
            }
            KhungTuong.ghiXacNhan(filesDir, xacNhan)
        }
    }

    private fun bindCheck(id: Int, prop: KMutableProperty0<Boolean>) {
        findViewById<CheckBox>(id).apply {
            isChecked = prop.get()
            setOnCheckedChangeListener { _, checked -> prop.set(checked) }
        }
    }

    /** Ô nhập số gắn với một thông số; chỉ lưu khi giá trị nằm trong khoảng cho phép. */
    private fun bindNumber(id: Int, prop: KMutableProperty0<Int>, range: IntRange) {
        val edit = findViewById<EditText>(id)
        edit.setText(prop.get().toString())
        edit.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                val v = s?.toString()?.toIntOrNull()
                if (v != null && v in range) {
                    prop.set(v)
                    edit.error = null
                } else {
                    edit.error = "${range.first}–${range.last}"
                }
            }
        })
    }
}
