## Ziggy 🐧

AI agent lokal untuk bantu system administration di CachyOS/Hyprland, jalan sepenuhnya offline pakai Ollama, tanpa API eksternal.

## Buat Apa Ziggy?

CachyOS itu rolling release — breaking changes bisa muncul kapan aja tiap update mingguan (Hyprland syntax berubah, Waybar tiba-tiba dobel instance, udev rules butuh disesuaikan ulang, dll). Ziggy dibangun buat jadi asisten yang paham konteks sistem sendiri: baca config, baca log, dan (nantinya) belajar dari "war story" fix-fix yang pernah gua lakuin, biar bisa bantu diagnosis masalah serupa di masa depan.

Project ini juga semoga jadi portofolio utama gua menuju AI/ML Engineer, fokus ke pola ReAct (Reasoning + Acting), tool calling, dan RAG.

## Stack

- **Ollama** — jalanin LLM lokal
- **Model**: `qwen2.5-coder:1.5b` (RAM issue, nanti kedepannya coba pakai model yg lebih besar)
- **Python** — loop ReAct + tools
- **Chroma** (rencana Fase 3) — vector DB buat RAG

## Struktur
ziggy/
├── agent.py # loop ReAct utama
├── tools.py # kumpulan tools yang bisa dipanggil agent
└── config.py # setting model, host, max iterations

## Prinsip Desain

- **Security dulu**: tidak ada `shell=True`, validasi path pakai `Path.resolve()` + `is_relative_to()`, whitelist command ketat untuk semua tool yang berinteraksi dengan sistem
- **Kejujuran atas keterbatasan**: agent didesain untuk mengakui ketika sebuah kemampuan belum tersedia, bukan mencoba tool acak atau mengarang hasil eksekusi
- **Progress bertahap**: tiap fase punya bukti konkret sebelum lanjut ke fase berikutnya

## Roadmap

- [x] **Fase 0** — Setup dasar: ReAct loop sederhana + tool `read_file()`
- [ ] **Fase 1** — Tools dasar sistem: `run_command()` dengan whitelist aman (`journalctl`, `systemctl status`), `check_updates()` pakai pacman, loop detection
- [ ] **Fase 2** — Update handling: `get_changelog()`, `snapshot_config()`, `diff_config_after_update()` untuk nanganin breaking changes rolling release
- [ ] **Fase 3** — RAG: index "war story" (histori fix udev rules, Hyprland 0.56 breaking changes, Waybar dobel bug) ke vector db
- [ ] **Fase 4** — Auto-fix dengan approval flow (y/n) sebelum eksekusi apapun
- [ ] **Fase 5** — Showcase: README lengkap, commit history rapi, deploy versi kecil ke cloud

## Status Saat Ini

Fase 0 selesai. ReAct loop stabil: model bisa memilih antara memanggil tool atau menjawab langsung, tidak lagi mengarang isi file maupun hasil eksekusi tool yang tidak ada, dan validasi path berhasil menahan percobaan path traversal (`/etc/passwd` ditolak).

## Jalanin Sendiri

```bash
# Pastikan Ollama sudah jalan dan model sudah di-pull
ollama pull qwen2.5-coder:1.5b

# Clone & jalankan
git clone https://github.com/ddimzuu-source/ziggy.git
cd ziggy
python -m venv venv
source venv/bin/activate.fish  # sesuaikan dengan shell 
pip install requests

python agent.py # command
```
