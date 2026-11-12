# Database Kode Pos Jepang — HTML + GitHub Pages

Website **static** untuk mencari kode pos Jepang (`0000000` sampai `9999999`), tanpa MySQL, PHP, server, paket npm, atau proses Python di komputer Anda.

**Sumber:** Japan Post (kode pos wilayah + kode pos khusus perusahaan/instansi). Database **tidak disertakan dalam ZIP ini**; database secara otomatis diunduh, diperiksa, dipecah, dan di-deploy oleh GitHub Actions saat pertama kali deploy. Proses diperbarui otomatis setiap tanggal 5 tiap bulan.

## Instalasi ke GitHub Pages

1. Buat repository publik baru di GitHub, misalnya `japan-postcode`.
2. **Upload seluruh isi folder** ini ke repository pada branch `main` (jangan mengunggah ZIP sebagai satu file). Pastikan `.github/workflows/deploy.yml` ikut terunggah.
3. Buka **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Buka tab **Actions** → workflow **Build postal-code database and deploy Pages** → **Run workflow**, jika workflow belum otomatis berjalan ketika file di-push.
5. Tunggu status workflow berubah **hijau (Success)**, kemudian klik alamat situs di bagian **Deployments** atau **Settings → Pages**.

URL tipikal: `https://USERNAME.github.io/japan-postcode/` (sesuaikan username dan repo).

**Penting:** Alamat baru tersedia setelah workflow selesai. Jika muncul error, buka tab **Actions → Build postal-code database and deploy Pages → job gagal** dan salin bagian log berwarna merah.

## Cara kerja

- Pencarian terjadi sesudah pengguna mengetik 7 digit.
- Hanya satu file `data/XYZ.json` sesuai tiga digit awal yang diunduh (contoh `data/100.json`).
- Browser meng-cache JSON prefiks selama sesi tab dibuka.
- Kode pos `001` dan awalan nol lain diperlakukan sebagai **teks**, bukan angka.
- Alamat umum berisi **prefektur, kota/kabupaten dan wilayah**; kode pos khusus instansi juga dapat menampilkan **nama instansi dan blok/detail** yang dicatat oleh Japan Post.
- Nomor rumah/apartemen/ruangan milik pengguna **tidak dapat disimpulkan dari kode pos**; harus diisi sendiri.
- Bila kode pos punya beberapa alamat, pengguna dapat memilih hasil yang sesuai.

### Struktur JSON

`data/100.json` kurang lebih seperti:

```json
{
  "0001": [["東京都", "千代田区", "千代田"]],
  "8798": [["東京都", "千代田区", "霞が関", "日本郵便株式会社", "一丁目3-2", "office"]]
}
```

Ini contoh skema, **bukan** isi data resmi yang dijamin cocok untuk nilai contoh tersebut.

Format:
- Key: **4 digit terakhir** dari kode pos.
- Nilai: daftar alamat yang berlaku untuk kode pos itu.
- Alamat biasa `[prefektur,kota,wilayah]`.
- Alamat instansi `[prefektur,kota,wilayah,nama_instansi,detail,"office"]`.

## Perbarui data manual

Di tab **Actions** klik **Build postal-code database and deploy Pages** lalu **Run workflow**. Secara default diperbarui otomatis **tanggal 5 tiap bulan (UTC)**.

## Data source & reliability

- Official Japan Post UTF-8 general zip: https://www.post.japanpost.jp/service/search/zipcode/download/utf/zip/utf_ken_all.zip
- Official Japan Post office zip: https://www.post.japanpost.jp/service/search/zipcode/download/office/zip/jigyosyo.zip
- Mirror fallback: https://github.com/hiroyuki-komatsu/japanpost_zipcode

Workflow mencoba sumber resmi lebih dulu, lalu mirror. Jika kedua sumber gagal, deployment gagal agar situs tidak diam-diam memakai data tak lengkap; **deployment sebelumnya tetap tersedia**.

## Tes lokal (opsional, tidak diperlukan untuk deploy)

`python scripts/build_data.py --out public` lalu jalankan `python -m http.server 8000 --directory public` dan buka `http://localhost:8000/`.

### Lainnya

- GitHub Actions membutuhkan repository Actions aktif dan GitHub Pages source diset ke GitHub Actions.
- GitHub Pages punya batas pemakaian dan tidak menyediakan jaminan uptime.
- Dataset memuat *postal-level towns/areas*, bukan setiap nomor rumah, dan bukan data lokasi pribadi.
- Tidak ada kode yang mengumpulkan data input pengguna ke server lain; hanya meminta JSON dari domain situs GitHub Pages yang sama.
