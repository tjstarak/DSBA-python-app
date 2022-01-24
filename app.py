# coding=utf-8
from flask import Flask, redirect, render_template, request, flash, url_for, session
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
from maps import *
from database import *

app_root =  os.path.realpath(os.path.dirname(__file__))




@app.route("/")

@app.route("/")

@app.route("/index/")
def index():
    # Importing data from mySQL
    df = load_norm_df()
    df = df[df['Price'].notna()]
    df_initial = df.groupby("Market type")["Price"].count().reset_index()
    df_initial["Price"] = df_initial["Price"]/ df_initial["Price"].sum() *100
    total_rows = df.shape[0]
    category4 = df_initial["Market type"].tolist()
    values4 = df_initial["Price"].round(1).tolist()
    df = df.dropna()



    list_of_districts = ["Bemowo", "Białołęka", "Bielany", "Mokotów", "Ochota", "Praga-Południe",
                         "Praga-Północ", "Targówek","Ursus", "Ursynów", "Ursynów", "Wawer", "Wesoła", "Wilanów", "Wola", "Włochy", "Śródmieście",
                         "Żoliborz"]

    df = df[df['District'].isin(list_of_districts)]
    df["District"].replace({"Praga-Południe": "Praga Południe", "Praga-Północ": "Praga Północ"}, inplace=True)
    df3 = df.copy()
    total_average_price = df["Price"].mean() / 1000
    total_average_price = round(total_average_price,1)

    total_average_surface = round(df["Surface"].mean(),1)
    total_average_charges = round(df["Monthly charges"].mean(),1)
    total_average_construcion = int(round(df["Construction year"].mean(),0))

    df = df.groupby("District")["Price", "Surface", "Monthly charges", "Construction year"].median().reset_index()

    df = df.sort_values("Price")
    districts1 = df["District"].tolist()
    districts1 = districts1
    values1 = df["Price"]/1000
    values1 = values1.tolist()
    values1 = values1
    values1 = [int(i) for i in values1]

    df2 = df.sort_values("Surface").copy()
    districts2 = df2["District"].tolist()
    values2 = df2["Surface"].round()
    values2 = values2.tolist()
    values2 = [int(i) for i in values2]

    df3['Surface_category'] = df3['Surface'].apply(lambda x: '<20m2' if x < 20 else
                                                    ('20-40m2' if x < 40 else
                                                     ('40-60m2' if x < 60 else
                                                      ('60-80m2' if x < 80 else
                                                       ('80-100m2' if x < 100 else
                                                        ('100-120m2' if x < 120 else ">120m2"))))))


    df3 = df3.groupby("Surface_category")["Price"].count().reset_index()

    df3['sort'] = df3['Surface_category'].apply(lambda x: '1' if x == "<20m2" else
                                                ('2' if x == "20-40m2" else
                                                 ('3' if x == "40-60m2" else
                                                  ('4' if x == "60-80m2" else
                                                   ('5' if x == "80-100m2" else
                                                    ('6' if x == "100-120m2" else
                                                     '7'))))))

    df3 = df3.sort_values("sort").copy()
    categories3 = df3["Surface_category"].tolist()
    values3 = df3["Price"].tolist()


    return render_template("index.html",
                           total_average_price=total_average_price,
                           total_average_surface=total_average_surface,
                           total_average_charges=total_average_charges,
                           total_average_construcion=total_average_construcion,
                           total_rows=total_rows,
                           districts1=districts1,
                           values1=values1,
                           districts2=districts2,
                           values2=values2,
                           categories3=categories3,
                           values3=values3,
                           category4=category4,
                           values4=values4
                           )


@app.route("/map_price/", methods=['GET','POST'])
def map_price():
    choropleth(value="price")
    return render_template("file_map.html")

@app.route("/map_surface/", methods=['GET','POST'])
def map_surface():
    choropleth(value="surface")
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

        db_df = load_norm_df()
        db_df['Price per sqm'] = db_df['Price'] / db_df['Surface']
        print(db_df.columns)

        plt.ioff()
        fig, ax1 = plt.subplots()
        ax1.hist(np.clip(db_df.loc[db_df["Building type"] == apt_df["Building type"][0],"Price per sqm"],5000,25000),density=True,bins=20)
        ax1.title.set_text("Building type")
        ax1.set_xlabel("Price per sqm (PLN)")
        ax1.set_yticks([])
        ax1.set_ylabel("Relative frequency")
        ax1.axvline(valuation_sqm,ymax=1,color="r",linewidth=3,linestyle="--")

        fig_path = os.path.join(app_root, "static/img/hist_building_type.png")
        fig.savefig(fname=fig_path)
        plt.close(fig)

        fig, ax1 = plt.subplots()
        ax1.hist(np.clip(db_df.loc[db_df["Property condition"] == apt_df["Property condition"][0],"Price per sqm"],5000,25000),density=True,bins=20)
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

@app.route("/scraper_sale/", methods=['GET', 'POST'])
def scraper_sale():
    offers_card = "n/a"
    price_card = "n/a"
    district_card = "n/a"
    surface_card = "n/a"
    save_mode = ""

    file_download_file = os.path.join(app_root, "static\Scraped_data.xlsx.csv")
    print((file_download_file))
    # Create the pandas DataFrame
    df = pd.DataFrame(columns=['Price',
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

    # Executed after button click
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
                if offers_to_scrape_current == int(offers_to_scrape):
                    break
                else:
                    continue

        if save_mode == 'excel':
            df.to_csv(file_download_file, encoding='utf-8-sig')
        else:
            append_df(normalize_df(get_clean_df(df)))
        abc = load_norm_df()
        print(abc.shape)
        # Data preparation for card display
        clean_df = get_clean_values(df)
        offers_card = len(clean_df.index)
        price_card = int(clean_df["Price"].mean() / 1000)
        district_card = len(set(clean_df["District"]))
        surface_card = clean_df["Surface"].mean()
        surface_card = round(surface_card,1)

    return render_template("scraper_sale.html",
                           tables=[df.to_html(justify="right",
                                   classes='table table-bordered',
                                   table_id='dataTables',
                                   render_links=True,
                                   index=False,
                                   col_space = "200px").replace('<td>', '<td align="right">')],
                           offers_card=offers_card,
                           price_card=price_card,
                           district_card=district_card,
                           surface_card=surface_card,
                           save_mode=save_mode,
                           file_download_file=file_download_file)


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
