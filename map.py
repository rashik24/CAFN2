import streamlit as st
import pandas as pd
import pydeck as pdk
from opencage.geocoder import OpenCageGeocode
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────
os.environ["MAPBOX_API_KEY"] = "pk.eyJ1IjoicnNpZGRpcTIiLCJhIjoiY21jbjcwNWtkMHV5bzJpb2pnM3QxaDFtMyJ9.6T6i_QFuKQatpGaCFUvCKg"
OPENCAGE_API_KEY = "f53bdda785074d5499b7a4d29d5acd1f"
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

# CSV with agency data (Name, Contact, Hours, Address, latitude, longitude)
AGENCY_CSV = "agencies_with_latlon.csv"

# ─── STREAMLIT APP ───────────────────────────────────────────────────────
st.set_page_config(page_title="Food Pantries Map", layout="wide")
st.title("Nearby Food Pantries")

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

    # ─── LOAD AGENCY DATA ───────────────────────────────────────────────
    agencies_df = pd.read_csv(AGENCY_CSV)
    agencies_df.columns = agencies_df.columns.str.strip().str.title()

    # Show the table with Name, Contact, Hours, Address
    display_cols = ["Name", "Contact", "Hours", "Address"]
    st.subheader("Food Pantry Details")
    st.dataframe(agencies_df[display_cols])

    # --- user location ---
    user_location_df = pd.DataFrame({
        "name": ["Your Location"],
        "latitude": [user_lat],
        "longitude": [user_lon],
        "color_r": [0],
        "color_g": [0],
        "color_b": [255],
        "tooltip": ["Your Location"]
    })

    # --- agency locations ---
    agency_map_df = agencies_df.copy()
    agency_map_df = agency_map_df.rename(columns={"Name": "name", "Latitude": "latitude", "Longitude": "longitude"})
    agency_map_df["color_r"] = 255
    agency_map_df["color_g"] = 0
    agency_map_df["color_b"] = 0
    agency_map_df["tooltip"] = "Agency: " + agency_map_df["name"]

    combined_df = pd.concat([user_location_df, agency_map_df], ignore_index=True)

    # ─── PYDECK MAP ─────────────────────────────────────────────
    layer = pdk.Layer(
        "ScatterplotLayer",
        combined_df,
        get_position='[longitude, latitude]',
        get_color='[color_r, color_g, color_b]',
        get_radius=250,
        pickable=True,
    )

    tooltip = {
        "html": "{tooltip}",
        "style": {"color": "white"}
    }

    view_state = pdk.ViewState(
        longitude=user_lon,
        latitude=user_lat,
        zoom=10,
        pitch=0
    )

    deck = pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=view_state,
        layers=[layer],
        tooltip=tooltip
    )

    st.pydeck_chart(deck)
