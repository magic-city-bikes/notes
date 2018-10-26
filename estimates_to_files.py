from os import listdir, sep
from os.path import isfile
import pandas as pd
import sys
import json
import time
import datetime
from scipy.optimize import curve_fit
from scipy.stats import expon
import math
from dateutil import tz

def get_files_from_folder(data_path):
    for p in listdir(data_path):
        if p.endswith('.csv'):
            yield '{}{}{}'.format(data_path, sep, p)

def add_columns(df):
  df['date'] = df.ts.apply(lambda x: pd.to_datetime(x, utc=True))
  df['hour'] = df.date.apply(lambda x: x.hour)
  df['minutes_from_midnight'] = df['ts'].apply(lambda x: int(x[11:13]) * 60 + int(x[14:16]))
  df['weekday'] = df['date'].apply(lambda x: x.weekday())
  df['weekend'] = df['weekday'].apply(lambda x: x > 4)
  df['bike_added'] = df.apply(lambda x: df.iloc[(x.name - 1 if x.name > 0 else 0)]['bikes'] < x['bikes'] , axis=1)
  df['bike_removed'] = df.apply(lambda x: df.iloc[(x.name - 1 if x.name > 0 else 0)]['bikes'] > x['bikes'] , axis=1)
  print('dataframe shape after added columns', df.shape)
  return df

def add_waiting_time_for_next_bike(df):
  s = time.time()
  print('adding waiting time for next bike brought')
  i = 0
  first_non_additive_index = 0
  while (i < len(df)):
    while (i < len(df) and df.iloc[i]['bike_added'] == False):
        i += 1
    if (i >= len(df)):
        break
    additive_row = df.iloc[i]
    current_time = additive_row['minutes_from_midnight']
    # add running time based on hour
    times_until_now = df.loc[first_non_additive_index:i-1, 'minutes_from_midnight']
    difference_1 = abs(current_time - times_until_now)
    df.loc[first_non_additive_index:(i-1 if i > 0 else 0), 'wait_for_new_bike'] = difference_1
    first_non_additive_index = i
    i += 1
    # if we can't know when the next bike will be added, fill with -1 for now
  df = df.fillna(-1)
  e = time.time()
  dur = e-s
  print('Adding waiting times took', str(dur), 'seconds')
  return df

def add_waiting_time_for_next_bike_take(df):
  s = time.time()
  print('adding waiting time for next bike take')
  i = 0
  first_non_removing_index = 0
  while (i < len(df)):
      while (i < len(df) and df.iloc[i]['bike_removed'] == False):
          i += 1
      if (i >= len(df)):
          break
      removing_row = df.iloc[i]
      current_time = removing_row['minutes_from_midnight']
      times_until_now = df.loc[first_non_removing_index:i-1, 'minutes_from_midnight']
      difference = abs(current_time - times_until_now)
      df.loc[first_non_removing_index:(i-1 if i > 0 else 0), 'wait_for_bike_taken'] = difference
      first_non_removing_index = i
      i += 1
  # if we can't know when the next bike will be taken, fill with -1 for now
  df = df.fillna(-1)
  e = time.time()
  dur = e-s
  print('Adding waiting times took', str(dur), 'seconds')
  return df

def merge_with_weather_data(df, weather_data_file):
  print('merging bike data with weather data')
  weather = pd.read_csv(weather_data_file)
  weather = weather.fillna(method='pad')
  weather['merge_timestamp'] = weather.apply(lambda x: '%s/%s/%s %s' % (x['Year'], x['m'], x['d'], x['Time']), axis=1)
  df['merge_timestamp'] = df.apply(lambda x: '%s/%s/%s %s' % (x['date'].year, x['date'].month, x['date'].day, x['date'].strftime('%H:00')), axis=1)
  df = pd.merge(df, weather, on='merge_timestamp')
  df = df.drop(columns=['Year', 'm', 'd', 'Time', 'Time zone', 'merge_timestamp'])
  print('done')
  return df

def clean_data(df):
  max_wait_counts = df['max_wait_for_new_bike'].value_counts()
  wait_counts = df['wait_for_bike_taken'].value_counts()
  cleaned_df = df.drop(columns=['index', 'ts', 'sid', 'hour_and_minutes', 'name', 'bike_added', 'bike_removed', 'lat', 'lon', 'bikes', 'total_slots', 'minutes_from_midnight', 'date'])
# remove outliers = if theres less than 10 data points of a specific waiting time
  filterable_max_waits = max_wait_counts[max_wait_counts < 10].index
  filterable_waits = wait_counts[wait_counts < 10].index
  cleaned_df = cleaned_df[~cleaned_df['max_wait_for_new_bike'].isin(filterable_max_waits)]
  cleaned_df = cleaned_df[~cleaned_df['wait_for_bike_taken'].isin(filterable_waits)]
  print('removed', len(df) - len(cleaned_df), 'rows')
  return df

def expfunc(x, l):
    return l * math.e ** (-l * x)

def get_estimate(scale):
    return expon.ppf(0.75, scale=1/scale).item()

def learn_parameter(waits):
    return curve_fit(expfunc, waits.keys(), waits.values, p0=0)

