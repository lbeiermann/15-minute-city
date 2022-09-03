#!/usr/bin/env python
# coding: utf-8

from streamlit_folium import st_folium
import folium
import mapclassify
import matplotlib
import geopandas as gpd
import networkx as nx
import osmnx as ox
import osmnx.utils_graph
import streamlit as st
# from descartes import PolygonPatch
from shapely.geometry import Point

# title and layout
st.set_page_config(layout="wide", page_title="The 15-Minute-Map 🗺️")
col1, col2 = st.columns(2)
with col1:
    st.title("The 15-Minute-Map 🗺️")
    st.write("Mapping the 15-minute city: Use this web app to map all local amenities you can reach via a 5-/10-/15-minute walk from any address in the world!")

# address input
place = st.text_input("Enter street address")
st.text("e.g. 712 Red Bark Lane, Henderson, NV 89011, USA")

# configure the network type, trip times, and travel speed
network_type = "walk"
trip_times = [15, 10, 5]  # in minutes
travel_speed = 4.8  # walking speed in km/hour

# make map containing isochrone polygons
@st.experimental_memo
def make_map(place):
    # download the street network
    G = ox.graph_from_address(place, network_type=network_type)

    # find the centermost node and then project the graph to UTM
    gdf_nodes = ox.graph_to_gdfs(G, edges=False)
    x, y = gdf_nodes["geometry"].unary_union.centroid.xy
    center_node = ox.distance.nearest_nodes(G, x[0], y[0])
    G = ox.project_graph(G)

    # add an edge attribute for time in minutes required to traverse each edge
    meters_per_minute = travel_speed * 1000 / 60  # km per hour to m per minute
    for _, _, _, data in G.edges(data=True, keys=True):
        data["time"] = data["length"] / meters_per_minute

    # get one color for each isochrone
    iso_colors = ox.plot.get_colors(n=len(trip_times), cmap="autumn", start=0, return_hex=True)
    # make the isochrone polygons
    isochrone_polys = []
    for trip_time in sorted(trip_times, reverse=True):
        subgraph = nx.ego_graph(G, center_node, radius=trip_time, distance="time")
        node_points = [Point((data["x"], data["y"])) for node, data in subgraph.nodes(data=True)]
        bounding_poly = gpd.GeoSeries(node_points).unary_union.convex_hull
        isochrone_polys.append(bounding_poly)
    return G, iso_colors, isochrone_polys

#get amenities for place
@st.cache
def get_amenities(place):
    amenities = ox.geometries_from_address(place, tags={"amenity": True}, dist=1000)
    return amenities

#plot map
def plot_map(G, iso_colors, isochrone_polys, amenities):
    m = folium.Map(tiles="CartoDB positron")

    # isochrones,  NB CRS
    m = gpd.GeoDataFrame(
        {"color": iso_colors, "trip time": trip_times},
        geometry=isochrone_polys,
        crs=G.graph["crs"],
    ).explore(
        m=m,
        name="isochrones",
        style_kwds={"style_function": lambda p: {"color": p["properties"]["color"]}},
    )
    # amenities
    m = amenities.loc[:, ["amenity", "name", "geometry"]].explore(
        "amenity", m=m, name="amenities"
    )

    m.fit_bounds(m.get_bounds(), padding=(30, 30))

    folium.LayerControl("topleft", collapsed=False).add_to(m)
    return m

def main(place):
    G, iso_colors, isochrone_polys = make_map(place)
    amenities = get_amenities(place)
    m = plot_map(G, iso_colors, isochrone_polys, amenities)
    return m

if place:
    #with st.spinner("Getting there at 4.8 km/h..."):
    try:
        m = main(place)
    except (KeyError, NameError):
        st.error("Please try another address.")
    st_data = st_folium(m, width=1000)





