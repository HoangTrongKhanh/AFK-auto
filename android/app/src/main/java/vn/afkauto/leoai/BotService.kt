package vn.afkauto.leoai

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.accessibilityservice.GestureDescription.StrokeDescription
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Path
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock
import android.view.Display
import android.widget.Toast
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.opencv.android.Utils
import org.opencv.core.Mat
import org.opencv.imgcodecs.Imgcodecs
import org.opencv.imgproc.Imgproc
import vn.afkauto.leoai.vision.BoMau
import vn.afkauto.leoai.vision.Box
import vn.afkauto.leoai.vision.NhanDien
import vn.afkauto.leoai.vision.REF_W
import java.io.File
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.concurrent.Executors
import kotlin.coroutines.resume

// Hệ thống có lúc không bao giờ trả lời yêu cầu chụp màn hình / thao tác (ví dụ khi lớp "Chống chạm nhầm" của Samsung
// đang che màn hình). Quá hạn thì coi là thất bại thay vì chờ mãi.
private const val SCREENSHOT_TIMEOUT = 5000L
private const val GESTURE_TIMEOUT_EXTRA = 2000L     // cộng thêm vào thời lượng cử chỉ
const val SCREENSHOT_NO_RESPONSE = -1               // mã lỗi riêng: hệ thống không trả lời yêu cầu chụp
private const val OVERLAY_HIDE_WAIT = 80L           // ẩn bảng nổi rồi chờ bấy nhiêu ms cho màn hình vẽ lại trước khi chụp

private const val MAX_DEBUG_IMAGES = 100            // ~3MB/ảnh trên máy 1600x2560
private val FILE_TIME = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss-SSS")

// Vị trí mặc định của bảng nổi (toạ độ máy gốc rộng 1600). Khi chụp hoặc thao tác luôn ẩn bảng tạm.
val DAI_AN_TOAN = Box(100, 150, 1300, 330)

const val GAME_PACKAGE = "com.farlightgames.igame.gp.vn"

/** Bot tự dừng hẳn (đạt điều kiện dừng, kẹt, không thể làm tiếp); reason hiện cho người dùng. */
class StopBot(val reason: String) : Exception(reason)

class ScreenshotFailed(val code: Int) : RuntimeException("chụp màn hình lỗi (mã $code)")

/** Dịch vụ Trợ năng thay cho ADB: chụp màn hình bằng takeScreenshot(), chạm/vuốt bằng dispatchGesture(). */
class BotService : AccessibilityService() {
    companion object {
        @Volatile
        var instance: BotService? = null
            private set
    }

    val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    lateinit var nd: NhanDien
        private set
    lateinit var prefs: Prefs
        private set
    lateinit var leo: Leo
        private set
    private var overlay: Overlay? = null
    private val shotExecutor = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var job: Job? = null
    val isJobRunning: Boolean get() = job?.isActive == true

    /** App đang ở trên cùng màn hình (theo sự kiện đổi cửa sổ, bỏ qua chính app này), "" nếu chưa biết. */
    @Volatile
    var foregroundPackage = ""
        private set

    /** Gọi trên luồng chính với tên tác vụ đang chạy, null khi rảnh. */
    var onJobChanged: (String?) -> Unit = {}

    override fun onServiceConnected() {
        nd = NhanDien(BoMau.load(
            read = { name -> assets.open(name).use { it.readBytes() } },
            list = { dir -> assets.list(dir).orEmpty().toList() },
        ))
        prefs = Prefs(this)
        leo = Leo(this)
        overlay = Overlay(this).also { it.show() }
        applyOverlayVisibility()
        instance = this
        AppLog.i("Đã bật dịch vụ Trợ năng. Mở game ở Màn AFK rồi bấm ▶ trên bảng nổi.")
        if (prefs.running && !prefs.overlayClosed) {
            AppLog.i("Tiếp tục chạy (dịch vụ vừa khởi động lại).")
            startBot()
        } else {
            BotStatus.set("Sẵn sàng · ${prefs.todayText()}")
        }
    }

    // ---------------------------------------------------------------- Tác vụ

    /** ▶ Chạy: leo liên tục; nhớ trạng thái để dịch vụ khởi động lại thì chạy tiếp. */
    fun startBot() {
        prefs.running = true
        runJob("Leo ải") { leo.chay(Leo.CheDoChay.LEO) }
    }

    /** Đánh đúng 1 trận rồi dừng (thử). */
    fun startOneBattle() = runJob("Đánh 1 trận") { leo.chay(Leo.CheDoChay.MOT_TRAN) }

