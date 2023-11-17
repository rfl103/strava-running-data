import requests
import urllib3
import streamlit as st
import pandas as pd
import plotly.express as px
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#getting activities data from activities API
auth_url = "https://www.strava.com/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"

payload = {
    'client_id': st.secrets.CLIENT_ID,
    'client_secret': st.secrets.CLIENT_SECRET,
    'refresh_token': st.secrets.REFRESH_TOKEN,
    'grant_type': "refresh_token",
    'f': 'json'
}

print("Requesting Token...\n")
res = requests.post(auth_url, data=payload, verify=False)
access_token = res.json()['access_token']
print("Access Token = {}\n".format(access_token))

header = {'Authorization': 'Bearer ' + access_token}

#loading new activites from API
request_page_num = 1
all_activities = []

while True:
    param = {'per_page': 200, 'page': request_page_num}
    my_dataset = requests.get(activites_url, headers=header, params=param).json()
    if len(my_dataset) == 0:
        print("breaking out of loop due to response of 0: no more activities")
        break

    if all_activities:
        print("all_activities is populated")
        all_activities.extend(my_dataset)

    else:
        print("all_activities is not populated with more data")
        all_activities=my_dataset

    request_page_num += 1

#converting dict from API to dataframe and selecting columns interested in
activity_dataframe = pd.DataFrame(all_activities)
activity_data = activity_dataframe[['type', 'sport_type', 'distance', 'moving_time', 'elapsed_time', 'total_elevation_gain', 'id', 'start_date', 'average_speed', 'average_cadence', 'elev_high', 'elev_low']]

#converting meters to miles
activity_data = activity_data.assign(distance = round(activity_data['distance']*0.00062137, 2))

#converting cadence to get steps per minute
activity_data = activity_data.assign(average_cadence = activity_data['average_cadence'] * 2)

#dropping rows with distance equal to 0.00 - this was due to indoor biking and these data points were not recorded properly
activity_data.drop(activity_data[activity_data['distance'] == 0.00].index, inplace = True)

#converting meters to miles
activity_data = activity_data.assign(total_elevation_gain = round(activity_data['total_elevation_gain']*3.28084,2))
activity_data = activity_data.assign(elev_high = round(activity_data['elev_high']*3.28084,2))
activity_data = activity_data.assign(elev_low = round(activity_data['elev_low']*3.28084,2))

#converting data from seconds to minutes
activity_data = activity_data.assign(moving_time = round(activity_data['moving_time']/60,2))
activity_data = activity_data.assign(elapsed_time = round(activity_data['elapsed_time']/60,2))

#creating new average speed measure with correct units (miles per hour)
activity_data = activity_data.assign(average_speed = round(activity_data['distance']/(activity_data['moving_time']/60),2))

#formatting start_date column - mainly interested in tracking year, month, and week
activity_data['start_date'] = pd.to_datetime(activity_data['start_date'])
activity_data['year'] = activity_data.start_date.apply(lambda x: x.year)
activity_data['month'] = activity_data.start_date.apply(lambda x: x.month)
activity_data['month_name'] = pd.to_datetime(activity_data['month'], format = '%m').dt.month_name()
activity_data['week_number'] = activity_data.start_date.apply(lambda x: x.weekofyear)
activity_data['start_date'] = pd.to_datetime(activity_data['start_date'])
activity_data['weekday'] = activity_data['start_date'].dt.dayofweek.map({
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday'
})

#page configuration
st.set_page_config(page_title="My Exercise Data",
                   layout="wide")

st.markdown("<h1 style='text-align: center; color:orange;'> My Exercise Data </h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; color:blue;'>Data collected from Strava API </h2>", unsafe_allow_html=True)

st.write("I am an avid runner and began using Strava in July 2023.  The data shown as obtained from the Strava API and reflects "
         "running activities that I have recorded in Strava via data collected from my Garmin watch.")

st.subheader(':green[Summary Metrics]', divider='rainbow')
b1,b2,b3 = st.columns(3)
with b1:
    #lowest average speed
    slowest_average_speed = activity_data['average_speed'].min()
    st.metric("Lowest Average Speed for a Run",slowest_average_speed)

with b2:
    #fastest average speed
    fastest_average_speed = activity_data['average_speed'].max()
    st.metric("Fastest Average Speed for a Run",fastest_average_speed)

with b3:
    #total number of miles run
    total_miles = round(activity_data['distance'].sum(),2)
    st.metric("Total Number of Miles Run Using Strava", total_miles)

st.subheader(':green[Click the tabs below to learn more about how different factors are related to average speed and how it has changed over time.]', divider='rainbow')
tab1, tab2, tab3, tab4 = st.tabs(["Elevation Gain vs Speed", "Cadence vs Speed", "Average Speed by Day of Week", "Average Speed Over Time"])

with tab1:
    #total elevation gain vs speed
    fig = px.scatter(x=activity_data['total_elevation_gain'], y=activity_data['average_speed'], title = 'Effect of Total Elevation on Speed').update_layout(
        xaxis_title = "Total Elevation Gain (feet)", yaxis_title = "Average Speed (mph)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("There does not appear to be a correlation between speed and total elevation gain.")

with tab2:
    #cadence vs speed
    fig = px.scatter(x=activity_data['average_cadence'], y=activity_data['average_speed'], title="Effect of Cadence on Speed").update_layout(
        xaxis_title = "Average Cadence (Steps/Minute)", yaxis_title = "Average Speed (mph)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("It does appear that there is a correlation between average cadence and average speed.")

with tab3:
    #average speed by day of week
    week_data = activity_data.groupby('weekday')[['distance', 'moving_time']].sum().reset_index()
    week_data['Average Speed'] =week_data['distance']/ (week_data['moving_time']/60)
    week_data['Average Speed'].sort_values()
    fig = px.bar(week_data, x='weekday', y='Average Speed', title = 'Average Speed by Day of Week')
    st.plotly_chart(fig, use_container_width=True)
    st.caption("It does appear that there are some days of the week with higher average speeds in comparison to others.  "
               "This makes sense as I tend to run harder workouts on certain days of the week.")

with tab4:
    #average_speed over time
    fig = px.line(activity_data, x = "start_date", y="average_speed", title = "Average Speed Over Time")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("This chart shows average speed over time.  As of October 2023, I would like to track this data more long-term to "
               "draw more meaningful conclusions. ")

st.subheader(':green[I hope to add to and further explore this data over time.] :woman-running:')


