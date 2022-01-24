# coding=utf-8
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.model_selection import cross_val_score, KFold

import pickle

def load_data(path):
    offers_excel = pd.read_excel(path)
    offers_clean = get_clean_values(offers_excel)

    diff_cols = offers_excel.columns.difference(offers_clean.columns)
    offers = pd.merge(offers_excel[diff_cols], offers_clean, left_index=True, right_index=True, how="inner")
    vars = ["Surface", "Monthly charges","Floor","Construction year","Number of rooms", "Building type", "Property condition"]
    predicted = ["Price"]

    offers2 = offers.loc[:,vars + predicted].dropna()
    offers2["Price per sqm"] = offers2["Price"] / offers2["Surface"]
    return offers2

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
    valuation = val_model.predict(apt_params_checked)
    return valuation

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