    /** Bài thử: mở Thành Tích, đọc danh sách đội rồi dừng (không đánh, không chép). */
    fun startReadRecords() = runJob("Đọc Thành Tích") { leo.chay(Leo.CheDoChay.XEM_THANH_TICH) }

    /** Đọc khung (phẩm) tướng của bạn ở danh sách tướng màn đội hình; chạy lại sau khi nâng phẩm tướng. */
    var heroesReadStatus = "Bấm đọc để trở lại game, rồi mở Màn AFK hoặc màn đội hình. Bot chờ tối đa 45 giây; kết quả cập nhật khi quay lại app."
        private set

    fun startReadHeroes() = runJob("Đọc khung tướng") { readHeroes() }

    /** Màn app phải xuống nền trước khi đọc; không chụp chính giao diện cài đặt. */
    fun startReadHeroesFromApp() = runJob("Đọc khung tướng") {
        heroesReadStatus = "Đang chờ game hiện để đọc khung tướng…"
        val ready = withTimeoutOrNull(4000) {
            while (appScreenOpen) delay(100)
            // Không dùng tên cửa sổ từ Trợ năng: thông báo/lớp phủ Samsung có thể thay tên dù game vẫn hiện.
            // Luồng đọc kiểm tra Màn AFK/đội hình bằng ảnh trước khi bấm bất cứ nút nào.
            delay(700)
            true
        } == true
        if (!ready) {
            heroesReadStatus = "Chưa thấy game. Hãy mở Màn AFK hoặc màn đội hình rồi bấm Khung tướng trong Nâng cao của bảng nổi."
            Toast.makeText(this, heroesReadStatus, Toast.LENGTH_LONG).show()
            throw StopBot(heroesReadStatus)
        }
        readHeroes(waitForScreen = true)
    }

    private suspend fun readHeroes(waitForScreen: Boolean = false) {
        try {
            if (waitForScreen) {
                heroesReadStatus = "Mở Màn AFK hoặc màn đội hình trong game. Bot đang chờ tối đa 45 giây để đọc."
                BotStatus.set("Đọc khung · chờ Màn AFK / đội hình")
                Toast.makeText(this, heroesReadStatus, Toast.LENGTH_LONG).show()
                val found = withTimeoutOrNull(45_000) {
                    var ready = false
                    while (!ready) {
                        val img = screenshot()
                        ready = try {
                            withContext(Dispatchers.Default) { nd.nhanDien(img).manHinh in listOf("man_afk", "doi_hinh") }
                        } finally { img.release() }
                        if (!ready) delay(1000)
                    }
                    true
                } == true
                if (!found) {
                    heroesReadStatus = "Chưa thấy Màn AFK hoặc đội hình sau 45 giây. Mở đúng màn rồi thử lại bằng nút Khung tướng trên bảng nổi."
                    throw StopBot(heroesReadStatus)
                }
            }
            heroesReadStatus = "Đang đọc khung tướng…"
            BotStatus.set("Đang đọc khung tướng")
            val ok = leo.docTuong()
            heroesReadStatus = if (ok) "Đã đọc xong khung tướng. Kết quả bên dưới đã được cập nhật."
                else "Chưa đọc được: hãy mở Màn AFK hoặc màn đội hình trong game rồi thử lại."
            Toast.makeText(this, heroesReadStatus, Toast.LENGTH_LONG).show()
            if (!ok) throw StopBot(heroesReadStatus)
        } catch (e: CancellationException) {
            heroesReadStatus = "Đã dừng đọc khung tướng. Bạn có thể bấm đọc lại."
            throw e
        } catch (e: Exception) {
            if (e !is StopBot) heroesReadStatus = "Đọc khung tướng gặp lỗi: ${e.message}. Xem Nhật ký để biết chi tiết."
            throw e
        }
    }

    /** Bài thử: nhận diện màn hình hiện tại và ghi vào nhật ký. */
    fun startRecognize() = runJob("Nhận diện màn hình") { leo.nhanDienThu() }

