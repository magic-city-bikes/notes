# Magic City Bikes

- Joni Salmi
- Irene Nikkarinen
- Kristiina Rahikainen

Introduction to Data Science miniproject for predicting when a HSL city bike will be added and when one will be taken from a city bike station.

## [Link to deliverable](https://magic-city-bikes.herokuapp.com/)

The application repository can be found [here](https://github.com/magic-city-bikes/magic-city-bikes-web).

### How it works:

Estimates are calculated for each station separately based on data of last three seasons. There are different estimates for rainy/not rainy weather and warm/cold weather for each weekday and hour. The current weather is queried from opendata.fmi.fi, and the correct estimate is displayed. If there are no bikes, the estimate for next bike brought is not shown. New weather data is queried and estimates chosen every ten minutes.

We used the [kaupunkifillarit.fi](https://github.com/sampsakuronen/kaupunkifillarit-web) application as a basis for our project.

![Example use case](/pics/magic-city-bike-use-case.png)

## Data

We combined data on the HSL city bike stations and weather data.

### HSL city bikes

HSL provides comprehensive APIs for all means of public transportation. In this report we focus on the city bike data exclusively which is available at <https://dev.hsl.fi/>. The used APIs are real-time but some limited historical data is available at <https://dev.hsl.fi/citybike/>. The API contains the following information for each station: id, name, coordinates, number of parked bikes, number of parking slots and some status info. Fortunately, we had been collecting the data for three last seasons ourselves. The data collection was conducted by polling the HSL City Bike APIs for past three years with one minute intervals. These snapshots that represent the status of a single station at given time are referred to as events. We had total of 68 million events in the dataset.

We encountered some issues with the event data which we'll describe in more detail here. There were duplicate events caused by bug in our collector and we had to include data deduplication in our pipeline. There were missing events caused by either City Bike API unavailability or errors with the collector. This lead to us making assumptions about data when at most one consecutive snapshot (1 minute) was missing, and discarding some events that happened around the missing events when durations were longer. HSL made changes to the City Bikes network throughout seasons such as relocation of stations, and assigning new identifiers to stations because of that. We considered stations to be the same, if the name of the station was the same throughout seasons and considered them to be distinct otherwise. Another option was to normalize stations based on their coordinates and treat stations as equal if they were close to other station from previous season.

### Weather

Weather data was collected from FMI. For the models we downloaded weather observations from the Kumpula observation station from the [FMI website](https://en.ilmatieteenlaitos.fi/download-observations#!/) as a CSV file. Due to time restrictions we only collected data from the observation station in Kumpula, instead of different weather observation stations nearer each city bike station.

Empty values in the weather data were filled with last known value. Only temperature and the amount of rain is used in the final model we used.

For the [application](https://github.com/magic-city-bikes/magic-city-bikes-web) the real-time weather data is collected from [FMI's API for getting weather observations for the Kumpula observation station](http://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature&storedquery_id=fmi::observations::weather::timevaluepair&fmisid=101004&parameters=r_1h,t2m&starttime=2018-10-25T11:39:10.992Z). The observations are temperature and the amount of rain from the last hour at 10 minute intervals. The average of the temperature and amount of rain from the last hour is used.

### Problems

Some problems we faced with the application were related to timezones and the different ways Python and JavaScript handle dates. We needed to make sure that the weather data and bike data timestamps were in both in the same timezone. The times were in UTC, so that needed to be taken into account when checking the results.

In our estimates created with Python, the weekday is a number where 0 means Monday and so on, due to how Python handles dates. In JavaScript however, weekdays gotten from a date object start from Sunday, so 0 equals Sunday, 1 equals Monday, etc. This needed to be dealt with in the code for adding the estimations to bike stations in the application.

## Estimates

### Preprocessing
Since the problem we're trying to solve was how long one would have to wait for a bike to be taken or brought to a station, the first thing we had to do was calculate the waiting times for each timestamp we had. We did this by adding a boolean column stating whether a bike was added or removed at a specific moment, and then calculating the amount of minutes passed in between. This was surely the slowest part of our analyser. We also calculated the amount of time the station had been idle for, since we thought this might be useful in regression.

We then removed any duplicates and waiting times which appeared less than 10 times, assuming that they are outliers and would distort the estimates.

The weather and bike usage data was merged based on hour. This way we ended up with a dataframe containing the waiting times and information about the temperature and amount of rain.

### What we tried (and failed)
The first thing we tried was linear regression. Some of the features the prediction was based on were: The amount of time the station had been idle, month of year, hour of day, if the day was a weekday or weekend, percentage of bikes at the station, temperature and amount of clouds. It soon became clear that this was not a linear problem, as the results were rather poor.

We then tried using a neural network for producing the waiting time, but the network only learned to predict the mean of waiting times. We also turned the problem into a classification task by dividing waiting times to different ranges and trying to predict the range from the same features. This didn't work either, and the network ended up predicting the most common class. This can be due to many things: notably not using enough data, bad network arcitecture, not doing enough hyperaparameter optimization or general lack of experience on our side.

### Final implementation

We had been exploring the data and plotting it in various ways. While some of these explorations gave some insight to the data, most ended up being useless. At one point we noticed that these two graphs we had plotted early on look rather familiar:

Distribution of waiting times for next bike **taken from** Kamppi station:
![Distribution of wait for next bike taken from station](/pics/bike_take.png)

Distribution of waiting times for next bike **brought to** Kamppi station:
![Distribution of wait for next bike brought to station](/pics/bike_brought.png)

They seemed to resemble exponential distribution. All of us being computer scientists and our statistics knowledge being limited to very basics, we hardly even knew what a exponential distribution existed. So we studied exponential distributions more and found out that confidence intervals could be used for making predictions. We looked into available solutions for fitting an exponential distribution to our existing dataset and landed on [curve_fit](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html) function of the SciPy library.

It didn't make sense to fit the curve to our entire dataset as we had earlier figured out time of the day, day of the week and station being the factors affecting the bike mobility the most. We instead fitted exponential function to waiting times for each hour of each weekday for each station. Having learned parameters for the exponential function we were able to calculate confidence intervals using percent point function (inverse of cdf — percentiles). We chose to use 75% confidence interval as it seemed to give good results.

Now, we could have also used the raw data for calculating the confidence intervals rather than fitting exponential function to the data and predicting based on that. However, the benefits of exponential function was that it could be stored as a single number, a parameter to the function, while the raw event data took over 4GB space. This made calculations and reiterations of confidence interval parameters much faster as well as made it possible to include the data with out application easily.

After that we labelled the dataset with rainy (over 0.2mm) and warm (temperature over 20 c) labels and built estimates separately for each case. See the current weather from the API and choose correct estimate. We didn't build estimates for combinations, so for example for cold and rainy and warm and rainy weather we will show the rainy prediction, as we think that rain has a bigger influence on cyclists than temperature.

For the technical implementation of our solution take a look at the `estimates_to_files.py` file in the repository. In this repository you can also see all the attempted solutions.

# Limitations

At the moment, the project is mostly a proof of concept, and not yet a production level application.

The biggest problem is low maintainability of the predictions. Our application has an impact on how people use the city bikes, so the data should be updated regularly by polling new data. However the process of rerunning is the data rather slow.

In addition, the division between rainy and cold weather is rather harsh. It would be safe to assume that there is a big difference in usage between 18 degrees and 10 degrees. In addition, the current implementation results in many hours where there are no estimates. If there is no estimate for any type of weather, none is shown. Instead, we could show an estimate which might be close.

Because the weather observations are collected only from the Kumpula observation station, they might not be very accurate when considering city bike stations for example in Espoo. Collecting weather observations from observation stations nearest to each bike station might increase the usefulness of the weather data in the predictions.

# Future work

The estimates should be moved to a database, which would ease the process of calculating new predictions. In addition, the amount of bikes in circulation could be calculated, and used as  a part of a more machine learning -type solution.


## Who did what

We worked together as a group. Everyone did somewhat equal amount of work and we constantly shared and validated ideas with each other.
