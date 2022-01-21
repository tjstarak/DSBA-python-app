import sqlalchemy as db
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import numpy as np

engine_string = "mysql+mysqlconnector://remote_user:pyth0nproj@46.101.184.189:3306/pythonproj"

def get_clean_values(offers, user_input = False):
    clean_values = pd.DataFrame(np.nan,index=range(0,offers.shape[0]),columns=["Currency", "Price", "Surface", "Floor", "Construction year", "Monthly charges","Number of rooms"])
    
    if user_input == False:
        # Extract Currency
        is_pln = offers["Price"].str.match(pat=".*zł",case=False,na=False)
        is_eur = offers["Price"].str.match(pat=".*eur",case=False,na=False)
        is_neither = ~(is_pln) & ~(is_eur)

        clean_values.loc[is_pln, "Currency"] = "PLN"
        clean_values.loc[is_eur, "Currency"] = "EUR"
        clean_values.loc[is_neither, "Currency"] = np.nan

        # Extract price, ignore decimal
        clean_values["Price"] = pd.to_numeric(offers["Price"].astype(str).str.replace(" ","").str.extract(pat="(\d+)",expand=False))

    # Extract surface, including decimal
    clean_values["Surface"] = pd.to_numeric(offers["Surface"].astype(str).str.replace(" ","").str.replace(",",".").str.extract(pat="(\d+\.?\d*)",expand=False))

    # Extract floor, floors >10 groupped together with 10
    clean_values["Floor"] = pd.to_numeric(offers["Floor"].astype(str).str.replace("parter","0",case=False).str.replace("suterena","-1",case=False).str.extract(pat="(-?\d+)",expand=False))

    # Extract construction year, assume construction year before 1900 is invalid
    clean_values["Construction year"] = pd.to_numeric(offers["Construction year"].astype(str).str.extract(pat="(\d+)",expand=False))
    clean_values[clean_values["Construction year"]<1900] =np.nan
    
    # Extract monthly charges, assume all values are in PLN, ignore decimal
    clean_values["Monthly charges"] = pd.to_numeric(offers["Monthly charges"].astype(str).str.replace(" ","").str.extract(pat="(\d+)",expand=False))

    if user_input == False:
        # Extract district
        clean_values["District"] = offers["Adress"].astype(str).str.replace(" ","").str.extract(pat="\,(.*?)\,",expand=False)

    # Extract rooms, group >5 rooms at 6
    clean_values["Number of rooms"] = pd.to_numeric(offers["Number of rooms"].astype(str).str.replace(" ","").str.extract(pat="(\d+)",expand=False))
    clean_values[clean_values["Number of rooms"]>5] = 6

    return clean_values

def get_clean_df(all_vals):
    clean_vals = get_clean_values(all_vals)

    diff_cols = all_vals.columns.difference(clean_vals.columns)
    clean_df = pd.merge(all_vals[diff_cols], clean_vals, left_index=True, right_index=True, how="inner")
    return clean_df

def load_df(source = 'app_tbl'):
    eng = db.create_engine(engine_string)
    conn = eng.connect()
    df = pd.read_sql(source, conn)
    conn.close()
    return df

def append_df(df):
    eng = db.create_engine(engine_string)
    conn = eng.connect()

    df.to_sql('app_tbl', conn, if_exists='append')

    conn.close()

def reset_db():
    eng = db.create_engine(engine_string)
    conn = eng.connect()
    try: 
        conn.execute('DROP TABLE app_tbl')
    except SQLAlchemyError as e:
        print(e)
    
    conn.execute('CREATE TABLE app_tbl LIKE backup_tbl')
    conn.execute('INSERT INTO app_tbl SELECT * FROM backup_tbl')
    
    conn.close()

def create_norm_tables(source = 'backup_tbl'):
    df = load_df(source)
    tbl_list = ['Building type', 'Heating type', 'Market type', 'Ownership', 'Property condition', 'District'] 
    pass


def main():
    df = load_df()
    tbl_list = ['Building type', 'Heating type', 'Ownership', 'Property condition', 'District'] 
    tbl_names = ['building', 'heating', 'ownership', 'property_condition', 'district']
    tbl_dict = dict(zip(tbl_list, tbl_names))
    print(tbl_dict)

if __name__ == '__main__':
    main()