    /** Chạy một tác vụ; mỗi lúc chỉ một tác vụ. */
    fun runJob(name: String, block: suspend () -> Unit) {
        if (job?.isActive == true) return
        val j = scope.launch(start = CoroutineStart.LAZY) {
            AppLog.i("▶ $name")
            try {
                block()
            } catch (e: CancellationException) {
                AppLog.i("Đã dừng.")
                throw e
            } catch (e: StopBot) {
                prefs.running = false
                AppLog.i("DỪNG: ${e.reason}")
                Notifier.show(this@BotService, Notifier.ID_STOPPED, "AFK Auto đã dừng", e.reason)
            } catch (e: Exception) {
                prefs.running = false
                AppLog.e("Lỗi: ${e.message ?: e}", e)
                Notifier.show(this@BotService, Notifier.ID_STOPPED, "AFK Auto dừng vì lỗi",
                    "${e.message ?: e}. Mở app, bấm Sao chép nhật ký và gửi cho người cài app.")
            }
        }
        job = j
        onJobChanged(name)
        overlay?.setKeepingScreenOn(true)
        j.invokeOnCompletion {
            main.post {
                if (job === j) {
                    prefs.running = false
                    overlay?.setKeepingScreenOn(false)
                    onJobChanged(null)
                    val what = if (prefs.overlayClosed) "Bảng nổi đã đóng" else "Đã dừng"
                    BotStatus.set("$what · ${prefs.todayText()}")
                }
            }
        }
        BotStatus.set("Đang chạy · $name")
        j.start()
    }

    /** ■: dừng tác vụ đang chạy (người dùng chủ động dừng nên không tự chạy tiếp nữa). */
    fun stopJob() {
        prefs.running = false
        overlay?.setKeepingScreenOn(false)
        job?.cancel()
        BotStatus.set("Đã dừng · ${prefs.todayText()}")
    }

