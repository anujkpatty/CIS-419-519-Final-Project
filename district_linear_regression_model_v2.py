# -*- coding: utf-8 -*-
"""district_linear_regression_model v2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1u7Z8Qf0LMVGpw67DWnXPKxv_Jlok8uUv
"""

# Import external libraries

import numpy as np
import pandas as pd
import os
from pathlib import Path

from sklearn import datasets, linear_model
from sklearn.model_selection import train_test_split
from matplotlib import pyplot as plt

from google.colab import drive
drive.mount('/content/drive')

"""## Preprocessing

#### Loading and merging the files

We will build a dataset from two sources: Edfacts.org and the National Center for Educational Statistics.

Edfacts.org contains annual achievement data for school districts. Specifically, it contains district performance on statewide standardized assessments. Our target variable is the district's percentage of fourth-grade students who passed the statewide math exam.

We will load this data from school years 2009-10 through 2015-16.
"""

# Load and append assessments files

assessments_dir = "/content/drive/MyDrive/419_519 Final Project/raw_data/assessments"
df_assess = pd.DataFrame(columns=['year'])
for file in os.listdir(assessments_dir):
  if file.endswith(".csv"):
    data = pd.read_csv(f"{assessments_dir}/{Path(file).stem}.csv")
    # Keep only data for 4th grade students
    data = data.loc[(data['grade_edfacts']==4) & 
                    (data['race']==99) &
                    (data['sex']==99) & 
                    (data['lep']==99) & 
                    (data['homeless']==99) &
                    (data['migrant']==99) & 
                    (data['disability']==99) & 
                    (data['econ_disadvantaged']==99) & 
                    (data['foster_care']==99) & 
                    (data['military_connected']==99)]
    # Create column for school year
    data['year'] = Path(file).stem[-4:]
    df_assess = pd.concat([df_assess,data])

df_assess = df_assess[['year','leaid_num','lea_name','math_test_pct_prof_midpt']]

print(df_assess.shape)
df_assess.head()

"""The National Center for Education Statistics contains data we will use as our features. Specifically, their Elementary and Secondary Information System (ELSi)  contains district financial and demographic data. We will load their data for school years 2011-12 through 2015-16. """

# Load ELSi data

filepath = "/content/drive/MyDrive/419_519 Final Project/raw_data/elsi/ELSI_csv_export_6375254678874229446831.csv"
df_elsi = pd.read_csv(f"{filepath}")

# Reshape file wide to long
df_elsi.columns = df_elsi.columns.map(lambda x : x.replace("-",""))

stub_names = [c[:-6] for c in df_elsi.columns if c[-2:]=='16'] # allows us to get column names for single year

df_elsi_long = pd.wide_to_long(df_elsi, stub_names, i="Agency ID  NCES Assigned [District] Latest available year", j="Year")

# Recoding year
df_elsi_long.reset_index(inplace=True)
df_elsi_long['Year'] = df_elsi_long['Year'].apply(lambda x : int(str(x)[:-2]) + 1)

# Adding ID variable
df_elsi_long['leaid_num'] = df_elsi_long['Agency ID  NCES Assigned [District] Latest available year']

print(df_elsi_long.shape)
df_elsi_long.head()

"""We will merge the EdFacts file with the ELSi file on school district ID and school year."""

# Convert case of ELSI dataframe columns
df_elsi_long.columns = df_elsi_long.columns.map(lambda x : x.lower().replace(" ","_"))

# Merge
df_elsi_long['year'] = df_elsi_long['year'].astype(int)
df_elsi_long['leaid_num'] = df_elsi_long['leaid_num'].astype(int)
df_assess['year'] = df_assess['year'].astype(int)
df_assess['leaid_num'] = df_assess['leaid_num'].astype(int)

df = pd.merge(df_elsi_long,df_assess,on=['year','leaid_num'])

print(df.shape)
df['year'].value_counts()

# TARGET: math_test_pct_prof_midpt
# KEY: year and leaid_num

"""####Feature extraction: prior-year achievement

We will create a new feature to increase the predictive strength of our model: prior-year achievement. Specifically, this featuers contains the percentage of fourth-grade students who passed the statewide math exam during the previous school year. We will lose some data since not all districts have prior-year data.
"""

# Capturing prior-year achievement

df['prior_achiev'] = None

for index, row in df.iterrows():
  prior_record = df.loc[(df['leaid_num']==row['leaid_num']) & (df['year']==row['year']-1)]['math_test_pct_prof_midpt']
  prior_achiev = None
  if prior_record.shape[0]>0:
    prior_achiev = prior_record.values[0]
  df.at[index,'prior_achiev'] = prior_achiev

