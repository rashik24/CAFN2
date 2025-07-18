import streamlit as st
import pandas as pd
import pydeck as pdk
import geopandas as gpd
from shapely.geometry import Point
from opencage.geocoder import OpenCageGeocode
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────
os.environ["MAPBOX_API_KEY"] = "pk.eyJ1IjoicnNpZGRpcTIiLCJhIjoiY21jbjcwNWtkMHV5bzJpb2pnM3QxaDFtMyJ9.6T6i_QFuKQatpGaCFUvCKg"

ODM_CSV = "ODM FBCENC 2.csv"
TRACTS_SHP = "cb_2023_37_tract_500k.shp"

OPENCAGE_API_KEY = "f53bdda785074d5499b7a4d29d5acd1f"
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

# ─── STREAMLIT APP ───────────────────────────────────────────────────────
st.set_page_config(page_title="Food Pantries Finder", layout="wide")
st.title("Food Pantries Finder")

# ─── USER INPUT ──────────────────────────────────────────────────────────
user_address = st.text_input(
    "Enter your address (e.g. 123 Main St, Raleigh, NC):"
)

if user_address:
    try:
        results = geocoder.geocode(user_address)
        if results:
            user_lat = results[0]["geometry"]["lat"]
            user_lon = results[0]["geometry"]["lng"]
            st.success(f"Geocoded location: {user_lat:.5f}, {user_lon:.5f}")
        else:
            st.error("Could not geocode your address.")
            st.stop()
    except Exception as e:
        st.error(f"Geocoding error: {e}")
        st.stop()

    # ─── LOAD DATA ───────────────────────────────────────────────────────
    odm_df = pd.read_csv(ODM_CSV)
    odm_df.columns = odm_df.columns.str.strip().str.lower()
    odm_df["geoid"] = odm_df["geoid"].astype(int)

    tracts_gdf = gpd.read_file(TRACTS_SHP)
    tracts_gdf = tracts_gdf.to_crs(epsg=4326)

    if tracts_gdf["GEOID"].dtype == object:
        tracts_gdf["GEOID"] = tracts_gdf["GEOID"].astype(int)

    # ─── FIND USER GEOID ────────────────────────────────────────────────
    user_point = Point(user_lon, user_lat)
    matched_tract = tracts_gdf[tracts_gdf.contains(user_point)]

    if not matched_tract.empty:
        user_geoid = matched_tract.iloc[0]["GEOID"]
        st.success(f"Matched your location to GEOID {user_geoid}")
    else:
        st.error("Could not match your location to a census tract.")
        st.stop()

    # ─── FIND AGENCIES REACHABLE FROM GEOID ─────────────────────────────
    agencies_from_user_geoid = odm_df[
        (odm_df["geoid"] == user_geoid) &
        (odm_df["total_traveltime"] <= 20)
    ]

    if agencies_from_user_geoid.empty:
        st.warning("No agencies linked to your tract. Searching all nearby agencies instead.")
        agencies_from_user_geoid = odm_df[odm_df["total_traveltime"] <= 60]

    if not agencies_from_user_geoid.empty:
        agencies_from_user_geoid = agencies_from_user_geoid.rename(columns={
            "total_traveltime": "travel_minutes",
            "total_miles": "distance_miles",
            "agency_name": "agency"
        })

        # Show agency table
        st.subheader("Nearby Agencies")
        agencies_from_user_geoid["travel_minutes"] = agencies_from_user_geoid["travel_minutes"].round(2)
        agencies_from_user_geoid["distance_miles"] = agencies_from_user_geoid["distance_miles"].round(2)
        st.dataframe(agencies_from_user_geoid[['agency', 'distance_miles', 'travel_minutes']])

        # ─── PYDECK MAP ─────────────────────────────────────────────
        user_location_df = pd.DataFrame({
            "name": ["Your Location"],
            "latitude": [user_lat],
            "longitude": [user_lon],
            "color_r": [0],
            "color_g": [0],
            "color_b": [255],
            "tooltip": ["Your Location"]
        })

        agency_map_df = agencies_from_user_geoid[[
            "agency", "latitude", "longitude", "travel_minutes", "distance_miles"
        ]].dropna().copy()

        agency_map_df["color_r"] = 255
        agency_map_df["color_g"] = 0
        agency_map_df["color_b"] = 0

        agency_map_df["tooltip"] = (
            "Agency: " + agency_map_df["agency"] +
            "<br>Travel Time (min): " + agency_map_df["travel_minutes"].astype(str) +
            "<br>Distance (miles): " + agency_map_df["distance_miles"].round(2).astype(str)
        )

        agency_map_df = agency_map_df.rename(columns={"agency": "name"})

        combined_df = pd.concat([user_location_df, agency_map_df], ignore_index=True)

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

    else:
        st.warning("No agencies accessible from your GEOID.")
