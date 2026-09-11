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

    private fun runEngine(
        backendUrl: String,
        topic: String,
        template: String,
        duration: String,
        musicEnabled: Boolean,
        watermarkEnabled: Boolean,
        youtube: Boolean,
        title: String,
        description: String,
        tags: String,
        privacy: String,
        onResult: (String) -> Unit
    ) {
        Thread {
            try {
                val seconds = duration.filter { it.isDigit() }
                val privacyValue = when (privacy) {
                    "Herkese açık" -> "public"
                    "Liste dışı" -> "unlisted"
                    else -> "private"
                }
                val params = listOf(
                    "topic" to topic,
                    "template" to template,
                    "duration" to seconds,
                    "music_enabled" to musicEnabled.toString(),
                    "watermark_enabled" to watermarkEnabled.toString(),
                    "youtube_enabled" to youtube.toString(),
                    "title" to title,
                    "description" to description,
                    "tags" to tags,
                    "privacy_status" to privacyValue
                ).joinToString("&") { (key, value) ->
                    "${URLEncoder.encode(key, "UTF-8")}=${URLEncoder.encode(value, "UTF-8")}"
                }
                val url = URL("${backendUrl.trimEnd('/')}/generate-and-upload")
                val connection = (url.openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    doOutput = true
                    connectTimeout = 5000
                    readTimeout = 15 * 60 * 1000
                    setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
                }
                connection.outputStream.use { it.write(params.toByteArray(Charsets.UTF_8)) }
                val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
                val response = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                val message = if (connection.responseCode in 200..299) {
                    if (response.contains("\"uploaded\":true")) "Video hazırlandı ve YouTube'a yüklendi."
                    else if (response.contains("\"watermark_enabled\":true")) "Video hazırlandı • Islamic Horizon watermark eklendi."
                    else if (response.contains("\"music_enabled\":true")) "Video hazırlandı • müzik eklendi."
                    else "Video başarıyla oluşturuldu."
                } else {
                    "Motor hatası (${connection.responseCode}): ${response.take(220)}"
                }
                connection.disconnect()
                runOnUiThread { onResult(message) }
            } catch (e: Exception) {
                runOnUiThread { onResult("Bağlantı hatası: ${e.message ?: "PC motoruna ulaşılamadı"}") }
            }
        }.start()
    }

    @Composable
    private fun AivideoApp() {
        var topic by remember { mutableStateOf("") }
        var selected by remember { mutableStateOf("Hayırlı Cumalar") }
        var duration by remember { mutableStateOf("30 sn") }
        var musicEnabled by remember { mutableStateOf(true) }
        var watermarkEnabled by remember { mutableStateOf(true) }
        var youtubeEnabled by remember { mutableStateOf(true) }
        var title by remember { mutableStateOf("") }
        var description by remember { mutableStateOf("") }
        var tags by remember { mutableStateOf("islam, hadis, ayet, dua, islami söz, shorts") }
        var privacy by remember { mutableStateOf("Özel") }
        var backendUrl by remember { mutableStateOf("http://192.168.1.100:8000") }
        var busy by remember { mutableStateOf(false) }
        var statusMessage by remember { mutableStateOf("") }

        MaterialTheme(colorScheme = darkColorScheme()) {
            Surface(Modifier.fillMaxSize()) {
                Column(
                    Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp, vertical = 22.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("Aivideo", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
                            Text("İslami Shorts Studio", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Surface(shape = RoundedCornerShape(50), color = MaterialTheme.colorScheme.surfaceVariant) {
                            Text("ÜCRETSİZ AI", modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp), style = MaterialTheme.typography.labelSmall)
                        }
                    }

                    Box(
                        modifier = Modifier.fillMaxWidth().height(150.dp).clip(RoundedCornerShape(28.dp))
                            .background(Brush.linearGradient(listOf(Color(0xFF173B35), Color(0xFF0E2220))))
                            .padding(22.dp)
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Bugünün mesajını videoya dönüştür", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                            Text("Ayet, hadis, dua veya İslami söz seç; gerisini stüdyo hazırlasın.", color = Color(0xFFD0DED9))
                        }
                    }

                    Text("Yeni Video", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    OutlinedTextField(value = topic, onValueChange = { topic = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Video konusu") }, placeholder = { Text("Örn. Sabır ve tevekkül") }, minLines = 2, shape = RoundedCornerShape(18.dp))

                    Text("Şablon", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("Hayırlı Cumalar", "Hadis", "Ayet").forEach { item -> FilterChip(selected = selected == item, onClick = { selected = item }, label = { Text(item) }) }
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("Dua", "İslami Söz", "Normal Söz").forEach { item -> FilterChip(selected = selected == item, onClick = { selected = item }, label = { Text(item) }) }
                    }

                    Card(shape = RoundedCornerShape(22.dp)) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Text("Video ayarları", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                                Column { Text("Süre"); Text("Dikey Shorts • 1080×1920", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    listOf("15 sn", "30 sn", "60 sn").forEach { item -> FilterChip(selected = duration == item, onClick = { duration = item }, label = { Text(item) }) }
                                }
                            }
                            HorizontalDivider()
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                                Column { Text("Arka plan müziği"); Text("Yerel müzik / ACE-Step hazırsa kullan", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                                Switch(checked = musicEnabled, onCheckedChange = { musicEnabled = it })
                            }
                            HorizontalDivider()
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                                Column(Modifier.weight(1f)) {
                                    Text("Islamic Horizon watermark", fontWeight = FontWeight.SemiBold)
                                    Text("Her videonun alt sağında zarif logo", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                                Switch(checked = watermarkEnabled, onCheckedChange = { watermarkEnabled = it })
                            }
                        }
                    }

                    Card(shape = RoundedCornerShape(22.dp)) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                                Column {
                                    Text("YouTube", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                    Text("Video hazır olunca kanalına yükle", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                                Switch(checked = youtubeEnabled, onCheckedChange = { youtubeEnabled = it })
                            }
                            OutlinedTextField(title, { title = it }, Modifier.fillMaxWidth(), label = { Text("Video başlığı") }, placeholder = { Text("AI başlığı otomatik de oluşturabilir") }, shape = RoundedCornerShape(14.dp))
                            OutlinedTextField(description, { description = it }, Modifier.fillMaxWidth(), label = { Text("Açıklama") }, minLines = 3, shape = RoundedCornerShape(14.dp))
                            OutlinedTextField(tags, { tags = it }, Modifier.fillMaxWidth(), label = { Text("Etiketler") }, placeholder = { Text("virgülle ayır") }, shape = RoundedCornerShape(14.dp))
                            Text("Yayın durumu", style = MaterialTheme.typography.labelLarge)
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                listOf("Özel", "Liste dışı", "Herkese açık").forEach { item -> FilterChip(selected = privacy == item, onClick = { privacy = item }, label = { Text(item) }) }
                            }
                            Text("İlk bağlantıda Google hesabınla YouTube izni verilecek.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }

                    Card(shape = RoundedCornerShape(20.dp)) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("PC AI Motoru", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text("Qwen3 + çoklu Pexels sahne + FFmpeg + YouTube", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            OutlinedTextField(value = backendUrl, onValueChange = { backendUrl = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Motor adresi") }, placeholder = { Text("http://PC-IP:8000") }, singleLine = true, shape = RoundedCornerShape(14.dp))
                        }
                    }

                    if (statusMessage.isNotBlank()) Text(statusMessage, modifier = Modifier.fillMaxWidth(), color = MaterialTheme.colorScheme.onSurfaceVariant)

                    Button(
                        enabled = !busy,
                        onClick = {
                            busy = true
                            statusMessage = "AI motoru çalışıyor… Qwen3 sahneleri planlıyor, görüntüler seçiliyor ve Shorts render ediliyor."
                            runEngine(backendUrl, topic, selected, duration, musicEnabled, watermarkEnabled, youtubeEnabled, title, description, tags, privacy) { result ->
                                busy = false
                                statusMessage = result
                                Toast.makeText(this@MainActivity, result, Toast.LENGTH_LONG).show()
                            }
                        },
                        modifier = Modifier.fillMaxWidth().height(58.dp), shape = RoundedCornerShape(18.dp)
                    ) {
                        Text(if (busy) "⏳  VİDEO HAZIRLANIYOR…" else "✦  AI İLE VİDEO OLUŞTUR", fontWeight = FontWeight.Bold)
                    }
                    OutlinedButton(onClick = { }, modifier = Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(18.dp)) { Text("Videolarım") }
                    Text("Ollama • Pexels • ComfyUI • Piper • Whisper • FFmpeg • YouTube", modifier = Modifier.fillMaxWidth(), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
