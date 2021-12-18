import pandas as pd

offers = pd.read_excel("C:/Users/tomasz.starakiewicz/Documents/GitHub/DSBA-python-app/database/scraped_data_rental.xlsx")

print(offers.head(10))

# Currency cleaning
is_pln = offers["Price"].str.match(pat=".*zł",case=False,na=False)
is_eur = offers["Price"].str.match(pat=".*eur",case=False,na=False)
offers.loc[is_pln, "Currency"] = "PLN"
offers.loc[is_eur, "Currency"] = "EUR"
is_neither = ~(is_pln) & ~(is_eur)
offers.loc[is_neither, "Currency"] = "NA"
offers["Price_clean"] = pd.to_numeric(offers["Price"].str.replace("Zapytaj o cenę","",case=False).str.replace(" ","").str.replace("zł","",case=False).str.replace("EUR","",case=False).str.replace(",","."))



