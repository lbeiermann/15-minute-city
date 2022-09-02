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

#%matplotlib inline

ox.config(log_console=False, use_cache=True)

# title and layout
st.set_page_config(page_title="The 15-Minute-Map 🗺️")
st.title("The 15-Minute-Map 🗺️")

# display text
st.write("Mapping the 15-minute city: Use this app to map all local amenities you can reach via a 5-/10-/15-minute walk from any address in the world!")

# enter address
place = st.text_input("Enter street address")
st.text("e.g. 712 Red Bark Lane, Henderson, NV 89011, USA")

# configure the network type, trip times, and travel speed
network_type = "walk"
trip_times = [15, 10, 5]  # in minutes
travel_speed = 4.8  # walking speed in km/hour

# configure submit button
#submit = st.button("Generate map")

if place:
    with st.spinner("Getting there..."):

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
        iso_colors = ox.plot.get_colors(n=len(trip_times), cmap="Blues", start=0, return_hex=True)

        # make the isochrone polygons
        isochrone_polys = []
        for trip_time in sorted(trip_times, reverse=True):
            subgraph = nx.ego_graph(G, center_node, radius=trip_time, distance="time")
            node_points = [Point((data["x"], data["y"])) for node, data in subgraph.nodes(data=True)]
            bounding_poly = gpd.GeoSeries(node_points).unary_union.convex_hull
            isochrone_polys.append(bounding_poly)

        # get amenities for place
        amenities = ox.geometries_from_address(place, tags={"amenity":True}, dist=1000)

        # plot the network, add isochrones as colored descartes polygon patches, then add amenities
        #fig, ax = ox.plot_graph(
            #G, show=False, close=False, edge_color="#999999", edge_alpha=0.2, node_size=0
        #)
        #for polygon, fc in zip(isochrone_polys, iso_colors):
            #patch = PolygonPatch(polygon, fc=fc, ec="none", alpha=0.6, zorder=-1)
            #ax.add_patch(patch)

        #amenities.plot(color="white", markersize=1, ax=ax)

        # not working as expected...
        #m = ox.folium.plot_graph_folium(G, popup_attribute="name", weight=2, color="#8b0000", fit_bounds=True, tiles="CartoDB positron")

        m = folium.Map(tiles="CartoDB positron")

        # edges ...
        m = (
            osmnx.utils_graph.graph_to_gdfs(G, nodes=False)
            .loc[:, ["name", "geometry"]]
            .explore(name="edges", m=m)
        )

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
        # ameneties
        m = amenities.loc[:, ["amenity", "name", "geometry"]].explore(
            "amenity", m=m, name="amenities"
        )

        m.fit_bounds(m.get_bounds(), padding=(30, 30))

        folium.LayerControl().add_to(m)

    st_data = st_folium(m, height=400, width=1000)

