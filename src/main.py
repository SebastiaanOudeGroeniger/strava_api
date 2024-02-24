import os 
from datetime import datetime, timedelta, time
import requests
from dotenv import load_dotenv
import json

#constants
BASE_URL = "https://www.strava.com/api/v3/"
DAILY_LIMIT = 1000
FIFTEEN_MINUTE_LIMIT = 195

#load environment variables
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REFRESH_TOKEN = os.getenv('REFRESH_TOKEN')
AUTHENTICATION_ENDPOINT = os.getenv('AUTHENTICATION_ENDPOINT')

current_datetime = datetime.utcnow()
formatted_datetime = current_datetime.strftime("%Y/%m/%d/%H/%M")

def get_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, AUTHENTICATION_ENDPOINT):
    # these params needs to be passed to get access
    # token used for retrieveing actual data
    payload:dict = {
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'refresh_token': REFRESH_TOKEN,
    'grant_type': "refresh_token",
    'f': 'json'
    }
    res = requests.post(AUTHENTICATION_ENDPOINT, data=payload, verify=False)
    access_token = res.json()['access_token']
    return access_token


def strava_auth_header():

    token = get_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, AUTHENTICATION_ENDPOINT)
    
    authorization_header = {'Authorization': f'Bearer {token}'}

    return authorization_header

def strava_get_athlete():

    url = f'{BASE_URL}/athlete'
    request = requests.get(url=url, headers=strava_auth_header())
    data = request.json()

    return data


def strava_get_athlete_activities(only_last_week:bool):

    if only_last_week:
        # Get the current date and time
        current_datetime = datetime.utcnow()

        # Calculate a week before now
        one_week_before_now = current_datetime - timedelta(weeks=1)

        # Convert the result to epoch timestamp (as integer)
        epoch_timestamp = int(one_week_before_now.timestamp())

        url = f'{BASE_URL}/athlete/activities?after={epoch_timestamp}'

    else:
        url = f'{BASE_URL}/athlete/activities'


    activities = []
    params = {'per_page': 200, 'page': 1}
    request = requests.get(url=url, headers=strava_auth_header(), params=params)
    data = request.json()

    while len(data) > 0:
        id_list = [record['id'] for record in data]
        activities.append(id_list)
        params['page'] += 1 
        request = requests.get(url=url, headers=strava_auth_header(), params=params)
        data = request.json()

    activity_ids = []
    for sublist in activities:
         activity_ids.extend(sublist)
    
    return activity_ids

def strava_individual_activity(only_last_week:bool):

    
    activity_ids = strava_get_athlete_activities(only_last_week)
    
    params = {'include_all_efforts': True} 
    activities = []
    api_limit_counter = 0
    #logging.info(f"Get all activity details function will pause {math.floor(len(activity_ids)/fifteen_minute_limit)} times for fifteen minutes to accomodate in the rate limit for this API ")
    for id in activity_ids:
        url = f'{BASE_URL}/activities/{id}'
        request = requests.get(url=url, headers=strava_auth_header(), params=params)
        api_limit_counter += 1
        data = request.json()
        activities.append(data)
        if api_limit_counter == FIFTEEN_MINUTE_LIMIT:
             #logging.info("Sleeping for 15 minutes to deal with rate limit in API")
             time.sleep(930)  #sleep for 15 minutes with additional 30 second failsafe
             api_limit_counter = 0 #reset counter
             #logging.info("Continuing again")

    return activities

def strava_get_gear():
    athlete_data = strava_get_athlete()
    shoes = athlete_data["shoes"]
    bikes = athlete_data["bikes"]
    shoes_id = []
    shoe_data = []
    bikes_id = []
    bike_data = []
    if len(shoes) > 0:
        
        for shoe in shoes:
            shoes_id.append(shoe["id"])  
        
        for id in shoes_id:
            url = f'{BASE_URL}/gear/{id}'
            request = requests.get(url=url, headers=strava_auth_header())
            shoe_data.append(request.json())

    else:
        shoe_data = []

    if len(bikes) > 0:

        for bike in bikes:
            bikes_id.append(bike["id"])
    
        for id in bikes_id:
            url = f'{BASE_URL}/gear/{id}'
            request = requests.get(url=url, headers=strava_auth_header())
            bike_data.append(request.json())
    else:
        bike_data = []

    return {"Bikes": bike_data, "Shoes": shoe_data}

def save_data_to_json(api_model:str, only_last_week:bool=True):

    global formatted_datetime

    if api_model == "athlete":
        data = json.dumps(strava_get_athlete())

    elif api_model == "athlete_activities":
        data = json.dumps(strava_individual_activity(only_last_week))

    elif api_model == "gear":
        data = json.dumps(strava_get_gear())
        

    else:
        print("This model is not available or invalid")

        return None
    
    file_name = f'{api_model}.json'
    folder = f'data/{api_model}/{formatted_datetime}'
    if not os.path.exists(folder):
        os.makedirs(folder)

    with open(f"{folder}/{file_name}", "w") as file:
        file.write(data)
  
def main():
   
    try:
        save_data_to_json(api_model="athlete_activities", only_last_week=True)
        pass
    except Exception as e:
        print(f"Error: {e}")
    
    try:    
        save_data_to_json(api_model="athlete")
    except Exception as e:
        print(f"Error: {e}")

    try:
        save_data_to_json(api_model="gear")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
