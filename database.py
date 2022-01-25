import sqlalchemy as db
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import numpy as np

engine_string = "mysql+mysqlconnector://remote_user:pyth0nproj@46.101.184.189:3306/pythonproj"

def get_clean_values(offers, user_input = False):
    clean_values = pd.DataFrame(np.nan,index=range(0,offers.shape[0]),columns=["Currency", "Price", "Surface", "Floor", "Construction year", "Monthly charges","Number of rooms"])
    
    if user_input == False:
        # Extract Currency
        is_pln = offers["Price"].astype(str).str.match(pat=".*zł",case=False,na=False)
        is_eur = offers["Price"].astype(str).str.match(pat=".*eur",case=False,na=False)
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

def load_norm_df(source = 'app_norm_tbl'):
    eng = db.create_engine(engine_string)
    conn = eng.connect()
    df = pd.read_sql(source, conn)
    norm_tbl_dict, norm_dict = load_norm_tables()
    for col, norm_df in norm_tbl_dict.items():
        df = pd.merge(df, norm_df, how='left', left_on=f'{norm_dict[col]}_id', right_on='id', suffixes=('','_y'))
        df.drop(columns='id_y', inplace=True)
        df.rename(columns={f'{norm_dict[col]}_type' : col}, inplace=True)
        
    df.drop(df.filter(regex='_id$').columns.tolist(), axis=1, inplace=True)
    return df

def reset_db():
    eng = db.create_engine(engine_string)
    conn = eng.connect()
    try: 
        conn.execute('DROP TABLE IF EXISTS app_tbl')
    except SQLAlchemyError as e:
        print(e)
    
    conn.execute('CREATE TABLE app_tbl LIKE backup_tbl')
    conn.execute('INSERT INTO app_tbl SELECT * FROM backup_tbl')
    
    conn.close()
    
def initialize_db(spec, name, foreign_keys = None):
    eng = db.create_engine(engine_string)
    conn = eng.connect()
    conn.execute(f'DROP TABLE IF EXISTS {name}')
    spec_fields = [f'`{key}` {value}' for key, value in spec.items()]
    parsed_spec = ", ".join(spec_fields)
    parsed_foreign_spec = ''
    foreign_spec = []
    if foreign_keys is not None:
        foreign_spec = [f'FOREIGN KEY ({value}_id) REFERENCES {value} (id)' for value in foreign_keys.values()]
        parsed_foreign_key_spec = ',' + ', '.join(foreign_spec)
        parsed_spec += ', ' + ', '.join([f'{value}_id int' for value in foreign_keys.values()])
    conn.execute(f'CREATE TABLE {name} ({parsed_spec}, id int NOT NULL AUTO_INCREMENT,'\
                 f'PRIMARY KEY (id) {parsed_foreign_key_spec})')
    conn.close()
    
def append_df(df, name = 'app_tbl', ix_name = 'id'):
    eng = db.create_engine(engine_string)
    conn = eng.connect()
    result = conn.execute(f'SELECT column_name FROM information_schema.columns WHERE table_schema = "pythonproj"'\
                          f'AND table_name = "{name}"')

    col_list = [row[0] for row in result]
    if ix_name in col_list: col_list.remove('id')
    col_list_esc = [f'`{x}`' for x in col_list]
    col_string = ", ".join(col_list_esc)

    ############################# Tutaj się bawiłem
    print(col_list)
    print(df.columns)
    insert_df = df[['Adress', 'Building type', 'Construction year', 'District', 'Floor', 'Heating type', 'Links', 'Market type', 'Monthly charges', 'Number of floors in building', 'Number of rooms', 'Offer number', 'Ownership', 'Price', 'Property condition', 'Scraping date', 'Surface', 'Title', 'Windows type']]

    insert_df = insert_df.replace({'n/a': None})
    ############################ Tutaj się skończyłem bawić

    placeholders = ", ".join(['%s' for x in col_list])
    insert_string = f'({placeholders})'
    insert_data = list(insert_df.itertuples(index=False, name=None))
    conn.execute(f'INSERT INTO {name} ({col_string}) values {insert_string}', insert_data)
    conn.close()