def build_estimtes(cleaned_df):
  print('building estimates')
  estimates = []
  rain_limit = 0.2
  temp_limit = 20
  weekdays = ['Monday', 'Tuesday', 'Wednesdy', 'Thursday', 'Friday', 'Saturday', 'Sunday']
  for weekday in range(7):
      for hour in range(24):
          curr_data = cleaned_df[(cleaned_df.weekday == weekday) & (cleaned_df.hour == hour)]
          bike_brought = curr_data['wait_for_new_bike'].value_counts(normalize=True).sort_index()
          bike_taken = curr_data['wait_for_bike_taken'].value_counts(normalize=True).sort_index()
          # according to temperature
          cold = curr_data[curr_data['Air temperature (degC)'] < temp_limit]
          cold_bike_brought = cold['wait_for_new_bike'].value_counts(normalize=True).sort_index()
          cold_bike_taken = cold['wait_for_bike_taken'].value_counts(normalize=True).sort_index()
          warm = curr_data[curr_data['Air temperature (degC)'] >= temp_limit]
          warm_bike_brought = warm['wait_for_new_bike'].value_counts(normalize=True).sort_index()
          warm_bike_taken = warm['wait_for_bike_taken'].value_counts(normalize=True).sort_index()
          # according to amount of rain
          no_rain = curr_data[curr_data['Precipitation intensity (mm/h)'] < rain_limit]
          with_rain = curr_data[curr_data['Precipitation intensity (mm/h)'] >= rain_limit]
          no_rain_bike_brought = no_rain['wait_for_new_bike'].value_counts(normalize=True).sort_index()
          no_rain_bike_taken = no_rain['wait_for_bike_taken'].value_counts(normalize=True).sort_index()
          rain_bike_brought = with_rain['wait_for_new_bike'].value_counts(normalize=True).sort_index()
          rain_bike_taken = with_rain['wait_for_bike_taken'].value_counts(normalize=True).sort_index()
          if len(bike_brought.values) == 0 or len(rain_bike_brought.values) == 0 or len(warm.values) == 0:
              continue
          if len(bike_taken.values) == 0 or len(rain_bike_taken.values) == 0:
              continue
          # fit exponential distribution to curve
          # bike brought to station
          # amnt of rain
          rain_popt_brought, _ = learn_parameter(rain_bike_brought)
          no_rain_popt_brought, _ = learn_parameter(no_rain_bike_brought)
          # temperature
          warm_popt_brought, _ = learn_parameter(warm_bike_brought)
          cold_popt_brought, _ = learn_parameter(cold_bike_brought)
          # bike taken from station
          # amnt of rain
          rain_popt_taken, _ = learn_parameter(rain_bike_taken)
          no_rain_popt_taken, _ = learn_parameter(no_rain_bike_taken)
          # temperature
          warm_popt_taken, _ = learn_parameter(warm_bike_taken)
          cold_popt_taken, _ = learn_parameter(cold_bike_taken)
          # get estimates
          # bike brought to station
          # amnt of rain
          rain_bike_brought = get_estimate(rain_popt_brought[0])
          no_rain_bike_brought = get_estimate(no_rain_popt_brought[0])
          # temp
          warm_bike_brought = get_estimate(warm_popt_brought[0])
          cold_bike_brought = get_estimate(cold_popt_brought[0])
          # bike taken from station
          # amnt of rain
          rain_bike_taken = get_estimate(rain_popt_taken[0])
          no_rain_bike_taken = get_estimate(no_rain_popt_taken[0])
          # temp
          warm_bike_taken = get_estimate(warm_popt_taken[0])
          cold_bike_taken = get_estimate(cold_popt_taken[0])
          # build estimation dictionary
          estimates.append({
              'sid': str(cleaned_df['sid'][0]),
              'name': str(cleaned_df['name'][0]),
              'weekday': int(weekday),
              'hour': hour,
              'label': weekdays[weekday],
              # rain
              'rain_bike_brought': rain_bike_brought,
              'no_rain_bike_brought': no_rain_bike_brought,
              # temp
              'warm_bike_brought': warm_bike_brought,
              'cold_bike_brought': cold_bike_brought,
              # rain
              'rain_bike_taken': rain_bike_taken,
              'no_rain_bike_taken': no_rain_bike_taken,
              # temp
              'warm_bike_taken': warm_bike_taken,
              'cold_bike_taken': cold_bike_taken,
              # store the rain and temperature limit
              'rain_limit': rain_limit,
              'temp_limit': temp_limit
          })
  print('got', str(len(estimates)), 'estimates.')
  return estimates

def write_data_to_file(data, filename):
  with open(filename + '.json', 'w') as outfile:
      json.dump(data, outfile)
  print('wrote data to', filename)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Please specify bike data folder and weather data file')
    else:
      start = time.time()
      bike_data_folder = sys.argv[1]
      weather_data_file = sys.argv[2]
      for file in get_files_from_folder(bike_data_folder):
        try:
          file_start = time.time()
          print('processing file', file)
          df = pd.read_csv(file, low_memory=False)
          df = df.drop_duplicates('ts').reset_index()
          df = add_columns(df)
          df = add_waiting_time_for_next_bike(df)
          df = add_waiting_time_for_next_bike_take(df)
          df = merge_with_weather_data(df, weather_data_file)
          estimates = build_estimtes(df)
          # assume that station id and name are the same for all rows
          write_data_to_file(estimates, './data/estimates/' + str(df['name'][0]) + '_' + str(df['sid'][0]) + '_estimates')
          file_end = time.time()
          file_duration = file_end - file_start
          print('processing', str(df['name'][0]), 'took', str(file_duration), 'seconds')
          print('')
        except Exception as e:
          print('error processing file', file, ':', str(e))
          print('continuing')
          print('')
      end = time.time()
      duration = end - start
      print('done :---------------------------------)')
      print('total duration', duration, 'seconds')
