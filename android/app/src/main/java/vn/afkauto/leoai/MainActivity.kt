package vn.afkauto.leoai

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.view.Gravity
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.Spinner
import android.widget.ArrayAdapter
import android.widget.AdapterView
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
import android.view.WindowManager
import android.content.res.ColorStateList
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.RadioGroup
import android.widget.TextView
import android.widget.Toast
import kotlin.reflect.KMutableProperty0

private const val DONE_COLOR = 0xFF6CD7AC.toInt()
private const val TODO_COLOR = 0xFFE5EDF3.toInt()

class MainActivity : Activity() {
    private val heroDir get() = KhungTuong.duLieu(this)
    private lateinit var prefs: Prefs
    private lateinit var botStatus: TextView
    private lateinit var logView: TextView
    private val logListener: () -> Unit = { logView.text = AppLog.recent(200).joinToString("\n") }
    private val statusListener: () -> Unit = { showStatus() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        prefs = Prefs(this)
        val pages = listOf(R.id.pageTask, R.id.pageHeroes, R.id.pageLogs, R.id.pageSettings)
        val tabs = listOf(R.id.tabTask, R.id.tabHeroes, R.id.tabLogs, R.id.tabSettings)
        fun selectPage(index: Int) {
            pages.forEachIndexed { i, id -> findViewById<View>(id).visibility = if (i == index) View.VISIBLE else View.GONE }
            tabs.forEachIndexed { i, id ->
                findViewById<TextView>(id).apply {
                    isSelected = i == index
                    setTextColor(if (isSelected) getColor(R.color.ui_accent) else getColor(R.color.ui_muted))
                    backgroundTintList = ColorStateList.valueOf(if (isSelected) getColor(R.color.ui_selected) else android.graphics.Color.TRANSPARENT)
                }
            }
            findViewById<android.widget.ScrollView>(R.id.scroll).scrollTo(0, 0)
        }
        tabs.forEachIndexed { i, id -> findViewById<View>(id).setOnClickListener { selectPage(i) } }
        selectPage(0)
        fun collapse(button: Int, panel: Int, title: String) {
            findViewById<TextView>(button).setOnClickListener {
                val v = findViewById<View>(panel)
                v.visibility = if (v.visibility == View.VISIBLE) View.GONE else View.VISIBLE
                findViewById<TextView>(button).text = title + if (v.visibility == View.VISIBLE) " ▴" else " ▾"
            }
        }
        collapse(R.id.setupToggle, R.id.setupPanel, "Thiết lập ban đầu")
        collapse(R.id.teamToggle, R.id.teamSettings, "Chọn đội")
        collapse(R.id.limitToggle, R.id.limitSettings, "Giới hạn chạy")
        findViewById<View>(R.id.runBot).setOnClickListener {
            BotService.instance?.let { if (it.isJobRunning) it.stopJob() else it.startBot() }
            showStatus()
        }
        findViewById<View>(R.id.readHeroes).setOnClickListener {
            val svc = BotService.instance
            when {
                svc == null -> Toast.makeText(this, "Hãy bật Trợ năng trong Thiết lập ban đầu trước", Toast.LENGTH_LONG).show()
                svc.isJobRunning -> Toast.makeText(this, "Hãy dừng tác vụ hiện tại trước", Toast.LENGTH_SHORT).show()
                else -> {
                    Toast.makeText(this, "Đang trở lại game để đọc khung tướng", Toast.LENGTH_SHORT).show()
                    moveTaskToBack(true)
                    svc.expectedHeroes = findViewById<EditText>(R.id.expectedHeroes).text.toString().toIntOrNull()?.takeIf { it > 0 }
                    findViewById<EditText>(R.id.expectedHeroes).setText("")
                    svc.startReadHeroesFromApp()
                }
            }
        }
        botStatus = findViewById(R.id.botStatus)
        logView = findViewById(R.id.log)
        findViewById<View>(android.R.id.content).setOnApplyWindowInsetsListener { v, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars())
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
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
            toggle.text = if (show) "Chẩn đoán ▴" else "Chẩn đoán ▾"
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
        // Bảng nổi có thể vừa đổi hai lựa chọn này trong lúc màn hình cài đặt đang ở nền.
        findViewById<RadioGroup>(R.id.cheDo).check(when (prefs.cheDo) {
            "afk" -> R.id.cheDoAfk
            "huyen_linh" -> R.id.cheDoHuyenLinh
            else -> R.id.cheDoCaHai
        })
        findViewById<CheckBox>(R.id.tuDong).isChecked = prefs.tuDong
        findViewById<CheckBox>(R.id.leoHo).isChecked = prefs.leoHo
        veKhungTuong()
        showSteps()
        showStatus()
        AppLog.addListener(logListener)
        BotStatus.addListener(statusListener)
        logListener()
    }

