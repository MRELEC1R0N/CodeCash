# Import Libraries
import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import datetime as dt
from scipy import stats
import plotly.figure_factory as ff
import plotly.graph_objs as go
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Read CSV file
# Ensure the path is correct; use raw string or forward slashes
df = pd.read_csv(r'model/model_data/stock_market_data/stocks/A.csv')  # Use raw string or forward slashes

# Display the first few rows of the DataFrame
print(df.head())

# Display summary statistics
print(df.describe())

# Rename column
df = df.rename(columns={'Name': 'Ticks'})

# Filter for 'AMZN' entries
amzn = df.loc[df['Ticks'] == 'AMZN']
print(amzn.head())  # Display the first few rows of the filtered DataFrame
