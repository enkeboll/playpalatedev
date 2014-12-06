import requests
import json

headers = {'AUTHORIZATION': 'TD1 5501/7d53845f1bd6e2cbf321483ecca0570226099e02'}
url = 'http://api.treasuredata.com/v3/job/result/18150340'
params = {'format':'json'}
response =  requests.get(url,headers=headers,params=params)

messy_response =  response.content
#print messy_response
rows = messy_response.split('\n')
rows = filter(None,rows)
rows = [row.strip('[]').split(',') for row in rows]
start_json = (len(rows[0])-1)/2
end_json = len(rows[0])-1
json_format = [json.loads(','.join(row[start_json:end_json])) for row in rows]

print json_format
