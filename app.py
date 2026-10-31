import asyncio
import io
import random
import re
import ddddocr
from faker import Faker
import nest_asyncio
from PIL import Image
from playwright.async_api import async_playwright
import streamlit as st

# Izinkan penanganan event loop bersarang untuk Streamlit
nest_asyncio.apply()

# --- KONFIGURASI HALAMAN STREAMLIT ---
st.set_page_config(
    page_title="Dashboard Otomatisasi Skoring UMKM",
    page_icon="🤖",
    layout="wide",
)

# Inisialisasi OCR & Faker
fake = Faker("id_ID")
DAFTAR_SEKTOR_USAHA = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


@st.cache_resource
def load_ocr():
  return ddddocr.DdddOcr(show_ad=False)


ocr_engine = load_ocr()

# --- HELPER AUTOMATION ---


async def safe_click(page, locator, delay=1.2):
  try:
    await locator.scroll_into_view_if_needed()
    await locator.wait_for(state="visible", timeout=10000)
    await locator.click(timeout=5000)
  except Exception:
    await locator.evaluate("elem => elem.click()")

  if delay > 0:
    await asyncio.sleep(delay)


def generate_single_user(user_id, url_target):
  nik_acak = (
      "32"
      + str(random.randint(10, 99))
      + "".join([str(random.randint(0, 9)) for _ in range(12)])
  )
  telepon_acak = (
      "08"
      + str(random.randint(11, 99))
      + "".join([str(random.randint(0, 9)) for _ in range(8)])
  )
  tanggal_lahir_acak = fake.date_of_birth(
      minimum_age=25, maximum_age=60
  ).strftime("%Y-%m-%d")
  sektor_usaha_acak = random.choice(DAFTAR_SEKTOR_USAHA)

  username_clean = re.sub(r"[^a-zA-Z0-9]", "", fake.first_name().lower())
  email_gmail = f"{username_clean}{random.randint(100000, 999999)}@gmail.com"

  return {
      "id": user_id,
      "nama": fake.name(),
      "email": email_gmail,
      "telepon": telepon_acak,
      "nik": nik_acak,
      "password": "Abcd123*",
      "tanggal_lahir": tanggal_lahir_acak,
      "sektor_usaha": sektor_usaha_acak,
      "url": url_target,
  }


async def solve_captcha_ai(page):
  try:
    captcha_selectors = [
        "img[src*='captcha' i]",
        "img[src*='Captcha' i]",
        "img[src*='data:image']",
        ".captcha img",
        "#captcha_img",
        "form img",
    ]
    captcha_img = None
    for selector in captcha_selectors:
      loc = page.locator(selector).first
      if await loc.count() > 0 and await loc.is_visible():
        captcha_img = loc
        break

    if not captcha_img:
      captcha_img = page.locator("form img").first
      await captcha_img.wait_for(state="visible", timeout=10000)

    img_bytes = await captcha_img.screenshot()
    result = ocr_engine.classification(img_bytes)
    clean_text = re.sub(r"[^A-Z0-9]", "", result.upper())
    return clean_text[:5].strip()
  except Exception:
    return ""


async def isi_captcha_ke_form(page, captcha_text):
  input_selectors = [
      "input[name*='captcha' i]",
      "input[id*='captcha' i]",
      "input[placeholder*='captcha' i]",
      "input[name='sec_code']",
      "input[name='code']",
      ".captcha-input input",
  ]
  captcha_input = None
  for selector in input_selectors:
    loc = page.locator(selector).first
    if await loc.count() > 0 and await loc.is_visible():
      captcha_input = loc
      break

  if captcha_input:
    await captcha_input.click()
    await captcha_input.fill("")
    await asyncio.sleep(0.5)
    await captcha_input.press_sequentially(captcha_text, delay=200)
    await asyncio.sleep(0.5)
    await captcha_input.dispatch_event("input")
    await captcha_input.dispatch_event("change")
    await captcha_input.dispatch_event("blur")
    return True
  return False


