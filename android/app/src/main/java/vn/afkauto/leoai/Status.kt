package vn.afkauto.leoai

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import java.time.LocalDate
import java.util.concurrent.CopyOnWriteArraySet

/** Một dòng trạng thái của bot, hiện trên bảng nổi và màn hình chính. Listener luôn được gọi trên luồng chính. */
object BotStatus {
    private val main = Handler(Looper.getMainLooper())
    private val listeners = CopyOnWriteArraySet<() -> Unit>()

    @Volatile
    var text: String = "Chưa chạy"
        private set

    fun set(text: String) {
        this.text = text
        main.post { listeners.forEach { it() } }
    }

    fun addListener(l: () -> Unit) = listeners.add(l)

    fun removeListener(l: () -> Unit) = listeners.remove(l)
}

private fun Prefs.homNay(): Boolean {
    val today = LocalDate.now().toString()
    if (statDate == today) return true
    statDate = today
    statWins = 0
    statBattles = 0
    return false
}

/** Số ải đã qua / số trận trong ngày (theo lịch máy), lưu lại qua các lần chạy. */
fun Prefs.winsToday(): Int = if (statDate == LocalDate.now().toString()) statWins else 0

fun Prefs.battlesToday(): Int = if (statDate == LocalDate.now().toString()) statBattles else 0

fun Prefs.addBattle(win: Boolean) {
    homNay()
    statBattles += 1
    if (win) statWins += 1
}

fun Prefs.todayText() = "hôm nay qua ${winsToday()} ải / ${battlesToday()} trận"

/** Thông báo cho người dùng khi bot cần người can thiệp (game bị thoát, màn hình lạ, pin yếu...). */
object Notifier {
    private const val CHANNEL = "can_nguoi"
    const val ID_WAITING = 1        // bot đang chờ (không nhận ra màn hình, game bị thoát...)
    const val ID_STOPPED = 2        // bot đã dừng (kẹt, đủ giờ, lỗi)
    const val ID_BATTERY = 3

    fun allowed(ctx: Context) =
        ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    fun show(ctx: Context, id: Int, title: String, text: String) {
        if (!allowed(ctx)) return
        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CHANNEL, "Cần bạn xử lý", NotificationManager.IMPORTANCE_HIGH)
            .apply { description = "Báo khi bot dừng hoặc không tự làm tiếp được" })
        val open = PendingIntent.getActivity(ctx, 0, Intent(ctx, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val n = android.app.Notification.Builder(ctx, CHANNEL)
            .setSmallIcon(R.drawable.ic_notify)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(android.app.Notification.BigTextStyle().bigText(text))
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        nm.notify(id, n)
    }

    fun cancel(ctx: Context, id: Int) {
        ctx.getSystemService(NotificationManager::class.java).cancel(id)
    }
}
