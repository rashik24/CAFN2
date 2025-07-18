import streamlit as st
import pandas as pd
import pydeck as pdk
from opencage.geocoder import OpenCageGeocode
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────
os.environ["MAPBOX_API_KEY"] = "pk.eyJ1IjoicnNpZGRpcTIiLCJhIjoiY21jbjcwNWtkMHV5bzJpb2pnM3QxaDFtMyJ9.6T6i_QFuKQatpGaCFUvCKg"
OPENCAGE_API_KEY = "f53bdda785074d5499b7a4d29d5acd1f"
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

AGENCY_CSV = "CAFN_July_edit.csv"  # columns: Name, Contact, Hours, Address, Latitude, Longitude
ODM_CSV = "ODM FBCENC 2.csv"            # columns: Total_TravelTime, Agency_name, Latitude, Longitude, etc.

# ─── STREAMLIT APP ───────────────────────────────────────────────────────
st.set_page_config(page_title="Food Pantries Map", layout="wide")
st.title("Nearest Food Pantry Finder")

# ─── USER INPUT ──────────────────────────────────────────────────────────
user_address = st.text_input("Enter your address (e.g., 123 Main St, Raleigh, NC):")

if user_address:
    try:
        results = geocoder.geocode(user_address)
        if results:
            user_lat = results[0]["geometry"]["lat"]
            user_lon = results[0]["geometry"]["lng"]
            st.success(f"Your location: {user_lat:.5f}, {user_lon:.5f}")
        else:
            st.error("Could not geocode your address.")
            st.stop()
    except Exception as e:
        st.error(f"Geocoding error: {e}")
        st.stop()

    # ─── LOAD DATA ───────────────────────────────────────────────────────
    agencies_df = pd.read_csv(AGENCY_CSV)
    odm_df = pd.read_csv(ODM_CSV)

    # Clean column names
    agencies_df.columns = agencies_df.columns.str.strip().str.title()
    odm_df.columns = odm_df.columns.str.strip()

    # ─── FIND CLOSEST AGENCY ─────────────────────────────────────────────
    odm_df_sorted = odm_df.sort_values(by="Total_TravelTime").copy()
    closest_agency = odm_df_sorted.head(1)

    # Merge with agency details if needed (match by Agency_name)
    merged_df = closest_agency.merge(
        agencies_df,
        left_on="Agency_name",
        right_on="Name",
        how="left"
    )

    # ─── SHOW TABLE ─────────────────────────────────────────────────────
    display_cols = ["Name", "Contact", "Hours", "Address", "Total_TravelTime", "Total_Miles"]
    st.subheader("Closest Food Pantry")
    st.dataframe(
        merged_df[display_cols].rename(columns={
            "Total_TravelTime": "Travel Time (min)",
            "Total_Miles": "Distance (miles)"
        })
    )

    # ─── MAP ─────────────────────────────────────────────────────────────
    user_location_df = pd.DataFrame({
        "name": ["Your Location"],
        "latitude": [user_lat],
        "longitude": [user_lon],
        "color_r": [0],
        "color_g": [0],
        "color_b": [255],
        "tooltip": ["Your Location"]
    })

    agency_map_df = merged_df.copy()
    agency_map_df["color_r"] = 255
    agency_map_df["color_g"] = 0
    agency_map_df["color_b"] = 0
    agency_map_df["tooltip"] = "Agency: " + agency_map_df["Name"]

    agency_map_df = agency_map_df.rename(columns={"Name": "name", "Latitude": "latitude", "Longitude": "longitude"})
    combined_df = pd.concat([user_location_df, agency_map_df], ignore_index=True)

    layer = pdk.Layer(
        "ScatterplotLayer",
        combined_df,
        get_position='[longitude, latitude]',
        get_color='[color_r, color_g, color_b]',
        get_radius=250,
        pickable=True,
    )

    tooltip = {"html": "{tooltip}", "style": {"color": "white"}}
    view_state = pdk.ViewState(longitude=user_lon, latitude=user_lat, zoom=10, pitch=0)

    deck = pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=view_state,
        layers=[layer],
        tooltip=tooltip
    )

    st.pydeck_chart(deck)