async def proses_lanjutan_otomatis(
    context, page, user_data, jenis_mode, log_status
):
  try:
    log_status(f"Fase 2 untuk User #{user_data['id']} ({user_data['nama']})...")

    # 1. Data Diri
    tgl_input = page.get_by_placeholder("Masukkan Tanggal Lahir")
    await tgl_input.wait_for(state="visible", timeout=15000)
    await tgl_input.fill(user_data["tanggal_lahir"])

    sector_select = page.locator('select[name="business_sector"]')
    await sector_select.wait_for(state="visible")
    await sector_select.select_option(user_data["sektor_usaha"])

    await page.locator('textarea[name="produced"]').fill("ADA")
    await page.locator('textarea[name="business_address"]').fill("ADA")

    dropdowns = [
        ('select[name="province"]', "32"),
        ('select[name="regency"]', "3209"),
        ('select[name="subdistrict"]', "3209200"),
        ('select[name="village"]', "3209200017"),
        ('select[name="postal_code"]', "30325"),
    ]
    for selector, val in dropdowns:
      elem = page.locator(selector)
      await elem.wait_for(state="visible", timeout=10000)
      await elem.select_option(val)
      await asyncio.sleep(0.5)

    await page.get_by_role("radio", name="Tidak").check()
    await page.locator("#syarat").check()

    await safe_click(page, page.get_by_role("button", name="Lanjut"), delay=1)
    await safe_click(
        page, page.get_by_role("button", name="Saya Setuju"), delay=1
    )

    # 2. Mulai Skoring Sesi 1
    await safe_click(
        page, page.get_by_role("link", name="Mulai Skoring"), delay=2
    )
    await page.wait_for_load_state("domcontentloaded")

    # 3. Survey 1
    await page.locator("label").filter(
        has_text="Kurang dari Rp100 juta/tahun"
    ).wait_for(state="visible", timeout=15000)
    await page.locator("label").filter(
        has_text="Kurang dari Rp100 juta/tahun"
    ).click()
    await safe_click(page, page.get_by_text("Di bawah atau sama dengan"))
    await safe_click(page, page.get_by_text("1 Orang"))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Tidak", exact=True).first)
    await safe_click(page, page.get_by_text("Tidak", exact=True).nth(1))
    await safe_click(page, page.get_by_text("Tidak", exact=True).nth(2))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Tidak", exact=True).first)
    await safe_click(page, page.get_by_text("Ya, Sebagian").nth(1))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Tidak, masih di satu provinsi"))
    await safe_click(page, page.get_by_text("Menggunakan media sosial ("))
    await safe_click(page, page.get_by_text("Ya, Sebagian").first)
    await safe_click(page, page.get_by_text("Ya, Sebagian").nth(1))
    await safe_click(page, page.get_by_text("Ya, Sebagian").nth(2))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Membuat prosedur tertulis"))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Ya", exact=True).first)
    await safe_click(page, page.get_by_text("Tidak", exact=True).nth(1))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Tidak", exact=True).first)
    await safe_click(page, page.get_by_text("Tidak, belum secara khusus"))
    await safe_click(page, page.get_by_text("Tidak", exact=True).nth(1))
    await safe_click(page, page.get_by_text("Tidak", exact=True).nth(2))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Belum memiliki dokumen"))
    await safe_click(page, page.get_by_text("NPWP atas nama badan usaha"))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Memastikan agar karyawan"))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Ya, tapi baru sebagian."))
    await safe_click(page, page.get_by_text("Tahu nama-nama atau merek"))
    await safe_click(
        page, page.get_by_role("link", name="Selanjutnya"), delay=0.8
    )

    await safe_click(page, page.get_by_text("Belum ada prosedur khusus"))
    await safe_click(page, page.get_by_text("Belum ada prosedur atau tim"))
    await safe_click(page, page.get_by_text("Saldo cadangan kas usaha saya"))
    await safe_click(page, page.get_by_text("Akses internet yang handal ("))

    await safe_click(
        page, page.get_by_role("link", name="Hitung Nilai Survey"), delay=1.5
    )
    await safe_click(
        page,
        page.get_by_role("link", name="Lihat Hasil Level UMKM Saya"),
        delay=2,
    )

    # 4. Mode Rescoring Ulang (Jika Diberdayakan)
    if jenis_mode == "Rescoring (Skoring Ulang)":
      log_status(f"Menjalankan tahap Rescoring User #{user_data['id']}...")
      btn_rescore = page.get_by_role("link", name="Skoring Ulang")
      await btn_rescore.wait_for(state="visible", timeout=15000)
      await safe_click(page, btn_rescore, delay=1)

      btn_confirm = page.get_by_role("link", name="Ya, Lakukan")
      await btn_confirm.wait_for(state="visible", timeout=10000)
      await safe_click(page, btn_confirm, delay=2)

      elem_survey2_start = page.get_by_text("Antara Rp100 juta/tahun s.d")
      await elem_survey2_start.wait_for(state="visible", timeout=15000)

      await safe_click(page, elem_survey2_start, delay=0.5)
      await safe_click(
          page, page.get_by_text("Di atas Rp10 juta s.d Rp50"), delay=0.5
      )
      await safe_click(page, page.get_by_text("-4 orang"), delay=0.5)
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(page, page.get_by_text("Ya", exact=True).first, delay=0.5)
      await safe_click(page, page.get_by_text("Ya", exact=True).nth(1), delay=0.5)
      await safe_click(
          page, page.get_by_text("Tidak", exact=True).nth(2), delay=0.5
      )
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(page, page.get_by_text("Ya", exact=True).first, delay=0.5)
      await safe_click(
          page, page.get_by_text("Ya, Sebagian").nth(1), delay=0.5
      )
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(
          page, page.get_by_text("Ya, lintas provinsi tapi"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Menggunakan media sosial ("), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Menggunakan platform e-"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Menggunakan pembayaran"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Ya, Sebagian").first, delay=0.5
      )
      await safe_click(page, page.get_by_text("Ya", exact=True).nth(1), delay=0.5)
      await safe_click(page, page.get_by_text("Ya", exact=True).nth(2), delay=0.5)
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(
          page, page.get_by_text("Membuat prosedur tertulis"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Melakukan pemeriksaan rutin"), delay=0.5
      )
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(page, page.get_by_text("Ya", exact=True).first, delay=0.5)
      await safe_click(page, page.get_by_text("Ya", exact=True).nth(1), delay=0.5)
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(page, page.get_by_text("Ya", exact=True).first, delay=0.5)
      await safe_click(page, page.get_by_text("Ya", exact=True).first, delay=0.5)
      await safe_click(
          page, page.get_by_text("Ya, pelatihan tahunan untuk"), delay=0.5
      )
      await safe_click(page, page.get_by_text("Ya", exact=True).nth(1), delay=0.5)
      await safe_click(page, page.get_by_text("Ya", exact=True).nth(2), delay=0.5)
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(
          page, page.get_by_text("Belum memiliki dokumen"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("NPWP atas nama badan usaha"), delay=0.5
      )
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(
          page, page.get_by_text("Memastikan agar karyawan"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Memiliki prosedur khusus"), delay=0.5
      )
      await safe_click(
          page,
          page.locator("label").filter(
              has_text="Memiliki target pengurangan"
          ),
          delay=0.5,
      )
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(
          page, page.get_by_text("Ya, tapi baru sebagian."), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Tahu nama-nama atau merek"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Melakukan perbandingan"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Tahu persis lokasi atau"), delay=0.5
      )
      await safe_click(
          page, page.get_by_role("link", name="Selanjutnya"), delay=1
      )

      await safe_click(page, page.get_by_text("Ya", exact=True).first, delay=0.5)
      await safe_click(page, page.get_by_text("Ya", exact=True).nth(1), delay=0.5)
      await safe_click(
          page, page.get_by_text("Saldo cadangan kas usaha saya"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Ada beberapa teman atau"), delay=0.5
      )
      await safe_click(
          page,
          page.get_by_text(
              "Sudah ada rekam jejak positif atau relasi baik di beberapa bank"
          ),
          delay=0.5,
      )
      await safe_click(
          page,
          page.get_by_text(
              "Sudah ada rekam jejak positif atau relasi baik di beberapa"
              " Lembaga keuangan"
          ),
          delay=0.5,
      )
      await safe_click(
          page, page.get_by_text("Akses internet yang handal ("), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("HP pintar khusus untuk bisnis"), delay=0.5
      )
      await safe_click(
          page, page.get_by_text("Laptop/Komputer kerja"), delay=0.5
      )

      await safe_click(
          page, page.get_by_role("link", name="Hitung Nilai Survey"), delay=1.5
      )
      await safe_click(
          page,
          page.get_by_role("link", name="Lihat Hasil Level UMKM Saya"),
          delay=1.5,
      )

    return True
  except Exception as e:
    log_status(f"Error User #{user_data['id']}: {e}")
    return False


async def execute_user(
    browser, user, semaphore, jenis_mode, is_headless, log_status
):
  async with semaphore:
    log_status(f"Membuka Browser untuk User #{user['id']}: {user['nama']}")
    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()

    try:
      await page.goto(user["url"], wait_until="domcontentloaded")
      await asyncio.sleep(1.5)

      # Form Utama Pendaftaran
      await page.get_by_role("textbox", name="Masukkan nama anda").fill(
          user["nama"]
      )
      await page.get_by_role("textbox", name="Masukkan nomor telepon anda").fill(
          user["telepon"]
      )
      await page.get_by_placeholder("Masukkan Email anda").fill(user["email"])
      await page.get_by_placeholder("Masukkan NIK anda").fill(user["nik"])

      pass_field = page.locator("form").filter(
          has_text="Nama Lengkap Nomor Telepon"
      ).locator('input[name="password"]')
      await pass_field.fill(user["password"])
      await page.locator('input[name="password_retype"]').fill(
          user["password"]
      )
      await asyncio.sleep(1.0)

      # CAPTCHA Engine
      captcha_tercapai = False
      for trial in range(1, 10):
        hasil_ai = await solve_captcha_ai(page)
        if len(hasil_ai) < 5:
          try:
            refresh_btn = page.locator(
                "a[href*='refresh'], .btn-refresh-captcha, img[src*='captcha']"
            ).first
            if await refresh_btn.is_visible():
              await refresh_btn.click()
              await asyncio.sleep(1.5)
          except:
            pass
          continue

        await isi_captcha_ke_form(page, hasil_ai)
        await safe_click(
            page, page.get_by_role("button", name="Daftar"), delay=2.0
        )

        tgl_elem = page.get_by_placeholder("Masukkan Tanggal Lahir")
        try:
          await tgl_elem.wait_for(state="visible", timeout=4000)
          captcha_tercapai = True
          break
        except:
          try:
            refresh_btn = page.locator(
                "a[href*='refresh'], .btn-refresh-captcha, img[src*='captcha']"
            ).first
            if await refresh_btn.is_visible():
              await refresh_btn.click()
              await asyncio.sleep(1.5)
          except:
            pass

      if captcha_tercapai:
        status_lanjutan = await proses_lanjutan_otomatis(
            context, page, user, jenis_mode, log_status
        )
        await context.close()
        return status_lanjutan
      else:
        await context.close()
        return False
    except Exception as e:
      try:
        await context.close()
      except:
        pass
      return False


# --- TAMPILAN DASHBOARD STREAMLIT ---
st.title("🤖 Dashboard Monitoring & Automation UMKM")
st.caption("Platform Otomatisasi Input & Skoring Referral LinkUMKM BRI")

with st.sidebar:
  st.header("⚙️ Pengaturan Tugas")
  target_url = st.text_input(
      "URL Target Referral",
      value="https://linkumkm.bri.co.id/umkmscore/mantri/175924",
  )
  mode_pilihan = st.selectbox(
      "Mode Eksekusi",
      ["New Scoring (Skoring Awal)", "Rescoring (Skoring Ulang)"],
  )
  jumlah_target = st.number_input(
      "Jumlah Target Pengguna", min_value=1, max_value=500, value=5
  )
  max_concurrent = st.slider(
      "Maksimal Concurrent Browser", min_value=1, max_value=10, value=2
  )

  # Pada Streamlit Cloud, browser harus berjalan secara headless (True)
  is_headless = st.checkbox(
      "Mode Headless Browser",
      value=True,
      help="Biarkan centang jika di-deploy di cloud server.",
  )
  btn_start = st.button("🚀 Mulai Otomatisasi", type="primary")

col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
metric_target = col_kpi1.metric("Target Total", f"{jumlah_target} Data")
metric_sukses = col_kpi2.metric("Berhasil", "0 Data")
metric_gagal = col_kpi3.metric("Gagal / Retry", "0 Data")

progress_bar = st.progress(0)
status_log = st.empty()
log_area = st.expander("📜 Detail Console Log Live", expanded=True)
logs_container = log_area.container()


def add_log(msg):
  logs_container.write(msg)


async def start_automation():
  semaphore = asyncio.Semaphore(max_concurrent)
  total_berhasil = 0
  total_gagal = 0
  next_id = 1
  jumlah_dibuat = jumlah_target

  add_log("⚡ Memulai engine browser Playwright...")

  async with async_playwright() as p:
    browser = await p.chromium.launch(
        headless=is_headless,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    while total_berhasil < jumlah_target:
      add_log(f"🔄 Membuat {jumlah_dibuat} data akun UMKM baru...")
      users = [
          generate_single_user(next_id + i, target_url)
          for i in range(jumlah_dibuat)
      ]
      next_id += jumlah_dibuat

      tasks = [
          execute_user(
              browser, u, semaphore, mode_pilihan, is_headless, add_log
          )
          for u in users
      ]
      results = await asyncio.gather(*tasks)

      berhasil_putaran = sum(1 for r in results if r is True)
      gagal_putaran = len(results) - berhasil_putaran

      total_berhasil += berhasil_putaran
      total_gagal += gagal_putaran

      # Update tampilan KPI & Progress Bar
      metric_sukses.metric("Berhasil", f"{total_berhasil} Data")
      metric_gagal.metric("Gagal / Retry", f"{total_gagal} Data")
      progress_bar.progress(min(total_berhasil / jumlah_target, 1.0))

      if total_berhasil < jumlah_target:
        jumlah_dibuat = gagal_putaran
        add_log(
            f"⚠️ Putaran selesai. Berhasil: {berhasil_putaran}, Gagal:"
            f" {gagal_putaran}. Mengulangi {gagal_putaran} data yang gagal..."
        )
        await asyncio.sleep(2.0)
      else:
        break

    await browser.close()
    st.balloons()
    st.success(
        f"✅ Seluruh target ({total_berhasil}/{jumlah_target}) telah selesai"
        " diproses secara tuntas!"
    )


if btn_start:
  asyncio.run(start_automation())
