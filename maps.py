import os
import numpy as np
import pandas as pd
from flask import Flask, redirect, render_template, request, flash, url_for, session
from bs4 import BeautifulSoup
import requests
import time
import random
from datetime import date
import json
import plotly.express as px
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import os
app = Flask(__name__)
app.secret_key = 'secret key'
import apt_valuation as apt
from database import get_clean_values
from maps import *
from database import *

app_root =  os.path.realpath(os.path.dirname(__file__))

def choropleth(value="price"):
    # method to use non embedded plotly graphs without running Dash app
    districts_url = os.path.join(app_root, "static/geojson/warszawa-dzielnice.geojson")

    # Importing data from database
    df = load_norm_df()
    df = df.dropna()

    if value == "price":
        df2 = pd.DataFrame(df.groupby("District")["Price"].mean().round())
    else:
        df2 = pd.DataFrame(df.groupby("District")["Surface"].mean().round())

    df2.reset_index(inplace=True)

    if value == "price":
        df2.rename(columns={'District': 'name', 'Price': 'value'}, inplace=True)
        maximum = 1000
        minimum = df2["value"].min()
    else:
        df2.rename(columns={'District': 'name', 'Surface': 'value'}, inplace=True)
        maximum = 80
        minimum = df2["value"].min()

    list_of_districts = ["Bemowo", "Białołęka", "Bielany", "Mokotów", "Ochota", "Praga-Południe",
                         "Praga-Północ", "Targówek",
                         "Ursus", "Ursynów", "Ursynów", "Wawer", "Wesoła", "Wilanów", "Wola", "Włochy", "Śródmieście",
                         "Żoliborz"]

    df2 = df2[df2['name'].isin(list_of_districts)]
    if value == "price":
        df2["value"] = df2["value"] / 1000
    df2 = df2.round()
    df2["name"].replace({"Praga-Południe": "Praga Południe", "Praga-Północ": "Praga Północ"}, inplace=True)

    # Loading both GeoJSON and data
    f = open(districts_url, encoding='utf-8')
    data = json.load(f)

    # Plotting Plotly Choropleth map
    fig = px.choropleth_mapbox(df2, geojson=data, locations='name', featureidkey="properties.name", color='value',
                               color_continuous_scale="turbo",
                               range_color=(minimum, maximum),
                               mapbox_style="carto-positron",
                               zoom=9.0, center={"lat": 52.2402, "lon": 21.0},
                               opacity=0.7,
                               labels={'value': 'Value', "name": "District"},
                               )

    fig.update_traces(hovertemplate=None)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, hovermode="x")

    # Instead of running dash app, current plot is saved as HTML, then some tags like <head> and <body>
    # are being removed. Then navbar and other divs are being added around generated code.

    map_url = os.path.join(app_root, "templates/map.html")

    fig.write_html(map_url)

    with open(map_url, "r", encoding='utf-8') as f:
        text = f.read()
    f.close()
    text = text[52:-15]

    if value == "price":
        text1 = "Change data to average surface"
        text2 = "Average sale price in Warsaw by district [PLN ths]"
        text3 = "/map_surface/"
    else:
        text1 = "Change data to average price"
        text2 = "Average surface in Warsaw by district [m2]"
        text3 = "/map_price/"


    text = """{% extends "layout.html" %}"
    {% set active_page = "Map" %}
    {% block body %}
    <script>
         function change(){
            document.getElementById("myform").submit();
        }
    </script>
    <div class="container-fluid">
         <form id="myform" method="post">
             <div class="row">
                 <div class="col-xl-9 col-md-6 mb-2">
                         <h1 class="h3 mb-0 text-gray-800">Choropleth map by Warsaw district</h1>
                 </div>
               <div class="col-xl-3 col-md-6 mb-2 align-self-end">
               <a href="""+text3+"""> 
                    <span class="text">""" + text1 + """</span>
                </button>
                </a>
             </div>
         </form>


     <div class="col-xl-12 col-lg-8" >
     <div class="card shadow mb-4">
     <div   class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
     <h6 id="abc" class="m-0 font-weight-bold text-dark">"""+ text2+  """</h6>
     </div>
     """ + text + """
     </div>
     </div>
     </div>
     {% endblock %}
     """

    file_map_url = os.path.join(app_root, "templates/file_map.html")

    with open(file_map_url, "w") as file:
        file.write(text)
        file.close()