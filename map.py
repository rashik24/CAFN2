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

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c * 0.621371  # Convert to miles

# ─── STREAMLIT APP ───────────────────────────────────────────────────────
st.set_page_config(page_title="Food Pantries Map", layout="wide")
st.title("Nearest Food Pantry Finder")

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

    # ─── LOAD ODM DATA ──────────────────────────────────────────────
    odm_df = pd.read_csv(ODM_CSV)
    odm_df.columns = odm_df.columns.str.strip()

    # Ensure numeric columns
    odm_df["Latitude"] = pd.to_numeric(odm_df["Latitude"], errors="coerce")
    odm_df["Longitude"] = pd.to_numeric(odm_df["Longitude"], errors="coerce")

    # ─── CALCULATE DISTANCE FROM USER ───────────────────────────────
    odm_df["User_Distance"] = odm_df.apply(
        lambda row: haversine_distance(user_lat, user_lon, row["Latitude"], row["Longitude"]), axis=1
    )

    # ─── FIND CLOSEST AGENCIES ──────────────────────────────────────
    closest_agencies = odm_df.sort_values(by="User_Distance").head(3)

    # ─── SHOW TABLE ─────────────────────────────────────────────────
    st.subheader("Closest Food Pantries (Based on Your Location)")
    display_cols = ["Agency_name", "Total_TravelTime", "Total_Miles", "User_Distance"]
    st.dataframe(
        closest_agencies[display_cols].rename(columns={
            "Total_TravelTime": "Travel Time (min)",
            "Total_Miles": "Distance (miles)",
            "User_Distance": "Distance from You (miles)"
        })
    )

    # ─── MAP ───────────────────────────────────────────────────────
    user_location_df = pd.DataFrame({
        "name": ["Your Location"],
        "latitude": [user_lat],
        "longitude": [user_lon],
        "color_r": [0],
        "color_g": [0],
        "color_b": [255],
        "tooltip": ["Your Location"]
    })

    agency_map_df = closest_agencies.rename(columns={
        "Agency_name": "name", "Latitude": "latitude", "Longitude": "longitude"
    })
    agency_map_df["color_r"] = 255
    agency_map_df["color_g"] = 0
    agency_map_df["color_b"] = 0
    agency_map_df["tooltip"] = (
        "Agency: " + agency_map_df["name"] +
        "<br>Travel Time: " + agency_map_df["Total_TravelTime"].astype(str) +
        "<br>Distance: " + agency_map_df["User_Distance"].round(2).astype(str) + " miles"
    )

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