"""#### Standardizing and scaling the data

We will transform our features through standardization and scaling. We will also impute missing values with the feature mean.
"""

#Standardization
from sklearn.preprocessing import StandardScaler

#columns to be standardized
column_names = ['total_number_of_public_schools_[public_school]_',
'total_students_all_grades_(excludes_ae)_[district]_',
'limited_english_proficient_(lep)_/_english_language_learners_(ell)_[district]_',
'individualized_education_program_students_[district]_',
'free_lunch_eligible_[public_school]_',
'grades_18_students_[district]_',
'grades_912_students_[district]_',
'grade_4_students_[district]_',
'american_indian/alaska_native_students_[district]_',
'asian_or_asian/pacific_islander_students_[district]_',
'hispanic_students_[district]_',
'black_students_[district]_',
'white_students_[district]_',
'hawaiian_nat./pacific_isl._students_[district]_',
'two_or_more_races_students_[district]_',
'total_revenue_(totalrev)_per_pupil_(v33)_[district_finance]_',
'total_revenue__local_sources_(tlocrev)_per_pupil_(v33)_[district_finance]_',
'total_revenue__state_sources_(tstrev)_per_pupil_(v33)_[district_finance]_',
'total_revenue__federal_sources_(tfedrev)_per_pupil_(v33)_[district_finance]_',
'total_current_expenditures__instruction_(tcurinst)_per_pupil_(v33)_[district_finance]_',
'total_current_expenditures__support_services_(tcurssvc)_per_pupil_(v33)_[district_finance]_',
'total_current_expenditures__other_elsec_programs_(tcuroth)_per_pupil_(v33)_[district_finance]_',
'total_current_expenditures__salary_(z32)_per_pupil_(v33)_[district_finance]_',
'total_current_expenditures__benefits_(z34)_per_pupil_(v33)_[district_finance]_',
'total_expenditures_(totalexp)_per_pupil_(v33)_[district_finance]_',
'total_expenditures__capital_outlay_(tcapout)_per_pupil_(v33)_[district_finance]_',
'total_current_expenditures__non_elsec_programs_(tnonelse)_per_pupil_(v33)_[district_finance]_',
'total_current_expenditures_(tcurelsc)_per_pupil_(v33)_[district_finance]_',
'instructional_expenditures_(e13)_per_pupil_(v33)_[district_finance]_',
'teacher_salaries__special_education_programs_(z36)_[district_finance]_',
'teacher_salaries__regular_education_programs_(z35)_[district_finance]_',
'teacher_salaries__vocational_education_programs_(z37)_[district_finance]_',
'total_general_revenue_(totalrev)_[district_finance]_',
'total_revenue__local_sources_(tlocrev)_[district_finance]_',
'total_revenue__state_sources_(tstrev)_[district_finance]_',
'total_revenue__federal_sources_(tfedrev)_[district_finance]_',
'total_current_expenditures__elsec_education_(tcurelsc)_[district_finance]_',
'total_current_expenditures__instruction_(tcurinst)_[district_finance]_',
'total_current_expenditures__support_services_(tcurssvc)_[district_finance]_',
'total_current_expenditures__other_elsec_programs_(tcuroth)_[district_finance]_',
'total_current_expenditures__salary_(z32)_[district_finance]_',
'total_current_expenditures__benefits_(z34)_[district_finance]_',
'prior_achiev']

from sklearn.impute import SimpleImputer
imp = SimpleImputer(missing_values=np.nan, strategy='mean')

# Recoding NAs
for c in column_names:
  df[c] = df[c] = [float("NaN") if "???" in str(x) or "???" in str(x) or "???" in str(x) else x for x in df[c]]
  df[c] = df[c].astype(float)

# Defining X and y 
X = df[column_names+['math_test_pct_prof_midpt']]
X = X.dropna() # drop rows with missing values 
y = X['math_test_pct_prof_midpt']
X = X.drop(columns='math_test_pct_prof_midpt')

# Imputing missing values with mean
#X_imputed = imp.fit_transform(X)
X_standardized = pd.DataFrame(StandardScaler().fit_transform(X),columns=column_names)

print(X_standardized.shape)
X_standardized.head()

"""#### Feature Selection: keeping linearly independent and predictive features 

In order to ensure our regression meets the independence assumption, we will only keep features that are linearly independent and show a correlation with our target.
"""