def load_norm_tables(tbl_dict = None):
    eng = db.create_engine(engine_string)
    conn = eng.connect()
    if tbl_dict is None:
        tbl_dict = {'Building type' : 'building',
                        'Heating type' : 'heating',
                        'Ownership' : 'ownership',
                        'Property condition' : 'prop_cond',
                        'District' : 'district' }
    norm_tbl_dict = {}
    for col, tbl in tbl_dict.items():
        df = pd.read_sql(tbl, conn)
        norm_tbl_dict[col] = df
    conn.close()
    return norm_tbl_dict, tbl_dict

def create_norm_tables(tbl_dict):
    eng = db.create_engine(engine_string)
    conn = eng.connect()

    for col, tbl in tbl_dict.items():
        conn.execute(f'CREATE TABLE IF NOT EXISTS {tbl} ('
                     f'id INT(3) NOT NULL AUTO_INCREMENT,'
                     f'{tbl}_type VARCHAR(50),'
                     f'PRIMARY KEY (id))')
    conn.close()

def drop_norm_tables(tbl_dict):
    eng = db.create_engine(engine_string)
    conn = eng.connect()

    for col, tbl in tbl_dict.items():
        conn.execute(f'DROP TABLE IF EXISTS {tbl}')
    conn.close()

def reset_norm_tables(tbl_dict, source = 'backup_tbl'):
    eng = db.create_engine(engine_string)
    conn = eng.connect()

    for col, tbl in tbl_dict.items():
        conn.execute(f'DELETE FROM {tbl}')
        conn.execute(f'ALTER TABLE {tbl} AUTO_INCREMENT = 1')
        conn.execute(f'INSERT INTO {tbl} ({tbl}_type) '
                     f'SELECT DISTINCT {source}.`{col}` FROM {source}')
    conn.close()

def normalize_df(df):
    norm_tbls, norm_dict = load_norm_tables()
    for col, norm_tbl in norm_tbls.items():
        norm_key = norm_tbl.columns.values.tolist()[1]
        df = pd.merge(df, norm_tbl, how='left',
            left_on=col, right_on=norm_key, suffixes=('', '_y'))
        df.drop(columns=[col, f'{norm_key}'], inplace=True)
        df.rename(columns={'id_y':f'{norm_dict[col]}_id'}, inplace=True)
    return df

def main():
    db_spec = {'Price' : 'double',
             'Title' : 'text',
             'Adress' : 'text',
             'Offer number' : 'bigint',
             'Surface' : 'int',
             'Number of rooms' : 'int',
             'Market type' : 'varchar(200)',
             'Building type' : 'varchar(200)',
             'Floor' : 'int',
             'Number of floors in building' : 'int',
             'Windows type' : 'varchar(200)',
             'Heating type' : 'varchar(200)',
             'Construction year' : 'int',
             'Property condition' : 'varchar(200)',
             'Monthly charges' : 'int',
             'Ownership' : 'varchar(200)',
             'Scraping date' : 'varchar(200)',
             'District' : 'varchar(200)',
             'Links' : 'text'}

    foreign_keys = {'Building type' : 'building',
                    'Heating type' : 'heating',
                    'Ownership' : 'ownership',
                    'Property condition' : 'prop_cond',
                    'District' : 'district' }

    db_norm_spec = { key : value for key, value in db_spec.items() if key in db_spec.keys() - foreign_keys.keys() }

    # Initialize main table according to specification dict and populate it with data scraped earlier, either form backup or stored locally in csv

    initialize_db(db_spec, 'app_tbl')
    df = get_clean_df(load_df('backup_tbl'))
    # df = pd.read_csv('C:/Users/tomasz.starakiewicz/software/GitHub/DSBA-python-app/database/scraped_data_rental.csv')
    append_df(get_clean_df(df), 'app_tbl')

    # Initializa normalization tables

    drop_norm_tables(foreign_keys)
    create_norm_tables(foreign_keys)
    reset_norm_tables(foreign_keys)
    
    # Initialize normalized main table according to spec dict after excluding foreign keys, load data from non-normalized table
    
    initialize_db(db_norm_spec, 'app_norm_tbl', foreign_keys)
    df = normalize_df(load_df('app_tbl'))
    append_df(df, name='app_norm_tbl')

    # Test loading data from normalized table
    df = load_norm_df('app_norm_tbl')

if __name__ == '__main__':
    main()