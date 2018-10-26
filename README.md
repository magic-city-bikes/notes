# Magic City Bikes

Joni Salmi
Irene Nikkarinen
Kristiina Rahikainen

Introduction to Data Science miniproject for predicting when a HSL city bike will be added and when one will be taken from a city bike station.

## Link to deliverable

### How it works:

Estimates are calculated for each station separately based on 2 years worth of data. There are different estimates for rainy/not rainy weather and warm/cold weather for each weekday and hour. The current weather is queried from opendata.fmi.fi, and the correct estimate is displayed. If there are no bikes, the estimate for next bike brought is not shown. New weather data is queried and estimates chosen every ten minutes.

We used the application [kaupunkifillarit.fi](https://github.com/sampsakuronen/kaupunkifillarit-web) as a basis for our project.

## Data

We combined data on the HSL city bike stations and weather data.

### HSL city bikes
TODO: Describe data used and how it was gathered

### Weather

Weather data was collected from FMI. For the models we downloaded weather observations from the Kumpula observation station from the [FMI website](https://en.ilmatieteenlaitos.fi/download-observations#!/) as a CSV file.

Empty values in the weather data were filled with last known value. Only temperature and the amount of rain is used in the final model we used.

For the [application](https://github.com/magic-city-bikes/magic-city-bikes-web) the real-time weather data is collected from [FMI's API for getting weather observations for the Kumpula observation station](http://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature&storedquery_id=fmi::observations::weather::timevaluepair&fmisid=101004&parameters=r_1h,t2m&starttime=2018-10-25T11:39:10.992Z). The observations are from the last hour at 10 minute intervals. The average of the temperature and amount of rain from the last hour is used.

### Problems
Same timezone in weather and bike stations (UTC)

HSL API's station identifiers not consistent

Missing timestamps --> assume that no bike was brought or taken

## Estimates

### Preprocessing
Since the problem we're trying to solve was how long one would have to wait for a bike to be taken or brought to a station, the first thing we had to do was calculate the waiting times for each timestamp we had. We did this by adding a boolean column stating whether a bike was added or removed at a specific moment, and then calculating the amount of minutes passed in between. This was surely the slowest part of our analyser. We also calculated the amount of time the station had been idle for, since we thought this might be useful in regression.

We then removed any duplicates ans waiting times which appeared less than 10 times, assuming that they are outliers and would distort the estimates.

The weather and bike usage data was merged based on hour. This way we ended up with a dataframe containing the waiting times and information about the temperature and amount of rain.

### What we tried (and failed)
The first thing we tried was linear regression. Some of the features the prediction was based on were: The amount of time the station had been idle, month of year, hour of day, if the day was a weekday or weekend, percentage of bikes at the station, temperature and amount of clouds. It soon became clear that this was not a linear problem, as the results were rather poor.

We then tried using a neural network for producing the waiting time, but the network only learned to predict the mean of waiting times. We also turned the problem into a classification task by dividing waiting times to different ranges and trying to predict the range from the same features. This didn't work either, and the network ended up predicting the most common class. This can be due to many things: notably not using enough data, bad network arcitecture, not doing enough hyperaparameter optimization or general lack of experience on our side.

Finally, we noticed that these two graphs we had plotted early on look rather familiar:

Distribution of waiting times for next bike **taken from** Kamppi station:
![Distribution of wait for next bike taken from station](/pics/bike_take.png)

Distribution of waiting times for next bike **brought to** Kamppi station:
![Distribution of wait for next bike brought to station](/pics/bike_brought.png)

### Final implementation

TODO: Joni Teaching the exponential distribution parameter, confidence interval

Calculate waiting time distribution for each weekday and hour

Learn parameter for exponential distribution using sklearn

Divided dataset to rainy (over 0.2mm) and not rainy, warm (temperature over 20 c) and built estimates separately for each case. See the current weather from the API and choose correct estimate. We didn't build estimates for combinations, so for example for cold and rainy and warm and rainy weather we will show the rainy prediciton, as we think that rain has a bigger influence on cyclists than temperature.

Confidence interval used: 0.75

The estimates are written to separate files using `estimates_to_files.py`.

## Who did what
