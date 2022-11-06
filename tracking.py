
from requests import get
#from matplotlib import pyplot as plt
from datetime import datetime
from pprint import pprint
import time 
from pandas.io.json import json_normalize
from flask_cors import CORS

import pandas as pd
from flask import Flask 
from flask_restful import Api, Resource, reqparse, abort, fields
import json
from flask import jsonify
#get it from log in snowtrace ;4


app = Flask(__name__)
app.config['CORS_HEADERS'] = 'Content-Type'

CORS(app)
api= Api(app)
ETHER_VALUE = 10 ** 18


#users choose snowtrace or etherscan: 1 for snowtrace ,other for etherscan
class select_network_address(Resource):
    
    BASE_URL = ""
    API_KEY = ""
    dr=0
    valid=""
    def get(self):
        return 200
    def put(self,eth_avax,ADD):
     if eth_avax==1:
      select_network_address.BASE_URL ="https://api.snowtrace.io/api"
      select_network_address.API_KEY = "1S973ZUIZZG4P3MD1DK48JN1RJBRG5IH9D"
      select_network_address.valid=ADD
      return 200
     elif eth_avax==0 :
        select_network_address.BASE_URL = "https://api.etherscan.io/api"
        select_network_address.API_KEY = "Q7S8F89W6UQKYRQPX4YDWCKNXCYNFTUCDG"
        select_network_address.valid=ADD
        return 200
     elif eth_avax==2:
           select_network_address.BASE_URL ="https://api.bscscan.com/api"
           select_network_address.API_KEY = "7KVTG817KNJI28WIS9B7KDZG9DSPTRC4TE"
           select_network_address.valid=ADD
           return 200
     else :
         select_network_address.valid=""
         abort(403,message="please select correct network")
         
api.add_resource(select_network_address,"/select_network_and_address/<int:eth_avax>/<string:ADD>")

#let users enter the address

#the value is in wei so,we will convert it by this;
#eht ;
#function to make apiUrl 
def make_api_url(module, action, address, **kwargs):
	url = select_network_address.BASE_URL+ f"?module={module}&action={action}&address={address}&apikey={select_network_address.API_KEY}"

	for key, value in kwargs.items():
		url += f"&{key}={value}"

	return url


#get all ex/in transactions in smartcontract with limit is 20000 
#if we want to get more we shoule set paramter "page" to 2 or 3 or 4...
def get_transactions():
    transactions_url = make_api_url("account", "txlist", select_network_address.valid, startblock=0, endblock=99999999, page=1, offset=10000, sort="asc")
    response = get(transactions_url)
    data = response.json()["result"]
    try :

     internal_tx_url = make_api_url("account", "txlistinternal", select_network_address.valid, startblock=0, endblock=99999999, page=1, offset=10000, sort="asc")
    
     response2 = get(internal_tx_url)
     data2 = response2.json()["result"]
    
     
     data.extend(data2)
     data.sort(key=lambda x: int(x['timeStamp']))
    except:
        abort(404,message="enter valid address or network")
            
    return data





#drop all unimportant columns
def drop() :
	#convert data from json to csv 
 df = pd.json_normalize(get_transactions())
 df.to_csv('test.csv', index=False, encoding='utf-8')
 #strat droping
 try :
    df.drop('hash', inplace=True, axis=1)
    df.drop('nonce', inplace=True, axis=1)
    df.drop('blockHash', inplace=True, axis=1)
    df.drop('transactionIndex', inplace=True, axis=1)
    df.drop('input', inplace=True, axis=1)
 #df.drop('traceId', inplace=True, axis=1)
    df.drop('confirmations', inplace=True, axis=1)
    df.drop('cumulativeGasUsed', inplace=True, axis=1)
 
#convert timeSTamp from obj to number
    df['timeStamp'] = pd.to_numeric(df['timeStamp'])
 except :
    abort(404,message="enter valid address or network")
 return df 
#df.sort_values("value", axis=0, ascending=False,inplace=True, na_position='first')

