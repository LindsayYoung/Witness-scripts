# uses Sunlight's Congress API and the api.genderize.io api to generate the data about gender disparity
# you will need a Sunlight API key for this. 

import json
import requests
import csv
import os.path

apikey =  # get a key http://sunlightfoundation.com/api/accounts/register/

first_names = []
full_witness_data = []
name_gender = {}

def call_congress_api(page):
  endpoint = 'https://congress.api.sunlightfoundation.com/hearings'

  query_params = {
          'apikey': apikey,
          'per_page': 50,
          'fields': 'witnesses,first_name,occurs_at,committee,subcommittee,house_event_id',
          'chamber': 'house',
          'page': page,
                 }
  
  response = requests.get(endpoint, params=query_params)

  response_url = response.url
  # debug
  # print response_url
  return response.json()

def read_response(resp):
  for hearing in resp["results"]:
    if hearing.has_key("witnesses"):
      for witness in hearing["witnesses"]:
        record = {}
        first_name = witness["first_name"]
        record["first_name"] = first_name
        record["last_name"] = witness["last_name"]
        record["house_event_id"] = hearing["house_event_id"]

        if witness.has_key("honorific"):
          record["honorific"] = witness["honorific"]
          if record["honorific"] == 'Mr.':
            record["gender"] = 'male'
          elif record["honorific"] in['Ms.', 'Mrs.', 'Miss.']:
            record["gender"] = 'female'
          else: 
            if first_name not in first_names: first_names.append(first_name)
            record["gender"] = None

        else:
          if first_name not in first_names: first_names.append(first_name)
          record["honorific"] = None
          record["gender"] = None

        if witness.has_key("organization") and witness["organization"] != None:
          record["organization"] = witness["organization"]
        else:
          record["organization"] = ''
        if witness.has_key('position') and witness["position"] != None:
          record["position"] = witness["position"]
        else:
          record["position"] = ''
        record["occurs_at"] = hearing["occurs_at"]
        record["date"] = hearing["occurs_at"]

        if hearing.has_key('committee'):
          record["committee"] = hearing["committee"]['name']
        else:
          record["committee"] = None

        if hearing.has_key("subcommittee"):
          record["subcommittee"] = hearing["subcommittee"]['name']
        else:
          record["subcommittee"] = None
        full_witness_data.append(record)
  
  return {'page': resp["page"]['page'], 'total_pages': int(resp['count'])/50}

def look_up_gender(first_names):
  # do first name lookup
  length = len(first_names)
  calls = length/20 
  if length % 20 != 0: calls += 1
  call = 0

  results = []
  for name in range(0,calls):
    first = call
    last = call + 20
    names= first_names[first:last]
    call_string = 'http://api.genderize.io?'
    num = 0
    for n in names:
      name_string = "name[%s]=%s&" % (num, n)
      call_string = call_string + name_string
      num += 1
    
    r = requests.get(call_string)
    name_results = r.json()
    for result in name_results:
      name_gender[result['name']] = result
    
    call += 20

  # saving name results 
  with open("name_data.json", "w") as name_file:
    json.dump(name_gender, name_file)


page = 1
total_pages = 1
# retrieve witness information
while page <= total_pages:
  resp = call_congress_api(page)
  # this adds to the full_witness_data list
  pages = read_response(resp)
  page = int(pages['page']) + 1
  total_pages = pages['total_pages']

#  saving Congress API results to disk
with open("hearing.json", "w") as hearing_file:
  json.dump(full_witness_data, hearing_file)

# reading gender data from file or calling the genderize API
if os.path.isfile("name_data.json"):
  name_gender = json.load(open("name_data.json", 'rb'))
else:
  look_up_gender(first_names)

committee_stats = {}
total = {'female':0, 'male':0, 'unidentified':0}

# write results as csv and calculate committee stats
with open('witness_data.csv', 'wb') as csvfile:
  writer = csv.writer(csvfile)
  writer.writerow(['honorific', 'honorific gender', 'gender guess', 'probability', 'first_name', 'last_name', 'position', 'organization', 'house_event_id', 'committee_name', 'subcommittee', 'date', 'gender'])
  for witness in full_witness_data:
    first_name = witness['first_name']
    gender_honorific = witness['gender']
    committee = witness['committee']
    # gender derived from genderize.io
    if gender_honorific == None:
      gender_guess = name_gender[first_name]['gender']
      gender = gender_guess
      if name_gender[first_name].has_key('probability'):
        probability = name_gender[first_name]['probability']
      else:
        probability = None
    # gender derrived from honorific
    else:
       gender = gender_honorific
       gender_guess = None
       probability = None

    writer.writerow([
      witness['honorific'],
      gender_honorific,
      gender_guess,
      probability,
      first_name.encode("ascii","ignore"),  
      witness['last_name'].encode("ascii","ignore"), 
      witness['position'].encode("ascii","ignore"), 
      witness['organization'].encode("ascii","ignore"), 
      witness['house_event_id'], 
      committee, 
      witness['subcommittee'], 
      witness['date'],
      gender, 
    ])
    if not committee_stats.has_key(committee):
      committee_stats[committee] = {'female':0, 'male':0, 'unidentified':0}
    if gender == 'female':
      committee_stats[committee]['female'] += 1
      total['female'] += 1
    elif gender == 'male':
      committee_stats[committee]['male'] += 1 
      total['male'] += 1
    else:
      committee_stats[committee]['unidentified'] += 1
      total['unidentified'] += 1

#saving committee totals to csv
with open("committee_totals.csv", "wb") as committee_file:
  writer = csv.writer(committee_file)
  writer.writerow(['committee', 'male','unidentified', 'female'])
  for com in committee_stats.keys():
    writer.writerow([com, committee_stats[com]['male'], committee_stats[com]['unidentified'], committee_stats[com]['female']])

print total