def correlation(df, dep):
    
  #Create correlation matrix 
  maincor = df.corr()

  #Create dataframe without dependent variable 
  nodep = df
  nodep = nodep.drop(columns=[dep])
  
  # Create new list, answer, to store selected features 
  answer = list()

  # Create empty list (=discard pile) to store features that are:
    #1. Moderately/strongly correlated (r > .7) to one of the selected features (i.e. multicollinear) 
    #2. Has weaker correlation with the output variable than the aforementioned feature.
  discard = set()

  # Find all features correlated (r < .99) to the output variable including negative correlations. 
  # Store results to an arrayk high_cors.
  #print(maincor.shape)
  high_cors =  maincor.loc[(maincor[dep].abs()>0) & (maincor[dep] !=1)]

  for index, row in high_cors.sort_values(by=dep,ascending=False).iterrows():
    # Starting with the highest-correlating feature in the list,
    # Skip if in discard pile
    if index in discard or index==dep:
      continue
    # Else, store in answer pile and move all linearly dependent features to discard poile 
    else:
      newcor = nodep.corr() 
      prison = newcor.loc[(newcor[index] > 0.9) & (newcor[index] != 1)].index
      discard.update(prison)
    answer.append(index) 
  
  #If answer list is empty, return string that says 'No results'. 
  #Else return answer list.
  if len(answer)==0:
    return 'No results'
  else:
    return answer

X_standardized.insert(0,'target',y)
results = correlation(X_standardized,'target') 
print("Features remaining: ", len(results))
X_select = X_standardized[results]
X_select.head()

"""# Test Harness and Cross-Validation with Regression

Our model evaluation will be ten-fold cross-validation. We will explore six approaches to our regression:



*   Linear regression with financial features
*   Linear regression with financial and student demographic features
*   Linear regression with financial, student demographic, and prior-year performance features
*   Polynomial regression with financial features
*   Polynomial regression with financial and student demographic features
*   Polynomial regression with financial, student demographic, and prior-year performance features








"""

from sklearn.preprocessing import PolynomialFeatures

# Capture feature categories
finance = [c for c in X_select.columns if 'finance' in c]
demographics = [c for c in X_select.columns if '[district]' in c]
prior_achievement = ['prior_achiev']

# Prepare inputs (linear regression)
inputs = {}
inputs['Lin_F'] = X_select[finance]
inputs['Lin_FD'] = X_select[finance+demographics]
inputs['Lin_FDP'] = X_select[finance+demographics+prior_achievement]

# Prepare inputs (polynomial feature expansion)
inputs['Poly_F'] = PolynomialFeatures(2).fit_transform(X_select[finance])
inputs['Poly_FD'] = PolynomialFeatures(2).fit_transform(X_select[finance+demographics])
inputs['Poly_FDP'] = PolynomialFeatures(2).fit_transform(X_select[finance+demographics+prior_achievement])

import sklearn
from sklearn import model_selection

names = ['Lin_F','Lin_FD','Lin_FDP','Poly_F','Poly_FD','Poly_FDP']
scoring='neg_root_mean_squared_error'
results = []
table = []

for name in names:
  # get model
  model = sklearn.linear_model.LinearRegression()

  # do cross-validation
  kfold = model_selection.KFold(n_splits=10)
  cv_results = model_selection.cross_val_score(model, inputs.get(name), y, cv=kfold, scoring=scoring)
  results.append(cv_results)
  table.append([name,np.min(cv_results),np.max(cv_results),cv_results.mean(),cv_results.std()])


# boxplot of algorithm comparison
fig = plt.figure()
fig.suptitle('Algorithm Comparison')
ax = fig.add_subplot(111)
plt.boxplot(results)
ax.set_xticklabels(names)
plt.savefig("boxplot_r2_comparison.png")
plt.show()

# table of algorithm comparison
table2 = pd.DataFrame(data=table,columns=['Model','Score (Min)','Score (Max)','Score (Mean)','Score (Std)'])
print(table2)
table2.to_csv("overall_score_comparison.csv",index=False)

# Scatterplot of fitted lines
''' graph 1: scatterplot of data points for the 'prior_achiev' feature
    and a fitted regression line from Lin_FDP model
    
    graph 2: scatterplot of data points for the 'prior_achiev' feature
    and a fitted regression curve from Poly_FDP curve'''

# Plot actual vs. predictived values

X_train, X_test, y_train, y_test = train_test_split(X_select, y, test_size=0.2)
# print(X_train.shape, y_train.shape)
# print(X_test.shape, y_test.shape)

# fit the model
lm = linear_model.LinearRegression()
model = lm.fit(X_train, y_train)
predictions = lm.predict(X_test)

## The line / model
plt.scatter(y_test, predictions)
plt.xlabel("True Values")
plt.ylabel("Predictions")
plt.savefig("scatterplot_predicted_vs_actual.png")
print ("Score:", model.score(X_test, y_test))

#linear regression+finance features