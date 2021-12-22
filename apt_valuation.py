import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.model_selection import cross_val_score, KFold

import pickle

def train_model(dataset, indep, dep):
    Y = dataset.loc[:, dep]
    X = dataset.loc[:, indep] 

    seed = 7
    test_size = 0.33
    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=test_size, random_state=seed)
    model = XGBRegressor()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    score = model.score(X_train, y_train)
    print("Model score: ", score)
    scores = cross_val_score(model, X_train, y_train, cv=10)
    print("Mean cross validation score: %.2f" % scores.mean())

    kfold = KFold(n_splits=10, shuffle=True)
    kf_cv_scores = cross_val_score(model, X_train, y_train, cv=kfold )
    print("K-fold CV average score: %.2f" % kf_cv_scores.mean())

    mse = mean_squared_error(y_test, y_pred)
    print("RMSE: %.2f" % mse**0.5)
    return model

def save_model(model):
    model_path = "database/valuation_model.dat"
    pickle.dump(model, open(model_path,"wb"))
    return model_path

def load_model(model_path):
    loaded_model = pickle.load(open(model_path, "rb"))
    return loaded_model


def value_apartment(apt_params, val_model):
    model_features = val_model.get_booster().feature_names
    # Drop all params not featured in the model
    apt_params_checked = apt_params[apt_params.columns.intersection(model_features)]
    print(apt_params_checked)
    valuation = val_model.predict(apt_params_checked)
    return valuation

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

if __name__ == "__main__":
    offers_excel = pd.read_excel("database/scraped_data_rental.xlsx")
    offers_clean = get_clean_values(offers_excel)
    
    # offers = offers_excel.merge(right=offers_clean,left_index=True,right_index=True,suffixes=(None,"_clean"))
    # offers["Price per sqm"] = offers["Price_clean"] / offers["Surface_clean"]

    num_vars = ["Surface", "Monthly charges","Floor","Construction year","Number of rooms"]
    predicted = ["Price"]

    offers2 = offers_clean.loc[:,num_vars + predicted].dropna()

    trained_model = train_model(offers2, num_vars, predicted)

    save_model(trained_model)