    /** Lưu ảnh vào files/debug/ (nếu bật trong màn hình chính); giữ tối đa MAX_DEBUG_IMAGES ảnh mới nhất. */
    fun saveImage(img: Mat, name: String, force: Boolean = false) {
        if (!prefs.saveImages && !force) return
        val copy = img.clone()
        scope.launch(Dispatchers.IO) {
            val dir = File(getExternalFilesDir(null), "debug").apply { mkdirs() }
            Imgcodecs.imwrite(File(dir, "${LocalDateTime.now().format(FILE_TIME)}-$name.png").path, copy)
            copy.release()
            dir.listFiles()?.sortedByDescending { it.name }?.drop(MAX_DEBUG_IMAGES)?.forEach { it.delete() }
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val pkg = event?.packageName?.toString() ?: return
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED && pkg != packageName) foregroundPackage = pkg
    }

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        shutdown()
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        shutdown()
        super.onDestroy()
    }

    private fun shutdown() {
        if (instance == null) return
        instance = null
        scope.cancel()
        overlay?.hide()
        overlay = null
        shotExecutor.shutdown()
        BotStatus.set("Đã tắt dịch vụ Trợ năng")
        AppLog.i("Đã tắt dịch vụ Trợ năng.")
    }

    // ---------------------------------------------------------------- Bảng nổi

    private var appScreenOpen = false       // màn hình chính của app đang mở: ẩn bảng nổi để không che nội dung
    private var hiddenForShot = false       // ẩn tạm trong lúc chụp màn hình

    private fun applyOverlayVisibility() {
        overlay?.setVisible(!prefs.overlayClosed && !appScreenOpen && !hiddenForShot)
    }

    fun setAppScreenOpen(open: Boolean) {
        appScreenOpen = open
        applyOverlayVisibility()
    }

    /** Nút ✕: đóng bảng nổi và dừng bot, đồng thời bỏ giữ sáng. */
    fun closeOverlay() {
        if (job?.isActive == true) stopJob()
        AppLog.i("Đã đóng bảng nổi. Mở lại bằng nút Hiện bảng nổi trong app.")
        prefs.overlayClosed = true
        applyOverlayVisibility()
        BotStatus.set("Bảng nổi đã đóng · ${prefs.todayText()}")
    }

    /** Nút Hiện bảng nổi trong app. */
    fun reopenOverlay() {
        prefs.overlayClosed = false
        applyOverlayVisibility()
        if (!isJobRunning) BotStatus.set("Sẵn sàng · ${prefs.todayText()}")
    }

    fun refreshOverlay() {
        overlay?.refreshOptions()
    }

    fun screenWidth(): Int = getSystemService(WindowManager::class.java).maximumWindowMetrics.bounds.width()

    /** Dải an toàn cho bảng nổi trên màn hình này (px màn hình). */
    fun safeBand(): Box {
        val s = screenWidth().toDouble() / REF_W
        return Box((DAI_AN_TOAN.x0 * s).toInt(), (DAI_AN_TOAN.y0 * s).toInt(), (DAI_AN_TOAN.x1 * s).toInt(), (DAI_AN_TOAN.y1 * s).toInt())
    }

    /** Ẩn cả bảng thu gọn trước khi chụp/thao tác, kể cả khi người dùng kéo vào vùng game cần đọc. */
    private suspend fun <T> withoutOverlay(block: suspend () -> T): T {
        val hide = overlay?.boundsOnScreen() != null
        if (hide) {
            hiddenForShot = true
            applyOverlayVisibility()
        }
        try {
            if (hide) delay(OVERLAY_HIDE_WAIT)
            return block()
        } finally {
            if (hide) {
                hiddenForShot = false
                applyOverlayVisibility()
            }
        }
    }

    // ---------------------------------------------------------------- Chụp màn hình

    /** Ảnh chụp màn hình (BGR). Người gọi giải phóng ảnh. */
    suspend fun screenshot(): Mat = withoutOverlay {
        var retries = 0
        var shot: Mat? = null
        while (shot == null) {
            val result = withTimeoutOrNull(SCREENSHOT_TIMEOUT) { requestScreenshot() } ?: SCREENSHOT_NO_RESPONSE
            if (result is ScreenshotResult) shot = withContext(Dispatchers.Default) { toMat(result) }
            else {
                val code = result as Int
                if (code == ERROR_TAKE_SCREENSHOT_INTERVAL_TIME_SHORT && retries < 100) {
                    retries++
                    delay(40)
                } else throw ScreenshotFailed(code)
            }
        }
        shot
    }

    /** ScreenshotResult nếu chụp được, mã lỗi (Int) nếu không. */
    private suspend fun requestScreenshot(): Any = suspendCancellableCoroutine { cont ->
        takeScreenshot(Display.DEFAULT_DISPLAY, shotExecutor, object : TakeScreenshotCallback {
            override fun onSuccess(result: ScreenshotResult) {
                if (cont.isActive) cont.resume(result) else result.hardwareBuffer.close()
            }

            override fun onFailure(errorCode: Int) {
                if (cont.isActive) cont.resume(errorCode)
            }
        })
    }

    private fun toMat(result: ScreenshotResult): Mat {
        val buffer = result.hardwareBuffer
        try {
            val hw = Bitmap.wrapHardwareBuffer(buffer, result.colorSpace)
                ?: throw IllegalStateException("không đọc được ảnh chụp màn hình")
            val bmp = hw.copy(Bitmap.Config.ARGB_8888, false)
            hw.recycle()
            val rgba = Mat()
            Utils.bitmapToMat(bmp, rgba)
            bmp.recycle()
            val bgr = Mat()
            Imgproc.cvtColor(rgba, bgr, Imgproc.COLOR_RGBA2BGR)
            rgba.release()
            return bgr
        } finally {
            buffer.close()
        }
    }

    // ---------------------------------------------------------------- Thao tác

    /** Thực hiện cử chỉ; false nếu bị huỷ hoặc hệ thống không trả lời trong thời lượng cử chỉ + GESTURE_TIMEOUT_EXTRA. */
    private suspend fun dispatch(gesture: GestureDescription): Boolean = withoutOverlay {
        val duration = (0 until gesture.strokeCount).maxOf { gesture.getStroke(it).let { s -> s.startTime + s.duration } }
        val result = withTimeoutOrNull(duration + GESTURE_TIMEOUT_EXTRA) {
            suspendCancellableCoroutine { cont ->
                val callback = object : GestureResultCallback() {
                    override fun onCompleted(d: GestureDescription?) {
                        if (cont.isActive) cont.resume(true)
                    }

                    override fun onCancelled(d: GestureDescription?) {
                        if (cont.isActive) cont.resume(false)
                    }
                }
                if (!dispatchGesture(gesture, callback, null)) cont.resume(false)
            }
        }
        if (result == null) AppLog.i("  Hệ thống không phản hồi thao tác chạm (màn hình đang bị che?).")
        result == true
    }

    private fun line(x0: Int, y0: Int, x1: Int, y1: Int) = Path().apply {
        moveTo(x0.toFloat(), y0.toFloat())
        if (x1 != x0 || y1 != y0) lineTo(x1.toFloat(), y1.toFloat())
    }

    suspend fun tap(x: Int, y: Int) =
        dispatch(GestureDescription.Builder().addStroke(StrokeDescription(line(x, y, x, y), 0, 60)).build())

    suspend fun swipe(x0: Int, y0: Int, x1: Int, y1: Int, ms: Long) =
        dispatch(GestureDescription.Builder().addStroke(StrokeDescription(line(x0, y0, x1, y1), 0, ms)).build())

    // ---------------------------------------------------------------- Trạng thái máy

    fun screenOn() = getSystemService(PowerManager::class.java).isInteractive

    fun uptime() = SystemClock.uptimeMillis()
}
