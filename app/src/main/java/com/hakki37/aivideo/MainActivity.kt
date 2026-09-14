package com.hakki37.aivideo

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { AivideoApp() }
    }

    private fun normalizedUrl(value: String): String {
        val trimmed = value.trim().trimEnd('/')
        return if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) trimmed else "http://$trimmed"
    }

    private fun postForm(path: String, backendUrl: String, params: List<Pair<String, String>>, timeout: Int = 30 * 60 * 1000, onResult: (String) -> Unit) {
        Thread {
            try {
                val body = params.joinToString("&") { (key, value) -> "${URLEncoder.encode(key, "UTF-8")}=${URLEncoder.encode(value, "UTF-8")}" }
                val connection = (URL("${normalizedUrl(backendUrl)}$path").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    doOutput = true
                    connectTimeout = 5000
                    readTimeout = timeout
                    setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
                }
                connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
                val code = connection.responseCode
                val stream = if (code in 200..299) connection.inputStream else connection.errorStream
                val response = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                connection.disconnect()
                val message = if (code in 200..299) {
                    if (path == "/generate-story") {
                        if (response.contains("\"narration_enabled\":true")) "📖 Hikâye videosu hazır • Türkçe seslendirme + sahneler + watermark"
                        else "📖 Hikâye videosu hazır • seslendirme motoru bulunamadı"
                    } else if (response.contains("\"uploaded\":true")) "Video hazırlandı ve YouTube'a yüklendi."
                    else "Video başarıyla oluşturuldu."
                } else "Motor hatası ($code): ${response.take(500)}"
                runOnUiThread { onResult(message) }
            } catch (e: Exception) {
                runOnUiThread { onResult("Bağlantı hatası: ${e.message ?: "PC motoruna ulaşılamadı"}") }
            }
        }.start()
    }

    private fun checkConnection(backendUrl: String, onResult: (String) -> Unit) {
        Thread {
            try {
                val connection = (URL("${normalizedUrl(backendUrl)}/health").openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = 5000
                    readTimeout = 5000
                }
                val code = connection.responseCode
                val response = connection.inputStream.bufferedReader().use { it.readText() }
                connection.disconnect()
                runOnUiThread { onResult(if (code in 200..299 && response.contains("\"ok\":true")) "🟢 PC AI motoru bağlı ve hazır" else "🔴 Motor hazır değil (HTTP $code)") }
            } catch (e: Exception) {
                runOnUiThread { onResult("🔴 Bağlantı kurulamadı: ${e.message ?: "PC motoruna ulaşılamadı"}") }
            }
        }.start()
    }

    @Composable
    private fun AivideoApp() {
        var mode by remember { mutableStateOf("Shorts") }
        var topic by remember { mutableStateOf("") }
        var template by remember { mutableStateOf("Hayırlı Cumalar") }
        var duration by remember { mutableStateOf("30 sn") }
        var storyMinutes by remember { mutableStateOf("15 dk") }
        var musicEnabled by remember { mutableStateOf(true) }
        var watermarkEnabled by remember { mutableStateOf(true) }
        var youtubeEnabled by remember { mutableStateOf(true) }
        var title by remember { mutableStateOf("") }
        var description by remember { mutableStateOf("") }
        var tags by remember { mutableStateOf("islam, hadis, ayet, dua, islami söz, shorts") }
        var privacy by remember { mutableStateOf("Özel") }
        var backendUrl by remember { mutableStateOf("http://192.168.1.91:8000") }
        var busy by remember { mutableStateOf(false) }
        var checking by remember { mutableStateOf(false) }
        var connectionStatus by remember { mutableStateOf("") }
        var status by remember { mutableStateOf("") }

        MaterialTheme(colorScheme = darkColorScheme()) {
            Surface(Modifier.fillMaxSize()) {
                Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                        Column { Text("Aivideo", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold); Text("İslami Video Studio", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                        Surface(shape = RoundedCornerShape(50), color = MaterialTheme.colorScheme.surfaceVariant) { Text("ÜCRETSİZ AI", modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp), style = MaterialTheme.typography.labelSmall) }
                    }
                    Box(Modifier.fillMaxWidth().height(150.dp).clip(RoundedCornerShape(28.dp)).background(Brush.linearGradient(listOf(Color(0xFF173B35), Color(0xFF0E2220)))).padding(22.dp)) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) { Text(if (mode == "Hikâye") "Uzun hikâyeni videoya dönüştür" else "Bugünün mesajını videoya dönüştür", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold); Text(if (mode == "Hikâye") "Qwen3 senaryoyu yazar, sahnelere böler, Pexels görüntülerini ve yerel seslendirmeyi hazırlar." else "Ayet, hadis, dua veya İslami söz seç; gerisini stüdyo hazırlasın.", color = Color(0xFFD0DED9)) }
                    }
                    Text("Video türü", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        FilterChip(selected = mode == "Shorts", onClick = { mode = "Shorts" }, label = { Text("⚡ Shorts") })
                        FilterChip(selected = mode == "Hikâye", onClick = { mode = "Hikâye" }, label = { Text("📖 15–20 dk Hikâye") })
                    }
                    OutlinedTextField(value = topic, onValueChange = { topic = it }, modifier = Modifier.fillMaxWidth(), label = { Text(if (mode == "Hikâye") "Hikâye konusu" else "Video konusu") }, placeholder = { Text(if (mode == "Hikâye") "Örn. Hz. Yusuf'un sabrı ve affetmesi" else "Örn. Sabır ve tevekkül") }, minLines = 2, shape = RoundedCornerShape(18.dp))

                    if (mode == "Hikâye") {
                        Card(shape = RoundedCornerShape(22.dp)) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                Text("Hikâye ayarları", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                Text("Uzun format • sahne sahne • 16:9 YouTube videosu", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    listOf("15 dk", "20 dk").forEach { item -> FilterChip(selected = storyMinutes == item, onClick = { storyMinutes = item }, label = { Text(item) }) }
                                }
                                HorizontalDivider()
                                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) { Column(Modifier.weight(1f)) { Text("Arka plan müziği"); Text("Yerel müzik", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }; Switch(checked = musicEnabled, onCheckedChange = { musicEnabled = it }) }
                                HorizontalDivider()
                                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) { Column(Modifier.weight(1f)) { Text("Islamic Horizon watermark"); Text("Alt sağda zarif logo", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }; Switch(checked = watermarkEnabled, onCheckedChange = { watermarkEnabled = it }) }
                            }
                        }
                        Text("🎙️ Seslendirme: PC'deki yerel TTS (pyttsx3/Windows sesi) bulunursa otomatik kullanılır.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else {
                        Text("Şablon", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) { listOf("Hayırlı Cumalar", "Hadis", "Ayet").forEach { item -> FilterChip(selected = template == item, onClick = { template = item }, label = { Text(item) }) } }
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) { listOf("Dua", "İslami Söz", "Normal Söz").forEach { item -> FilterChip(selected = template == item, onClick = { template = item }, label = { Text(item) }) } }
                        Card(shape = RoundedCornerShape(22.dp)) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                Text("Video ayarları", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { listOf("15 sn", "30 sn", "60 sn").forEach { item -> FilterChip(selected = duration == item, onClick = { duration = item }, label = { Text(item) }) } }
                                HorizontalDivider()
                                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) { Text("Arka plan müziği"); Switch(checked = musicEnabled, onCheckedChange = { musicEnabled = it }) }
                                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) { Text("Islamic Horizon watermark"); Switch(checked = watermarkEnabled, onCheckedChange = { watermarkEnabled = it }) }
                            }
                        }
                        Card(shape = RoundedCornerShape(22.dp)) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) { Text("YouTube", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold); Switch(checked = youtubeEnabled, onCheckedChange = { youtubeEnabled = it }) }
                                OutlinedTextField(title, { title = it }, Modifier.fillMaxWidth(), label = { Text("Video başlığı") }, shape = RoundedCornerShape(14.dp))
                                OutlinedTextField(description, { description = it }, Modifier.fillMaxWidth(), label = { Text("Açıklama") }, minLines = 2, shape = RoundedCornerShape(14.dp))
                                OutlinedTextField(tags, { tags = it }, Modifier.fillMaxWidth(), label = { Text("Etiketler") }, shape = RoundedCornerShape(14.dp))
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { listOf("Özel", "Liste dışı", "Herkese açık").forEach { item -> FilterChip(selected = privacy == item, onClick = { privacy = item }, label = { Text(item) }) } }
                            }
                        }
                    }

                    Card(shape = RoundedCornerShape(20.dp)) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("PC AI Motoru", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text("Qwen3 • Pexels • FFmpeg • yerel TTS", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            OutlinedTextField(value = backendUrl, onValueChange = { backendUrl = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Motor adresi") }, singleLine = true, shape = RoundedCornerShape(14.dp))
                            Button(enabled = !checking, onClick = { checking = true; connectionStatus = "⏳ Kontrol ediliyor…"; checkConnection(backendUrl) { checking = false; connectionStatus = it } }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp)) { Text(if (checking) "Kontrol ediliyor…" else "🔌 BAĞLANTIYI KONTROL ET") }
                            if (connectionStatus.isNotBlank()) Text(connectionStatus, fontWeight = FontWeight.SemiBold)
                        }
                    }
                    if (status.isNotBlank()) Text(status, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Button(enabled = !busy, onClick = {
                        if (topic.isBlank()) { status = "⚠️ Önce bir konu yaz kanka."; return@Button }
                        busy = true
                        if (mode == "Hikâye") {
                            val minutes = storyMinutes.filter { it.isDigit() }
                            status = "📖 Qwen3 hikâyeyi yazıyor, sahneler hazırlanıyor ve video render ediliyor… Bu işlem uzun sürebilir."
                            postForm("/generate-story", backendUrl, listOf("topic" to topic, "minutes" to minutes, "music_enabled" to musicEnabled.toString(), "watermark_enabled" to watermarkEnabled.toString()), 45 * 60 * 1000) { result -> busy = false; status = result; Toast.makeText(this@MainActivity, result, Toast.LENGTH_LONG).show() }
                        } else {
                            val seconds = duration.filter { it.isDigit() }
                            val privacyValue = when (privacy) { "Herkese açık" -> "public"; "Liste dışı" -> "unlisted"; else -> "private" }
                            status = "⚡ Shorts hazırlanıyor…"
                            postForm("/generate-and-upload", backendUrl, listOf("topic" to topic, "template" to template, "duration" to seconds, "music_enabled" to musicEnabled.toString(), "watermark_enabled" to watermarkEnabled.toString(), "youtube_enabled" to youtubeEnabled.toString(), "title" to title, "description" to description, "tags" to tags, "privacy_status" to privacyValue)) { result -> busy = false; status = result; Toast.makeText(this@MainActivity, result, Toast.LENGTH_LONG).show() }
                        }
                    }, modifier = Modifier.fillMaxWidth().height(58.dp), shape = RoundedCornerShape(18.dp)) { Text(if (busy) "⏳  HAZIRLANIYOR…" else if (mode == "Hikâye") "📖  HİKÂYE VİDEOSU OLUŞTUR" else "✦  AI İLE SHORTS OLUŞTUR", fontWeight = FontWeight.Bold) }
                    Text("Ollama • Qwen3 • Pexels • FFmpeg • Local TTS • YouTube", modifier = Modifier.fillMaxWidth(), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
