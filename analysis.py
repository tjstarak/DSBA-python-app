import pandas as pd

offers = pd.read_excel("C:/Users/tomasz.starakiewicz/Documents/GitHub/DSBA-python-app/database/scraped_data_rental.xlsx")

def get_clean_values(offers):
    # Extract currency
    currency = [None] * offers.shape[0]
    is_pln = offers["Price"].str.match(pat=".*zł",case=False,na=False)
    is_eur = offers["Price"].str.match(pat=".*eur",case=False,na=False)
    currency[is_pln, "currency"] = "PLN"
    offers.loc[is_eur, "currency"] = "EUR"
    is_neither = ~(is_pln) & ~(is_eur)
    offers.loc[is_neither, "currency"] = "NA"

    # Extract price, ignore decimal
    price_clean = pd.to_numeric(offers["Price"].astype(str).str.replace(" ","").str.extract(pat="([0-9]+)",expand=False))

    # Extract surface, including decimal
    surface_clean = pd.to_numeric(offers["Surface"].astype(str).str.replace(" ","").str.replace(",",".").str.extract(pat="(\d+\.\d*)",expand=False))

    # Extract floor, floors >10 groupped together with 10
    floor_clean = pd.to_numeric(offers["Floor"].astype(str).str.replace("parter","0",case=False).str.replace("suterena","-1",case=False).str.extract(pat="(-?\d+)",expand=False))

    construction_year_clean = pd.to_numeric(offers["Construction year"].astype(str).str.extract(pat="(\d+)",expand=False))

    # Extract monthly charges, assume all values are in PLN, ignore decimal
    monthly_charges_clean = pd.to_numeric(offers["Monthly charges"].astype(str).str.replace(" ","").str.extract(pat="(\d+)",expand=False))

