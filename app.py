import streamlit as st
import pandas as pd
import pydeck as pdk
import h3

st.set_page_config(layout="wide")
st.title("Pilot Traffic - Home")

# === 1️⃣ Load data ===
df = pd.read_csv(r"C:\Data Analyst\QA Dataset\traffic_dataset.csv")
df['date'] = pd.to_datetime(df['date'])

# === 2️⃣ Sidebar filter interaktif ===
selected_hour = st.sidebar.slider("Pilih jam", 0, 23, 18)
selected_date = st.sidebar.date_input("Pilih tanggal", df['date'].min())
show_arc = st.sidebar.checkbox("Tampilkan Home → Traffic", value=False)

# Filter data per jam & tanggal
df_traffic = df[
    (df["hour"] == selected_hour) &
    (df["date"] == pd.Timestamp(selected_date))
]

if df_traffic.empty:
    st.warning("Tidak ada data untuk filter ini.")
else:
    # === 3️⃣ Aggregate count_visitor per traffic H3 ===
    traffic_agg = df_traffic.groupby("traffic_h3_8")["count_visitor"].sum().reset_index()

    # Fungsi H3 ke lat/lon
    def h3_to_latlon(h, count):
        lat, lon = h3.h3_to_geo(h)
        return {"h3": h, "lat": lat, "lon": lon, "count_visitor": count}

    traffic_hex = pd.DataFrame([h3_to_latlon(h, c) for h, c in zip(traffic_agg["traffic_h3_8"], traffic_agg["count_visitor"])])

    # Gradasi warna: visitor rendah → terang, tinggi → gelap
    min_count = traffic_hex["count_visitor"].min()
    max_count = traffic_hex["count_visitor"].max()
    def color_scale(count):
        val = int(180 - (count - min_count) / (max_count - min_count + 1e-6) * 130)
        val = max(val, 50)
        return [255, val, val, 180]

    traffic_hex["color"] = traffic_hex["count_visitor"].apply(color_scale)

    # === 4️⃣ Sidebar Table untuk pilih H3 ===
    st.sidebar.subheader("Pilih H3 Traffic")
    h3_list = traffic_agg.sort_values("count_visitor", ascending=False)
    selected_h3_table = st.sidebar.radio(
        "Klik H3:",
        options=[None] + h3_list["traffic_h3_8"].tolist(),
        index=0
    )

    # === 5️⃣ Layer traffic H3 ===
    if selected_h3_table:  # fokus hanya H3 yang dipilih
        traffic_hex_filtered = traffic_hex[traffic_hex["h3"] == selected_h3_table]
    else:  # semua H3
        traffic_hex_filtered = traffic_hex

    traffic_layer = pdk.Layer(
        "H3HexagonLayer",
        data=traffic_hex_filtered,
        get_hexagon="h3",
        get_fill_color="color",
        extruded=False,
        pickable=True
    )

    layers = [traffic_layer]

    # === 6️⃣ Layer Arc/Home jika dicentang dan H3 dipilih ===
    if show_arc and selected_h3_table:
        df_filtered = df_traffic[df_traffic["traffic_h3_8"] == selected_h3_table]

        home_hex = pd.DataFrame([h3_to_latlon(h, 0) for h in df_filtered["home_h3_8"].unique()])

        home_layer = pdk.Layer(
            "H3HexagonLayer",
            data=home_hex,
            get_hexagon="h3",
            get_fill_color=[0, 200, 255, 180],
            extruded=False
        )

        arc_layer = pdk.Layer(
            "ArcLayer",
            data=df_filtered,
            get_source_position=["origin_lon", "origin_lat"],
            get_target_position=["dest_lon", "dest_lat"],
            get_source_color=[0, 200, 255, 200],
            get_target_color=[255, 100, 100, 200],
            get_width=4,
            pickable=True,
            auto_highlight=True
        )

        layers.extend([home_layer, arc_layer])

    # === 7️⃣ View State ===
    view_state = pdk.ViewState(
        latitude=df_traffic["dest_lat"].mean(),
        longitude=df_traffic["dest_lon"].mean(),
        zoom=13,
        pitch=0,
        bearing=0
    )

    # === 8️⃣ Deck ===
    
    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_provider='carto',
        map_style='light',
        tooltip={"text": "Traffic H3: {h3}\nVisitors: {count_visitor}"},
        height=3000,
        width=1200
    )

    st.pydeck_chart(r)
