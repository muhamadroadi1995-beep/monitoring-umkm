# Dashboard UMKM — Website status + Python di PC (tanpa SQL)

Paket ini sesuai rancangan:
- Website statis di Render Static Site, tetap bisa dibuka dari HP.
- Python FastAPI berjalan di PC Windows 11 melalui terminal VS Code.
- Cloudflare Tunnel menghubungkan website ke Python di PC.
- Website memeriksa `/health` setiap 3 detik.
- Jika PC/Python/tunnel tidak bisa dihubungi, website tetap terbuka dan menampilkan **SERVER OFFLINE**.
- Tidak memakai SQL, database, penyimpanan data, login admin, Playwright, Faker, pyngrok, maupun integrasi/pengiriman data ke situs BRI.

> Catatan cakupan: versi ini khusus halaman status server. Fitur login admin dan pengelolaan data tidak disertakan karena permintaan terakhir adalah website yang hanya menampilkan status online/offline. Tidak ada data yang disimpan.

## Struktur folder

```text
dashboard_umkm_status/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── render.yaml
└── static/
    ├── index.html
    └── config.js
```

## A. Jalankan Python di Windows 11

1. Install Python 3.11+ dan VS Code.
2. Buka folder proyek ini di VS Code.
3. Buka Terminal > New Terminal (PowerShell).
4. Jalankan:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Jika PowerShell menolak aktivasi, pilih terminal Command Prompt lalu jalankan:

```cmd
.venv\Scripts\activate.bat
```

5. Jalankan server hanya pada loopback PC:

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

6. Tes di PC dengan membuka `http://127.0.0.1:8000/health`.
   Respons yang diharapkan memuat `"status":"online"`.

Biarkan terminal tetap berjalan. Jika terminal dihentikan, API Python berhenti.

## B. Buat Cloudflare Tunnel dari PC

### Cara cepat untuk uji coba (Quick Tunnel)

1. Install `cloudflared` dari dokumentasi resmi:
   https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
2. Buka terminal PowerShell baru (jangan hentikan terminal Python).
3. Jalankan:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

4. Tunggu alamat HTTPS yang berakhiran `trycloudflare.com`, misalnya `https://contoh-acak.trycloudflare.com`.
5. Salin alamat tersebut. Quick Tunnel bersifat sementara dan alamatnya dapat berubah ketika tunnel dibuat ulang.

Jangan bagikan alamat tunnel bila tidak ingin endpoint status PC diketahui publik. Endpoint ini hanya menampilkan status minimal, tidak menyediakan kontrol PC.

### Untuk penggunaan jangka panjang

Gunakan Named Tunnel dengan domain yang dikelola di Cloudflare. Ikuti panduan resmi:
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

Buat hostname khusus, misalnya `api.domain-anda.com`, dan arahkan tunnel ke `http://127.0.0.1:8000`. Jangan membuat route ke layanan lain di PC.

## C. Hubungkan website ke tunnel

1. Buka `static/config.js`.
2. Ganti nilai `API_BASE_URL` dengan alamat HTTPS tunnel yang didapat.
3. Contoh:

```javascript
window.DASHBOARD_CONFIG = {
  API_BASE_URL: "https://contoh-acak.trycloudflare.com"
};
```

4. Simpan perubahan.

## D. Deploy website ke Render Static Site

1. Buat repository GitHub untuk proyek ini. Unggah isi folder `dashboard_umkm_status`.
2. Pastikan `.env`, `.venv`, dan file rahasia tidak diunggah. File `.gitignore` sudah disediakan.
3. Masuk ke https://render.com dan pilih **New → Static Site**.
4. Hubungkan repository GitHub.
5. Atur:
   - Build Command: kosongkan
   - Publish Directory: `static`
6. Klik **Create Static Site**.
7. Render akan memberikan URL, misalnya `https://dashboard-umkm.onrender.com`.

Static Site tidak menjalankan Python. Python tetap berjalan di PC; Render hanya menyajikan HTML, CSS, dan JavaScript.

## E. Batasi akses CORS API ke website Render

Setelah mendapat URL Render, atur variabel `ALLOWED_ORIGINS` di terminal tempat menjalankan Python, lalu mulai ulang server:

```powershell
$env:ALLOWED_ORIGINS="https://dashboard-umkm.onrender.com"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Ganti URL contoh dengan URL Render milik sendiri. Jika memakai custom domain, tambahkan domain itu dipisahkan koma.

CORS membantu membatasi browser dari origin lain, tetapi bukan autentikasi dan bukan perlindungan terhadap semua jenis akses langsung. Endpoint `/health` memang dirancang publik dan hanya memberikan status minimal.

## F. Cara kerja sehari-hari

1. Nyalakan PC dan koneksi internet.
2. Jalankan Python di terminal VS Code.
3. Jalankan Cloudflare Tunnel di terminal kedua.
4. Buka website Render dari HP.
5. Website memeriksa server setiap 3 detik:
   - Python + tunnel aktif: **SERVER ONLINE**
   - Python berhenti, PC mati, atau tunnel terputus: **SERVER OFFLINE**
6. Website Render tetap dapat dibuka meskipun PC offline.

## Catatan

- Website statis tetap online, tetapi status PC hanya dapat diperbarui bila tunnel tersedia.
- Quick Tunnel dapat berubah URL; setelah URL berubah, perbarui `static/config.js` dan deploy ulang Static Site.
- PC harus tetap menyala dan tidak masuk sleep agar server dapat diakses.
- Jangan membuka port 8000 langsung ke internet. Gunakan tunnel.
- Jangan menambahkan endpoint yang menjalankan perintah sistem, mengakses file PC, mengendalikan browser, atau mengirim data ke situs eksternal.
- Versi ini tidak memuat data nasabah, data simulasi, maupun fungsi input/penyimpanan.