    override fun onPause() {
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
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
        findViewById<TextView>(R.id.heroesStatus).text = BotService.instance?.heroesReadStatus
            ?: "Bật Trợ năng rồi mở game ở Hội Trường Cộng Hưởng để đọc khung tướng."
        botStatus.text = if (BotService.instance == null) "Chưa bật Trợ năng - làm theo các bước bên dưới."
                         else BotStatus.text
        val svc = BotService.instance
        val active = svc?.isJobRunning == true
        findViewById<TextView>(R.id.runBot).apply { text = if (active) "■ Dừng bot" else "▶ Chạy bot"; isEnabled = svc != null }
        findViewById<TextView>(R.id.energyStatus).text = if (active) "Đang giữ màn hình sáng" else "Đã tắt giữ sáng · theo thời gian chờ của máy"
        if (active) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        for (id in listOf(R.id.cheDoCaHai, R.id.cheDoAfk, R.id.cheDoHuyenLinh, R.id.leoHo, R.id.readHeroes)) findViewById<View>(id).isEnabled = !active
    }

    /** Đánh dấu ✓ các bước đã xong, ẩn nút của bước đã xong. */
    private fun showSteps() {
        val a11y = BotService.instance != null
        val notify = Notifier.allowed(this)
        if (!a11y || !notify) {
            findViewById<View>(R.id.setupPanel).visibility = View.VISIBLE
            findViewById<TextView>(R.id.setupToggle).text = "Thiết lập ban đầu ▴"
        }
        mark(R.id.step1, a11y)
        for (id in listOf(R.id.step1Hint, R.id.openA11y)) findViewById<View>(id).visibility = if (a11y) View.GONE else View.VISIBLE
        // "Cài đặt bị hạn chế" chỉ có từ Android 13, với app cài từ file APK.
        val restricted = !a11y && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
        for (id in listOf(R.id.restrictedHint, R.id.openAppInfo)) findViewById<View>(id).visibility = if (restricted) View.VISIBLE else View.GONE
        findViewById<View>(R.id.reopenOverlay).visibility = if (a11y) View.VISIBLE else View.GONE
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
    private fun heroesIdle(): Boolean {
        if (BotService.instance?.isJobRunning != true) return true
        Toast.makeText(this,"Dừng tác vụ trước khi đổi hồ sơ hoặc bộ mẫu.",Toast.LENGTH_LONG).show(); return false
    }

    private fun veKhungTuong() {
        val box = findViewById<LinearLayout>(R.id.khungTuong)
        box.removeAllViews()
        val profileBox=findViewById<LinearLayout>(R.id.accountProfiles);profileBox.removeAllViews()
        val profiles = KhungTuong.hoSo(this)
        val profile = runCatching { profiles.current() }.getOrElse {
            profileBox.addView(TextView(this).apply { text="Chưa mở được hồ sơ: ${it.message}" }); return
        }
        val all = profiles.list()
        profileBox.addView(TextView(this).apply { text="Tài khoản đang dùng" })
        val selector = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, all.map { it.ten })
            setSelection(all.indexOfFirst { it.id == profile.id })
        }
        selector.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (!selector.isAttachedToWindow || all[position].id == profiles.current().id) return
                if (!heroesIdle()) { selector.setSelection(all.indexOfFirst { it.id == profiles.current().id }); return }
                profiles.select(all[position].id)
                findViewById<EditText>(R.id.expectedHeroes).setText("")
                BotService.instance?.heroProfileChanged()
                veKhungTuong(); showStatus()
            }
        }
        profileBox.addView(selector)
        profileBox.addView(TextView(this).apply { text="Chọn hồ sơ khớp với tài khoản đang mở trong game." })
        val profileButtons = LinearLayout(this)
        for ((rename, label) in listOf(false to "Thêm tài khoản", true to "Đổi tên")) profileButtons.addView(Button(this).apply {
            text=label; setOnClickListener {
                if (!heroesIdle()) return@setOnClickListener
                val input=EditText(this@MainActivity).apply { hint="Tên để phân biệt tài khoản"; if(rename)setText(profile.ten) }
                val dialog=AlertDialog.Builder(this@MainActivity).setTitle(label).setView(input).setNegativeButton("Hủy",null).setPositiveButton("Lưu",null).create()
                dialog.setOnShowListener { dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                    if (!heroesIdle()) return@setOnClickListener
                    runCatching { if(rename)profiles.rename(profile.id,input.text.toString()) else profiles.create(input.text.toString()) }
                        .onSuccess { if(!rename)BotService.instance?.heroProfileChanged(); this@MainActivity.findViewById<EditText>(R.id.expectedHeroes).setText(""); dialog.dismiss(); veKhungTuong(); showStatus() }
                        .onFailure { input.error=it.message }
                } };dialog.show()
            }
        })
        profileBox.addView(profileButtons)
        val ds = KhungTuong.quanTrong(this)
        val tay = KhungTuong.docTay(heroDir)
        val tuDoc = KhungTuong.docTuDoc(heroDir)
        val ungVien = KhungTuong.docUngVien(heroDir)
        val xacNhan = KhungTuong.docXacNhan(heroDir)
        val kho = KhungTuong.kho(this)
        runCatching {
            box.addView(TextView(this).apply { text="Bộ nhận diện: ${kho.current().version}" })
            box.addView(TextView(this).apply { text="Mẫu tên dùng chung; lựa chọn khung tay thuộc hồ sơ đang chọn." })
            val previous=kho.previousVersion()
            val rollback = Button(this).apply { text="Dùng lại bộ mẫu trước"; isEnabled=previous!=null; setOnClickListener {
                if (!heroesIdle()) return@setOnClickListener
                runCatching { kho.rollback() }.onSuccess { veKhungTuong() }.onFailure { Toast.makeText(this@MainActivity,it.message,Toast.LENGTH_LONG).show() }
            } };box.addView(rollback)
            if (kho.usingOlderPackage()) box.addView(Button(this).apply { text="Dùng bộ mẫu mới nhất"; setOnClickListener {
                if (!heroesIdle()) return@setOnClickListener
                runCatching { kho.restorePackaged() }.onSuccess { veKhungTuong() }.onFailure { Toast.makeText(this@MainActivity,it.message,Toast.LENGTH_LONG).show() }
            } })
            val notes=kho.current().samples.optJSONArray("migration_notes")
            if (notes!=null && notes.length()>0) box.addView(TextView(this).apply { text="Một số mẫu cá nhân chưa được chuyển: " + (0 until notes.length()).joinToString("; "){notes.getString(it)} })
            for (record in kho.localSamples().filter { it.getString("status") in listOf("pending","approved") }) {
                val row=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL }
                row.addView(ImageView(this).apply { setImageBitmap(BitmapFactory.decodeFile(kho.pendingImage(record.getString("id")).path));layoutParams=LinearLayout.LayoutParams(dp(48),dp(48)) })
                row.addView(TextView(this).apply { text=record.getString("label") })
                val actions=if(record.getString("status")=="approved") listOf(false to "Thu hồi mẫu") else listOf(true to "Duyệt mẫu tên",false to "Loại mẫu")
                for ((yes,label) in actions) row.addView(Button(this).apply { text=label;setOnClickListener {
                    if (!heroesIdle()) return@setOnClickListener
                    runCatching { kho.review(record.getString("id"),yes) }.onSuccess { veKhungTuong() }.onFailure { Toast.makeText(this@MainActivity,it.message,Toast.LENGTH_LONG).show() }
                } });box.addView(row)
            }
        }.onFailure { box.addView(TextView(this).apply { text="Chưa nạp được bộ nhận diện: ${it.message}" }) }
        val totals=runCatching { org.json.JSONArray(File(heroDir,KhungTuong.TEP_TU_DOC).readText()) }.getOrNull()
        if(totals==null) box.addView(TextView(this).apply { text="Chưa có lượt đọc trong hồ sơ này · ${tay.size} lựa chọn khung tay" })
        if(totals!=null) box.addView(TextView(this).apply { val known=(0 until totals.length()).count{totals.getJSONObject(it).has("ten")}; text="${totals.length()} thẻ · $known tên · ${totals.length()-known} chưa rõ · ${tay.size} lựa chọn khung tay" })
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
            1 -> "có khung"; 0 -> "không khung"; KhungTuong.CHUA_RO -> "chưa rõ khung"; KhungTuong.TRONG_DOI -> "đang trong đội, chưa đọc được"; else -> "không thấy"
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

        val fileXn = File(heroDir, "${KhungTuong.THU_MUC_XAC_NHAN}/$ten.png")
        var chiSo = 0
        fun daXacNhanMoi() = xacNhan[ten]?.mauId?.let { KhungTuong.kho(this).status(it) in listOf("pending","approved") } == true && fileXn.exists()
        fun hien() {
            val f = if (daXacNhanMoi()) fileXn else ungVien.getOrNull(chiSo)?.let { File(heroDir, it.anh) }
            val bmp = f?.takeIf { it.exists() }?.let { BitmapFactory.decodeFile(it.path) }
            anhThe.visibility = if (bmp != null) View.VISIBLE else View.GONE
            // Thẻ đang trong đội bị phủ xanh: không dùng làm mẫu.
            val phuXanh = !daXacNhanMoi() && ungVien.getOrNull(chiSo)?.trongDoi == true
            dung.visibility = if (bmp != null && !phuXanh) View.VISIBLE else View.INVISIBLE
            bmp?.let { anhThe.setImageBitmap(it) }
        }
        dung.isChecked = daXacNhanMoi()
        hien()
        anhThe.setOnClickListener {
            if (ungVien.isEmpty()) return@setOnClickListener
            if (daXacNhanMoi()) {                       // chuyển từ mẫu mới đã lưu sang ảnh ứng viên
                xacNhan.remove(ten)
                fileXn.delete()
                KhungTuong.ghiXacNhan(heroDir, xacNhan)
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
            KhungTuong.ghiTay(heroDir, tay)
            xacNhan[ten]?.let { x -> if (v != KhungTuong.CHUA_CO) { xacNhan[ten] = x.copy(khung = v); KhungTuong.ghiXacNhan(heroDir, xacNhan) } }
        }
        dong.addView(nhom)
        return dong
    }

    /** Tích để chờ duyệt mẫu tên; bỏ tích thu hồi mẫu đã duyệt bằng một phiên bản mới. */
    private fun ganDung(
        dung: CheckBox, ten: String, tay: Map<String, Int>, ungVien: List<KhungTuong.UngVien>,
        xacNhan: MutableMap<String, KhungTuong.XacNhan>, fileXn: File, chiSo: () -> Int,
    ) {
        fun restoreCheck(value: Boolean) {
            dung.setOnCheckedChangeListener(null); dung.isChecked=value
            ganDung(dung,ten,tay,ungVien,xacNhan,fileXn,chiSo)
        }
        dung.setOnCheckedChangeListener { _, checked ->
            if (!heroesIdle()) { restoreCheck(!checked); return@setOnCheckedChangeListener }
            if (checked) {
                val uv = ungVien.getOrNull(chiSo()) ?: return@setOnCheckedChangeListener
                val face = uv.mat?.let { File(heroDir,it) }
                if (face == null || !face.exists() || uv.nguon == null) {
                    Toast.makeText(this,"Ảnh cũ thiếu nguồn. Đọc lại danh sách trước khi bổ sung mẫu.",Toast.LENGTH_LONG).show()
                    restoreCheck(false)
                    return@setOnCheckedChangeListener
                }
                val sampleId = runCatching { KhungTuong.kho(this).stage(ten, face.readBytes(), uv.nguon) }.getOrElse {
                    Toast.makeText(this,it.message,Toast.LENGTH_LONG).show();restoreCheck(false)
                    return@setOnCheckedChangeListener
                }
                Toast.makeText(this,"Đã lưu mẫu chờ duyệt ở đầu danh sách.",Toast.LENGTH_LONG).show()
                fileXn.parentFile?.mkdirs()
                File(heroDir, uv.anh).copyTo(fileXn, overwrite = true)
                val k = tay[ten]?.takeIf { it != KhungTuong.CHUA_CO } ?: uv.khung
                xacNhan[ten] = KhungTuong.XacNhan("${KhungTuong.THU_MUC_XAC_NHAN}/$ten.png", k, sampleId)
            } else {
                val error=runCatching { xacNhan[ten]?.mauId?.let { id -> KhungTuong.kho(this).review(id,false) } }.exceptionOrNull()
                if(error!=null) { Toast.makeText(this,error.message,Toast.LENGTH_LONG).show(); restoreCheck(true); return@setOnCheckedChangeListener }
                xacNhan.remove(ten)
                fileXn.delete()
            }
            KhungTuong.ghiXacNhan(heroDir, xacNhan)
            veKhungTuong()
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
