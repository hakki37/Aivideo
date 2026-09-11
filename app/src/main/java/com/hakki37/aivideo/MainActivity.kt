package com.hakki37.aivideo

import android.os.Bundle
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

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { AivideoApp() }
    }
}

@Composable
fun AivideoApp() {
    var topic by remember { mutableStateOf("") }
    var selected by remember { mutableStateOf("Hayırlı Cumalar") }
    var duration by remember { mutableStateOf("30 sn") }
    var musicEnabled by remember { mutableStateOf(true) }

    MaterialTheme(colorScheme = darkColorScheme()) {
        Surface(Modifier.fillMaxSize()) {
            Column(
                Modifier.fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 18.dp, vertical = 22.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
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

                OutlinedTextField(
                    value = topic,
                    onValueChange = { topic = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Video konusu") },
                    placeholder = { Text("Örn. Sabır ve tevekkül") },
                    minLines = 2,
                    shape = RoundedCornerShape(18.dp)
                )

                Text("Şablon", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("Hayırlı Cumalar", "Hadis", "Ayet").forEach { item ->
                        FilterChip(selected = selected == item, onClick = { selected = item }, label = { Text(item) })
                    }
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("Dua", "İslami Söz").forEach { item ->
                        FilterChip(selected = selected == item, onClick = { selected = item }, label = { Text(item) })
                    }
                }

                Card(shape = RoundedCornerShape(22.dp)) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text("Video ayarları", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                            Column { Text("Süre"); Text("Dikey Shorts • 1080×1920", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                listOf("15 sn", "30 sn", "60 sn").forEach { item ->
                                    FilterChip(selected = duration == item, onClick = { duration = item }, label = { Text(item) })
                                }
                            }
                        }
                        HorizontalDivider()
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                            Column { Text("Arka plan müziği"); Text("İlahi / ney tarzı", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            Switch(checked = musicEnabled, onCheckedChange = { musicEnabled = it })
                        }
                    }
                }

                Button(
                    onClick = { },
                    modifier = Modifier.fillMaxWidth().height(58.dp),
                    shape = RoundedCornerShape(18.dp)
                ) {
                    Text("✦  AI İLE VİDEO OLUŞTUR", fontWeight = FontWeight.Bold)
                }

                OutlinedButton(
                    onClick = { },
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(18.dp)
                ) { Text("Videolarım") }

                Text(
                    "Ollama • Pexels • ComfyUI • Piper • Whisper • FFmpeg",
                    modifier = Modifier.fillMaxWidth(),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
