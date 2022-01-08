# coding=utf-8
from flask import Flask, redirect, render_template, request, flash, url_for
import numpy as np
import pandas as pd
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
from apt_valuation import get_clean_values

app_root =  os.path.realpath(os.path.dirname(__file__))

@app.route("/")

@app.route("/")

@app.route("/index/")
def index():
    return render_template("index.html")

@app.route("/map/")
def map():
   # Super strange method to use non embedded plotly graphs without running Dash app
    districts_url = os.path.join(app_root, "static/geojson/warszawa-dzielnice.geojson")
    map_data_url = os.path.join(app_root, "database/dane_map.csv")
    # Loading both GeoJSON and data
    f = open(districts_url, encoding='utf-8')
    data = json.load(f)


    df = pd.read_csv(map_data_url, dtype={"name": str})

   # Plotting Plotly Choropleth map
    fig = px.choropleth_mapbox(df, geojson=data, locations='name', featureidkey="properties.name", color='value',
                               color_continuous_scale="turbo",
                               range_color=(-0.2, 1),
                               mapbox_style="carto-positron",
                               zoom=9.0, center={"lat": 52.2402, "lon": 21.0},
                               opacity=0.35,
                               # Do not change width and height, it is possible down in code
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
    text = """{% extends "layout.html" %}"
    {% set active_page = "Map" %}


    {% block body %}
          
    <div class="container-fluid"> 
    <div class="d-sm-flex align-items-center justify-content-between mb-4">
    <h1 class="h3 mb-0 text-gray-800">Choropleth map by Warsaw district</h1>
    </div>
    <div class="col-xl-12 col-lg-8" >
    <div class="card shadow mb-4">
    <div   class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
    <h6 id="abc" class="m-0 font-weight-bold text-dark"> Sale price in Warsaw by district</h6>
    </div>
    """ + text + """
    
    </div>

  
    
    </div>
    </div>
    
    {% endblock %}
    """

    # Change of height and width of plot
    #text = text.replace('height":600', 'height":600')
    #text = text.replace('width":1340', 'width":1340')
    file_map_url = os.path.join(app_root, "templates/file_map.html")

    with open(file_map_url, "w") as file:
        file.write(text)
        file.close()

    return render_template("file_map.html")

@app.route("/pricing_tool/", methods=['GET','POST'])
def pricing_tool():
    params = ['surface', 'building_type', 'floor', 'construction_year', 'property_condition', 'rooms', 'monthly_charges']
    model_params = ['Surface', 'Building type', 'Floor', 'Construction year', 'Property condition', 'Number of rooms', 'Monthly charges']

    apt_params = { key : None for key in params}
    model_dict = dict(zip(model_params,params))

    valuation_str = None
    valuation_sqm_str = None

    if request.method == 'POST':
        apt_params = { model_param : [request.form[param]] for model_param, param in model_dict.items()}
        apt_df = pd.DataFrame.from_dict(apt_params)
        apt_df_clean = get_clean_values(apt_df, user_input=True)

        model_path = os.path.join(app_root, "database/valuation_model.dat")
        try:
            valuation_model = apt.load_model(model_path)
        except OSError:
            valuation_model = apt.load_model('path/to/backup/model')
        
        valuation = apt.value_apartment(apt_df_clean, valuation_model)[0]
        valuation_str = f"{valuation:,.0f} zł"
        valuation_sqm = valuation / apt_df_clean['Surface'][0]
        valuation_sqm_str = f"{valuation_sqm:,.0f} zł"

        plt.style.use("seaborn")

        database_path = os.path.join(app_root, "database/scraped_data_rental.xlsx")
        database = apt.load_data(database_path)

        plt.ioff()
        fig, ax1 = plt.subplots()
        ax1.hist(np.clip(database.loc[database["Building type"] == apt_df["Building type"][0],"Price per sqm"],5000,25000),density=True,bins=20)
        ax1.title.set_text("Building type")
        ax1.set_xlabel("Price per sqm (PLN)")
        ax1.set_yticks([])
        ax1.set_ylabel("Relative frequency")
        ax1.axvline(valuation_sqm,ymax=1,color="r",linewidth=3,linestyle="--")

        fig_path = os.path.join(app_root, "static/img/hist_building_type.png")
        fig.savefig(fname=fig_path)
        plt.close(fig)

        fig, ax1 = plt.subplots()
        ax1.hist(np.clip(database.loc[database["Property condition"] == apt_df["Property condition"][0],"Price per sqm"],5000,25000),density=True,bins=20)
        ax1.title.set_text("Property condition")
        ax1.set_xlabel("Price per sqm (PLN)")
        ax1.set_yticks([])
        ax1.set_ylabel("Relative frequency")
        ax1.axvline(valuation_sqm,ymax=1,color="r",linewidth=3,linestyle="--")

        fig_path = os.path.join(app_root, "static/img/hist_property_condition.png")
        fig.savefig(fname=fig_path)
        plt.close(fig)

    render_charts = False
    if valuation_str is not None:
        render_charts = True

    return render_template("pricing_tool.html", valuation=valuation_str, valuation_sqm = valuation_sqm_str, render_charts = render_charts)

@app.route("/scraper_sale/")
def scraper_sale():
    return render_template("scraper_sale.html")


@app.route("/scraper_rental/", methods=['GET', 'POST'])
def scraper_rental():


    # Create the pandas DataFrame
    df = pd.DataFrame( columns=['Price',
                             'Title',
                             'Adress',
                             'Offer number',
                             'Surface',
                             'Number of rooms',
                             'Market type',
                             'Building type',
                             'Floor',
                             'Number of floors in building',
                             'Windows type',
                             'Heating type',
                             'Construction year',
                             'Property condition',
                             'Monthly charges',
                             'Ownership',
                             'Scraping date',
                             'Links'])

    #Executed after button click
    if request.method == "POST":
        offers_to_scrape = request.form['select1']
        sleep_time = request.form['select2']
        save_mode = request.form['select3']



        # Number of pages to scrape
        list_of_links = []
        number_of_pages = 1
        count = []
        all_links = []
        offers_to_scrape_current = 0

        # Lists of scraped data
        scraped_links = []
        scraped_price = []
        scraped_title = []
        scraped_adress = []
        scraped_scraping_date = []
        scraped_unique_offer_number = []
        scraped_surface = []
        scraped_number_of_rooms = []
        scraped_building_type = []
        scraped_market_type = []
        scraped_floor = []
        scraped_total_floors = []
        scraped_window_type = []
        scraped_heating = []
        scraped_construction_year = []
        scraped_finish_condition = []
        scraped_monthly_charge = []
        scraped_ownership_type = []
        list_of_lists = [scraped_surface, scraped_number_of_rooms, scraped_market_type, scraped_building_type,
                         scraped_floor, scraped_total_floors, scraped_window_type, scraped_heating,
                         scraped_construction_year, scraped_finish_condition, scraped_monthly_charge,
                         scraped_ownership_type]

        # Pagination loop, for now page number is hard coded
        for page in range(number_of_pages):

            starting_url = "https://www.otodom.pl/pl/oferty/sprzedaz/mieszkanie/warszawa?description=do+zamieszkania&priceMin=10000&distanceRadius=0&market=ALL&page=" + str(number_of_pages) + "&limit=72&locations=%5Bcities_6-26%5D&by=DEFAULT&direction=DESC"
            html_text = requests.get(starting_url).text
            soup = BeautifulSoup(html_text, "lxml")

            list_of_links = []
            # Creating list with all links on the first page
            for a in soup.find_all('a', href=True, class_="css-jf4j3r es62z2j27"):
                full_link = "https://www.otodom.pl" + str(a['href'])
                if full_link not in all_links:
                    all_links.append(full_link)
                    list_of_links.append(full_link)
                    print(full_link)
                else:
                    continue

            # Looping through all links on list page - list_of_links
            for i, link in enumerate(list_of_links):
                url = list_of_links[i]
                html_text = requests.get(url).text
                soup = BeautifulSoup(html_text, "lxml")

                # Scraping single values from single offer page
                # All values stored in lists

                # Link
                scraped_links.append(url)

                # Price
                try:
                    price = soup.find("strong")
                    scraped_price.append(price.text)
                except:
                    scraped_price.append("n/a")

                    # Offer title
                offer_title = soup.find("h1")
                scraped_title.append(offer_title.text)

                # Address
                adress = soup.find("a", "e1nbpvi60 css-12w6h8t e1enecw71")
                scraped_adress.append(adress.text)
                print(adress.text)

                # Day when scraped
                scraped_scraping_date.append(date.today())

                # Unique offer number
                meta = soup.find("title")
                title_meta = meta.text
                offer_number = title_meta[-24:]
                offer_number = offer_number[:8]
                scraped_unique_offer_number.append(offer_number)

                # Table with atributes, all divs have same class, therefore more comlex method is needed
                atribute = soup.find_all("div", "css-o4i8bk ev4i3ak2")
                value = soup.find_all("div", "css-1ytkscc ev4i3ak0")

                for a, v in zip(atribute, value):

                    if a['title'] == "Powierzchnia":
                        scraped_surface.append(v.text)


                    elif a['title'] == "Liczba pokoi":
                        scraped_number_of_rooms.append(v.text)

                    elif a['title'] == "Rynek":
                        scraped_market_type.append(v.text)

                    elif a['title'] == "Rodzaj zabudowy":
                        scraped_building_type.append(v.text)

                    elif a['title'] == "Piętro":
                        scraped_floor.append(v.text)

                    elif a['title'] == "Liczba pięter":
                        scraped_total_floors.append(v.text)

                    elif a['title'] == "Okna":
                        scraped_window_type.append(v.text)

                    elif a['title'] == "Ogrzewanie":
                        scraped_heating.append(v.text)

                    elif a['title'] == "Rok budowy":
                        scraped_construction_year.append(v.text)

                    elif a['title'] == "Stan wykończenia":
                        scraped_finish_condition.append(v.text)

                    elif a['title'] == "Czynsz":
                        scraped_monthly_charge.append(v.text)

                    elif a['title'] == "Forma własności":
                        scraped_ownership_type.append(v.text)


                    else:
                        continue

                # Checking if some atributes aren't missing, if yes list is appended with "n/a"
                count.append("ok")

                for list_x in list_of_lists:
                    if len(list_x) < len(count):
                        list_x.append("n/a")
                    else:
                        continue

                df = pd.DataFrame(list(zip(
                    scraped_price,
                    scraped_title,
                    scraped_adress,
                    scraped_unique_offer_number,
                    scraped_surface,
                    scraped_number_of_rooms,
                    scraped_market_type,
                    scraped_building_type,
                    scraped_floor,
                    scraped_total_floors,
                    scraped_window_type,
                    scraped_heating,
                    scraped_construction_year,
                    scraped_finish_condition,
                    scraped_monthly_charge,
                    scraped_ownership_type,
                    scraped_scraping_date,
                    scraped_links)),

                    columns=['Price',
                             'Title',
                             'Adress',
                             'Offer number',
                             'Surface',
                             'Number of rooms',
                             'Market type',
                             'Building type',
                             'Floor',
                             'Number of floors in building',
                             'Windows type',
                             'Heating type',
                             'Construction year',
                             'Property condition',
                             'Monthly charges',
                             'Ownership',
                             'Scraping date',
                             'Links'])




                # Waiting before next page request

                offers_to_scrape_current = offers_to_scrape_current + 1
                time.sleep(int(sleep_time))
                print(sleep_time)
                if offers_to_scrape_current == int(offers_to_scrape):
                    break
                else:
                    continue

        if save_mode == 'excel':
            print("sdfsdfsdfsd")
            df.to_csv('Scraped_data.xlsx.csv', encoding='utf-8-sig')

    return render_template("scraper_rental.html",
                           tables=[df.to_html(justify="right",
                                   classes='table table-bordered',
                                   table_id='dataTables',
                                   render_links=True,
                                   index=False,
                                   col_space = "200px").replace('<td>', '<td align="right">')])


# No caching at all for API endpoints.
@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


if __name__ == "__main__":
    app.run(debug=True)
