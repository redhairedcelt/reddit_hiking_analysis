#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 17 15:24:15 2019

@author: patrickmaus
"""
import json
import urllib
import time

address = '1600+Amphitheatre+Parkway,+Mountain+View,+CA'
api_key = 'AIzaSyCNzvv8n7tBR7BoGDAi2OSdSngTsWdBfaw'
url = 'https://maps.googleapis.com/maps/api/geocode/json?'

url_address_api = '{}address={}&key={}'.format(url, address, api_key)

print(url_address_api)