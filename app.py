import datetime
import importlib
import random

try:
  st = importlib.import_module("streamlit")
except ModuleNotFoundError as exc:
  if exc.name != "streamlit":
    raise
  raise SystemExit(
    "Streamlit is not installed. Install the project dependency with: "
    "python -m pip install streamlit"
  ) from exc

# Konfigurasi Halaman Website
st.set_page_config(
    page_title="Dashboard Monitoring UMKM", page_icon="📊", layout="wide"
)

# Header Utama
st.title("📊 Dashboard Monitoring Operasional UMKM")
st.markdown("---")


# 1. SIMULASI DATA LOG/TRANSAKSI
@st.cache_data(ttl=60)
def load_data():
  # Simulasi data penjualan & aktivitas sistem
    return [
      {
        "Waktu": datetime.datetime.now() - datetime.timedelta(hours=i),
        "Kategori": random.choice(["Makanan", "Minuman", "Pakaian"]),
        "Total_Penjualan": random.randint(50000, 500000),
        "Status_Sistem": "ERROR" if i == 1 else "SUCCESS",
      }
      for i in range(10)
    ]


df = load_data()

# 2. METRIK UTAMA (KPI Cards)
col1, col2, col3, col4 = st.columns(4)

total_omset = sum(row["Total_Penjualan"] for row in df)
total_transaksi = len(df)
status_terakhir = df[0]["Status_Sistem"]
error_count = sum(row["Status_Sistem"] == "ERROR" for row in df)

with col1:
  st.metric(label="Total Omset Hari Ini", value=f"Rp {total_omset:,.0f}")

with col2:
  st.metric(label="Total Transaksi", value=f"{total_transaksi} Transaksi")

with col3:
  st.metric(
      label="Status Program Python",
      value="NORMAL" if status_terakhir == "SUCCESS" else "DOWNTIME",
  )

with col4:
  st.metric(
      label="Error Terdeteksi", value=f"{error_count} Kasus", delta_color="inverse"
  )

st.markdown("---")

# 3. GRAFIK & VISUALISASI DATA
left_col, right_col = st.columns(2)

with left_col:
  st.subheader("📈 Tren Penjualan per Jam")
  chart_data = {
      "Waktu": [row["Waktu"] for row in df],
      "Total_Penjualan": [row["Total_Penjualan"] for row in df],
  }
  st.line_chart(chart_data, x="Waktu", y="Total_Penjualan")

with right_col:
  st.subheader("📦 Penjualan per Kategori")
  category_sales = {}
  for row in df:
    category = row["Kategori"]
    category_sales[category] = category_sales.get(category, 0) + row["Total_Penjualan"]
  st.bar_chart(category_sales)

# 4. TABEL LOG SYSTEM UTAMA
st.subheader("📋 Riwayat Aktivitas System (Log)")
st.dataframe(df, use_container_width=True)

# Tombol Refresh Manual
if st.button("🔄 Refresh Data"):
  st.rerun()