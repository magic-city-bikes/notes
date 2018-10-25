# Magic City Bikes

Introduction to Data Science miniproject for predicting when a HSL city bike will be added and when one will be taken from a city bike station.

## Data

We combined data on the HSL city bike stations and weather data.

### HSL city bikes
TODO: Describe data used and how it was gathered

### Weather

Weather data was collected from FMI. For the models we downloaded weather observations from the Kumpula observation station from the [FMI website](https://en.ilmatieteenlaitos.fi/download-observations#!/) as a CSV file.

Empty values in the weather data were filled with last known value. Only temperature and the amount of rain is used in the final model we used.

For the [application](https://github.com/magic-city-bikes/magic-city-bikes-web) the real-time weather data is collected from [FMI's API for getting weather observations for the Kumpula observation station](http://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature&storedquery_id=fmi::observations::weather::timevaluepair&fmisid=101004&parameters=r_1h,t2m&starttime=2018-10-25T11:39:10.992Z). The observations are from the last hour at 10 minute intervals. The average of the temperature and amount of rain from the last hour is used.