#convert timestamp to readable time 

def timeStamp_convertrealtime(dataframe):
	
	for i in dataframe["timeStamp"]:
          t=datetime.fromtimestamp(i)
          dataframe['timeStamp'] = dataframe['timeStamp'].replace({i: t})

#convert value from wei to avax	  
def value_convert(dataframe):
	
    for i in dataframe["value"] :
        c=str(i)	
        v=float(c[:30])
        v=v/ETHER_VALUE
        v=str(v)
        dataframe['value']=dataframe['value'].replace({i:v})

#furnction to get balance by address ,
#snowtrace limit only 5 request by secound so we use sleep()
class getaccount_balance(Resource):
 def get_account_balance(address):
    balance_url = make_api_url("account", "balance", address, tag="latest")
    response = get(balance_url)
    data = response.json()	
    time.sleep(0.15) 

    value = int(data["result"]) / ETHER_VALUE
    return value 
      
api.add_resource(getaccount_balance,"/get_account_balance")

	 


#get all sender balance in dict
class getallbalance(Resource):

 def get(self):
  if(select_network_address.BASE_URL==""):
      abort(404,message="please select correct address")
  balance_address={}
  df=drop()
  df.drop_duplicates(subset ="from",keep = "last", inplace = True)                            
  for i in df['from']:
            time.sleep(0.1)
            balancelist=getaccount_balance.get_account_balance(i)
            balance_address[i]=balancelist
            sort_orders = sorted(balance_address.items(), key=lambda x: x[1], reverse=True)

    
  
  return sort_orders
api.add_resource(getallbalance,"/get_allbalance")
#get filleter json
class getfillterDF(Resource):
 def get(self):
  if(select_network_address.BASE_URL==""):
    abort(404,message="please select correct address")
  df=drop()
  timeStamp_convertrealtime(df)			
  value_convert(df)
  df.sort_values("value", axis=0, ascending=False,inplace=True, na_position='first')
  df_max_transactions=df.groupby(['value','from','to']).agg(time=('timeStamp','max') )
  df_max_transactions.sort_values("value", axis=0, ascending=False,inplace=True, na_position='first')
  df=df.to_json()
  response = jsonify(df)
  response.status_code = 200 # or 200 or whatever
  return response
  
api.add_resource(getfillterDF,"/getfillter")





#get most activite address wiht count,
class getmostAC(Resource):
 def get(self):
     if(select_network_address.BASE_URL==""):
      abort(404,message="please select correct address")
     df=drop()
	 #remove the address of the smartcontract casue is definitely the most activite
     df=df[df.to != select_network_address.valid]
     df=df['to'].value_counts()
     df=df.to_json()
     response = jsonify(df)
     response.status_code = 400 # or 200 or whatever
     return response
     
api.add_resource(getmostAC,"/getmostactivit")

#get the most activite reciver with count
class mostactivit_reciver(Resource):
 def get(self):
    if(select_network_address.BASE_URL==""):
      abort(404,message="please select correct address")
    df=drop()
	 #remove the address of the smartcontract casue is definitely the most activite
    df=df[df.to != select_network_address.valid]
    df=df['to'].value_counts()
    df=df.to_json()
    response = jsonify(df)
    response.status_code = 400 # or 200 or whatever
    return response
api.add_resource(mostactivit_reciver,"/mostactivitreciver")


#get the most activite sender with count
class mostactivit_sender(Resource):
 def get(self):
    if(select_network_address.BASE_URL==""):
      abort(404,message="please select correct address")
    df=drop()
	 #remove the address of the smartcontract casue is definitely the most activite
    df=df[df.to != select_network_address.valid]
    df=df['from'].value_counts()
    df=df.to_json()
    response = jsonify(df)
    response.status_code = 400 # or 200 or whatever
    return response
api.add_resource(mostactivit_sender,"/mostactivitsender")




if __name__ =="__main__" :
    app.run(host='0.0.0.0',port=5000)
