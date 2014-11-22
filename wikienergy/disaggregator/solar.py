"""
.. module:: solar
   :platform: Unix
   :synopsis: Contains methods for calculating solar savings.

.. moduleauthor:: Phil Ngo <ngo.phil@gmail.com>
.. moduleauthor:: Sabina Tomkins <sabina.tomkins@gmail.com>

"""

import json
import urllib2
from calendar import monthrange
import datetime

def get_solar_data_from_nrel(api,zip_code):
    f = urllib2.urlopen('http://developer.nrel.gov/api/solar/solar_resource/'
           +'v1.json?api_key='+str(api)+'&address='+str(zip_code))
    json_string = f.read()
    parsed_json = json.loads(json_string)
    return parsed_json['outputs']['avg_lat_tilt']['monthly']


def get_month_name(month_num):
    months = ['jan', 'feb' , 'mar', 'apr', 'may', 'jun',
            'jul','aug','sep','oct','nov','dec']
    return months[month_num-1]


def calculate_solar_generated(start_dt,end_dt,api,zip_code,
        array_size,eff_factor=0.8):

    month_data = get_solar_data_from_nrel(api,zip_code)
    delta = end_dt - start_dt
    data = []
    this_month = start_dt.month
    total_kWh = 0
    for val in range(delta.days+1):
        delta_days=datetime.timedelta(val)
        month_name= get_month_name(this_month)
        total_kWh=total_kWh+month_data[month_name]*eff_factor*array_size
        if (start_dt+delta_days).month is not this_month or val==delta.days:
            data.append({'date':str(month_name.title())+' ' + str((start_dt+delta_days).year) ,'value':total_kWh})
            this_month=(start_dt+delta_days).month
            total_kWh=0

    return data
