package com.hakki37.aivideo

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
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
    Surface(Modifier.fillMaxSize()) {
        Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Text("Aivideo", style = MaterialTheme.typography.headlineLarge)
            Text("Ücretsiz AI İslami Shorts Studio", style = MaterialTheme.typography.titleMedium)
            Text("Yeni Video", style = MaterialTheme.typography.headlineSmall)
            OutlinedTextField(topic, { topic = it }, Modifier.fillMaxWidth(), label = { Text("Konu") }, placeholder = { Text("Örn. Sabır ve tevekkül") }, minLines = 3)
            Text("Şablon", style = MaterialTheme.typography.titleMedium)
            listOf("Hayırlı Cumalar", "Hadis", "Ayet", "Dua", "İslami Söz").forEach { item ->
                FilterChip(selected = selected == item, onClick = { selected = item }, label = { Text(item) })
            }
            Button(onClick = {}, Modifier.fillMaxWidth()) { Text("AI ile Video Oluştur") }
            Text("9:16 • 1080×1920 • MP4")
            Text("Ollama • ComfyUI • Piper • Whisper • FFmpeg", style = MaterialTheme.typography.bodySmall)
        }
    }
}
