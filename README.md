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
- [x] **Fase 1** — Tools dasar sistem: `run_command()` dengan whitelist aman (`journalctl`, `systemctl status`), `check_updates()` pakai pacman, loop detection
- [ ] **Fase 2** — Update handling: `get_changelog()`, `snapshot_config()`, `diff_config_after_update()` untuk nanganin breaking changes rolling release
- [ ] **Fase 3** — RAG: index "war story" (histori fix udev rules, Hyprland 0.56 breaking changes, Waybar dobel bug) ke vector db
- [ ] **Fase 4** — Auto-fix dengan approval flow (y/n) sebelum eksekusi apapun
- [ ] **Fase 5** — Showcase: README lengkap, commit history rapi, deploy versi kecil ke cloud

## Status Saat Ini

Fase 1 selesai. Agent sekarang punya 3 tools: `read_file`, `run_command` (whitelist ketat, read-only), dan `check_updates` (pacman -Qu). Beberapa safety layer sudah diterapkan:

- **Whitelist command**, bukan blacklist — command dan subcommand harus eksplisit diizinkan
- **Tidak ada `shell=True`** — command dijalankan sebagai list argumen, terbukti menahan percobaan command injection (`journalctl -xe; rm -rf ~` ditolak)
- **Safety net level kode** — kata kunci destruktif (restart, install, remove, dll) langsung ditolak sebelum masuk ke model, tidak bergantung 100% pada kepatuhan model
- **Loop detection** — agent berhenti otomatis kalau mencoba memanggil action yang identik berulang kali
- **Fallback format** — kalau model gagal mengikuti format ReAct 2x berturut-turut, agent berhenti 

**Fase 2 :**
- `snapshot_config` — backup folder `~/.config/hypr/` dengan timestamp sebelum update
- `list_snapshots` — lihat daftar snapshot yang pernah dibuat
- `diff_config_after_update` — bandingkan config saat ini dengan snapshot, tampilkan
  perubahan (file baru/hilang + diff isi file)
- `get_changelog` — cek breaking changes/pengumuman dari Arch Linux News (RSS,
  domain di-whitelist)



### Known Limitations

- Model (`qwen2.5-coder:1.5b`) kadang menambahkan detail kecil yang tidak akurat di narasi jawaban akhir (misal mengklaim "menyimpan log ke file" padahal tool hanya menampilkan output) meski action yang dijalankan sendiri tetap aman dan sesuai whitelist. Ini kandidat kuat untuk diperbaiki lewat RAG di Fase 3, atau evaluasi upgrade model di fase-fase mendatang jika kompleksitas tool bertambah signifikan.
- Prompt disengaja dijaga pendek (3-4 contoh few-shot) karena model kecil ini cenderung "melanjutkan pola" contoh yang terlalu banyak alih-alih mengikuti instruksi.
- Model kecil (1.5b) cenderung menjawab dari asumsi/pengetahuan umum alih-alih memverifikasi lewat tool, khususnya untuk pertanyaan follow-up atau ambigu. Mitigasi saat ini: instruksi eksplisit "wajib verifikasi" ditambahkan per-tool berdasarkan temuan testing manual.
- Model (`qwen2.5-coder:1.5b`) kadang menjawab pertanyaan follow-up atau pertanyaan
  yang terdengar "umum" (misal "ada yang perlu diwaspadai sebelum update?") dari
  asumsi/pengetahuan umum, alih-alih memanggil tool yang tersedia untuk verifikasi
  data aktual — meski instruksi eksplisit sudah ditambahkan ("tool selalu didahulukan
  dibanding jawaban dari ingatan"). Sudah dicoba 2 pendekatan (instruksi spesifik
  per-tool, lalu instruksi general di seluruh prompt), hasilnya konsisten sama.
  Ini kemungkinan batas kapasitas reasoning model 1.5B untuk kasus ambigu, bukan
  masalah prompt engineering semata. Kandidat kuat untuk dievaluasi ulang di Fase 3
  (RAG bisa membantu dengan retrieval eksplisit) atau saat upgrade model
  dipertimbangkan lagi.
- Model kadang menambahkan detail kecil yang tidak akurat di narasi jawaban akhir
  meski action yang dijalankan sendiri tetap aman dan sesuai whitelist.



## Ide Pengembangan Masa Depan (belum dieksekusi)

Catatan ide yang worth dipertimbangkan di fase yang sesuai, bukan komitmen langsung:

- **Plugin/Tool Registry structure** — refactor `tools.py` jadi folder `plugins/` per kategori (pacman, systemd, docker, dll) begitu jumlah tools mulai banyak. Kandidat untuk Fase 5 (showcase), setelah Fase 1-4 selesai dan kebutuhan tool sudah jelas — bukan sekarang, karena migrasi struktur di tengah jalan cuma nambah kerjaan tanpa nambah kapabilitas.
- **Output terstruktur (JSON) dari tools** — daripada tool selalu return raw string, beberapa tool (terutama `check_updates` dan turunannya di Fase 2) bisa return data terstruktur biar lebih konsisten dibaca model. Dieval ulang saat mulai kerasa perlu.
- **Approval flow [Y/N] sebelum eksekusi** — sudah jadi rencana di Fase 4, tidak ada perubahan.

Ide lain (Docker manager, Snapshot/Snapper, notifikasi Telegram/Discord, web dashboard, voice assistant) sengaja belum masuk roadmap karena di luar scope inti Ziggy saat ini (fokus: diagnosis & handling breaking changes CachyOS). Bisa dipertimbangkan lagi kalau versi inti sudah stabil dan mau diperluas.

## Model Evaluation 
Model yg gua pakai yaitu qwen2.5-coder:1.5b memiliki banyak kekurangan mulai dari ngaco dalam memberikan hasil (halunisai format), ga belajar dari war history. Kemudian gua coba model lain yaitu qwen2.5-coder:3b dengan membandingkan dalam war history, pengambilan tools, kecepatan

## Ada Beberapa analisis yg bisa gua dapetin 

Soal akurasi tool-selection: 3b menang jelas di Test 2 dia beneran manggil tool yang tepat, sementara 1.5b nulis nama tool sebagai teks doang (halusinasi murni). Test 5 di 1.5b juga nunjukkin gejala serupa kayak Action dan Final Answer nempel dalam 1 output

Soal loop-repetition: ini yang menarik, dua-duanya sama-sama bisa ngulang command yang identik. Ini konfirmasi penting: safety net seen_actions itu emang krusial di kedua model, bukan cuma nambal buat 1.5b doang. Jangan pernah anggap upgrade model bakal "menghilangkan kebutuhan" safety net level kode keduanya tetap perlu.

Soal kecepatan: 3b konsisten ~1.5-2.5x lebih lambat (24-31s vs 11-19s buat query yang butuh tool call). Test 6 jadi pengecualian bagus (6.5s, karena cuma 1x panggil bersih).

## Kesimpulan Saat Ini 
Berdasarkan data ini, 3b sedikit lebih baik dari sisi tool-selection accuracy (terutama Test 2), tapi:

 - Trade-off kecepatan nyata (~2x lebih lambat)
 - Bug loop-repetition masih ada di 3b juga — jadi bukan solusi ajaib
 - Selisih akurasi cuma keliatan jelas di 1 dari 6 test, sisanya setara

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
