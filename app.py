from flask import Flask, render_template, make_response, request, render_template_string,redirect,url_for,jsonify #, Markup
from markupsafe import Markup 
from flask_flatpages import FlatPages, pygmented_markdown
from flask_frozen import Freezer
from flask_minify import minify 
import markdown
# from yaml import safe_load
import yaml

import pandas as pd
# from datetime import date, timedelta, datetime
import subprocess
import numpy as np
import sys, os, re, shutil, glob
import copy
import polars as pl
import json

import geopy

# Custom code:

# print(df_destinations)
# from python_code.seo import *

# -------
# ------- SETTINGS ------------- 
# -------

lang='NL'
port=5777
boolean_print = True

# Load environment file(s):
def load_config(filename):
  """Loads configuration from a YAML file."""
  with open(filename, 'r') as f:
    try:
      config = yaml.safe_load(f)
    except yaml.YAMLError as e:
      raise ValueError(f"Error parsing YAML file: {e}")
  return config

# Load the configuration from pseo.yml
config = load_config('pseo_config.yml')
dict_config = {k.lower(): v for k, v in config.items()}

DEBUG = True
FLATPAGES_AUTO_RELOAD = DEBUG
FLATPAGES_EXTENSION = '.md'

dict_base_url = {
   'NL':'https://www.weeropbestemming.nl',
}

dict_google_analytics_id = {
   'NL':'G-JM9SCXK4CZ'
}

dict_logo_parts = {
   'NL':{
      'part1':{'txt':'Weer','classes':'first'},
      'part2':{'txt':'op','classes':'unimportant'},
      'part3':{'txt':'Bestemming','classes':'second'},
      'part4':{'txt':'.nl','classes':'extension'},
      }
}

base_url = dict_base_url[lang]
google_analytics_id = dict_google_analytics_id[lang]


# -------
# ------- LOAD DATA ------------- 
# -------


from python_code.download import *

df_destinations = xlsx_sheet_to_df(filename=r'./data/destinations.xlsx',sheetname='Destinations')
dict_destinations = create_dict_destinations(df_destinations)
dict_destinations = translate_dict_destinations(dict_destinations,lang=lang)
# dict_destinations_data = create_dict_destinations_data(dict_destinations)

dict_destinations_clean = clean_dict_destinations(dict_destinations)
dict_destinations_data = create_dict_destinations_data(dict_destinations_clean)

dict_countries = create_dict_countries(dict_destinations_clean)

df_months = xlsx_sheet_to_df(filename=r'./data/months.xlsx',sheetname='Months')

df_sentences_all = xlsx_sheet_to_df(filename=r'./data/sentences.xlsx',sheetname='all')
df_sentences_home = xlsx_sheet_to_df(filename=r'./data/sentences.xlsx',sheetname='index')
df_sentences_sitemap = xlsx_sheet_to_df(filename=r'./data/sentences.xlsx',sheetname='sitemap')
df_sentences_c = xlsx_sheet_to_df(filename=r'./data/sentences.xlsx',sheetname='country')
df_sentences_cp = xlsx_sheet_to_df(filename=r'./data/sentences.xlsx',sheetname='country_place')
df_sentences_cpm = xlsx_sheet_to_df(filename=r'./data/sentences.xlsx',sheetname='country_place_month')

folder_data_processed = './data/processed'
folder_data_topojson = './static/topojson'


# -------
# ------- SCHEMA -------------
# -------




# -------
# ------- HELP FUNCTIONS -------------
# -------


def prerender_jinja(text):
    prerendered_body = render_template_string(Markup(text))
    prerendered_body = markdown.markdown(prerendered_body, extensions=['fenced_code','toc', 'attr_list','tables'])
    return pygmented_markdown(prerendered_body)






   
# Country = dict_destinations_clean[country][list(dict_destinations_clean[country].keys())[0]]['Country']

# -------
# ------- FLASK -------------
# -------


app = Flask(__name__)
app.config['FLATPAGES_HTML_RENDERER'] = prerender_jinja
app.config.from_object(__name__)
pages = FlatPages(app)
freezer = Freezer(app)

app.config['FREEZER_RELATIVE_URLS'] = True

# initializing minify for html, js and cssless 
minify(app=app, html=True, js=True, cssless=True)

def slug(text):
   return(text.replace(' ','-').lower())

list_months = df_months[lang].to_list()
list_months_slug = [slug(m) for m in list_months]
list_months3 = df_months[lang+'3'].to_list()

# Dictionary object available in all templates:
@app.context_processor
def dict_all():
    return dict(
       base_url = base_url,
       google_analytics_id = google_analytics_id,
       dict_logo = dict_logo_parts[lang],
       dict_config = dict_config,
       dict_destinations = dict_destinations,
       dict_destinations_clean = dict_destinations_clean,
       dict_destinations_data = dict_destinations_data,
       dict_countries = dict_countries,

       slug=slug,

       df_months = df_months,
       list_months =list_months,
       list_months_slug=list_months_slug,
       list_months3=list_months3,
       bg_page='bg-gray-50',
    )

   

# emoji's inside text are recognized:
import emoji
@app.template_filter('emojify')
def emoji_filter(s):
    #return emoji.emojize(s, use_aliases=True)
    return emoji.emojize(s)



# -------
# ------- ROUTES -------------
# -------


@app.route('/')
def home():
    if boolean_print:
        print('home')

    dict_topojson = {}
    # dict_m_data = {}
    dict_mapdata = {}
    dict_countrydata = {}
    countries_home = ['italië','griekenland','egypte','turkije']
    countries_tabs = ['spanje','portugal','italië','turkije']
    # dict_countrylinks = {}

    def remove_keys(dict_in,keys_keep=['Place','Map','Label','Lat','Lon','Popular','Superpopular']):
        dict_out = {}
        for place in dict_in:
           for k in keys_keep:
              dict_out[place]={k:dict_in[place][k] for k in keys_keep}
        return dict_out
    
    for country in countries_home:
       dict_destinations_country = remove_keys(dict_destinations_data[country])
       df_m_country = pd.read_csv(os.path.join(folder_data_processed,country,'df_m_country.csv'))
       cols_m_country = ['place','m','tmax_med']
       df_m_country = df_m_country[cols_m_country]
       dict_m_country = df_m_country.to_dict(orient='records')

       dict_mapdata[country]=[{**item,**dict_destinations_country[item['place']]} for item in dict_m_country]
       
       dict_countrydata[country]={'Country':'','n_popular_ct':0,'places':{}}
       n_popular_ct = 0
       for p in dict_destinations_data[country]:

        dict_countrydata[country]['Country']=dict_destinations_data[country][p]['Country']
        dict_countrydata[country]['places'][p]={k:dict_destinations_data[country][p][k] for k in ['Place','Popular']}
        dict_countrydata[country]['places'][p]['country']=country
        dict_countrydata[country]['places'][p]['place']=p
        n_popular_ct += dict_countrydata[country]['places'][p]['Popular']
       dict_countrydata[country]['n_popular_ct']=n_popular_ct

    #    dict_countrylinks[country]={'ct':country}

       for filename in os.listdir(folder_data_topojson):
          if filename.startswith(country+'_') or filename==f'{country}.json':
             dict_topojson[filename] = {
                'status': ('main' if (filename.endswith(f'{country}.json')) else 'secondary'),
                }


    dict_vars_home = {}
    dict_ID = create_dict_ID(df_sentences_home,dict_vars_home,lang=lang)
    # dict_ID_all = create_dict_ID(df_sentences_home,dict_vars_home,lang=lang)
    dict_page_meta = {
       'title':dict_ID['title'],
       'description':dict_ID['description'],
       'canonical':base_url+request.path
       }
    return render_template(
       'index.html',
       dict_page_meta=dict_page_meta,
       dict_ID=dict_ID,
       dict_topojson=dict_topojson,
       dict_mapdata=dict_mapdata,
       dict_countrydata=dict_countrydata,
    #    dict_countrylinks=dict_countrylinks,
       countries_tabs=countries_tabs,
       countries_home=countries_home
       )


@app.route('/sitemap/')
def sitemap():
    if boolean_print:
       print('sitemap')
    dict_vars_sitemap = {
       'base_url_strip':base_url.replace('https://','')
    }
    dict_ID = create_dict_ID(df_sentences_sitemap,dict_vars_sitemap,lang=lang)
    dict_page_meta = {
       'title':dict_ID['title'],
       'description':dict_ID['description'],
       'canonical':base_url+request.path,
       }
    return render_template('sitemap.html',
                          dict_page_meta=dict_page_meta,
                          dict_ID=dict_ID)

@app.route('/<string:country>/<string:place>/<string:month>/')
def country_place_month(country,place,month):
   if boolean_print:
      print(f'{country}/{place}/{month}')
#    print(f'PATH : {request.path}')
#    print('')
   month_index = list_months_slug.index(slug(month))+1
   month_name = list_months[month_index-1]
   month_slug = list_months_slug[month_index-1]
   
   dict_destination = {}
   dict_destination = dict_destinations_clean[country][place]
   dict_destination['month_index']=month_index
   dict_destination['month_name']=month_name
   dict_destination['month_slug']=month_slug

   def get_data_month(df_name,country,place,month_index,offset=0):
      df_data_month = pd.read_csv(os.path.join(folder_data_processed,country,place,df_name+'.csv'))
      ms = [(((month_index-1)+i)%12)+1 for i in range(-offset,offset+1)]
      df_data_month = df_data_month[df_data_month['m'].isin(ms)]
      df_data_month['m_abbr']=df_data_month['m'].map(lambda x: list_months3[x-1])
      if(offset>0):
         df_data_month['m']=df_data_month['m'].apply(
            lambda value: (value + 12) if ((value - month_index) < -offset)
            else (value - 12) if ((value - month_index) > offset) 
                               else value)
         if 'm3' in df_data_month.columns:
            df_data_month = df_data_month.sort_values(by=['m','m3'])
         else:
            df_data_month = df_data_month.sort_values(by=['m'])
      return(df_data_month)
   
   df_mh = get_data_month('df_mh',country,place,month_index)
   df_mm3 = get_data_month('df_mm3',country,place,month_index,offset=2)
   df_mm3d = get_data_month('df_mm3d',country,place,month_index)
   df_mm3h = get_data_month('df_mm3h',country,place,month_index)

   dict_vars_cpm = {
      'country_name':dict_countries[country]["country_name"],
      'place_name':dict_destinations[country][place]['Place'],
      'month_name':dict_destination['month_name'],
      }
   dict_ID = create_dict_ID(df_sentences_cpm,dict_vars_cpm,lang=lang)

   list_ids = ['h2_temp','h3_temp_minmax','h3_temp_hour','h3_temp_avg','h2_rain','h3_rain_avg','h3_rain_pct']
   dict_anchors = create_dict_anchors(list_ids,dict_ID)
   
   dict_page_meta = {
      'title':dict_ID['title'],
      'description':dict_ID['description'],
      'canonical':base_url+request.path
      }


   return render_template(
      "country_place_month.html",
      dict_page_meta=dict_page_meta,
      dict_ID=dict_ID,
      dict_anchors=dict_anchors,
      country=country,place=place,month=month,
    #   Country=Country,
      json_mm3=json.loads(df_mm3.to_json(orient='records')),
      json_mm3d=json.loads(df_mm3d.to_json(orient='records')),
      json_mh=json.loads(df_mh.to_json(orient='records')),
      json_mm3h=json.loads(df_mm3h.to_json(orient='records')),
      month_index=month_index,
      dict_destination=dict_destination,
      dict_destinations_country=dict_destinations_clean[country]
   ) 




@app.route('/<string:country>/<string:place>/')
def country_place(country,place):
   if boolean_print:
      print(f'{country}/{place}')
#    dict_destination = {}
   dict_destination = dict_destinations_clean[country][place]
   def get_data_place(df_name,country,place):
      df_data_place = pd.read_csv(os.path.join(folder_data_processed,country,place,df_name+'.csv'))
      df_data_place['m_abbr']=df_data_place['m'].map(lambda x: list_months3[x-1])
      return df_data_place
   
   df_mm3 = get_data_place('df_mm3',country,place)
   df_m = get_data_place('df_m',country,place)
   
   dict_vars_cp = {
        'country_name':dict_countries[country]["country_name"],
        'place_name':dict_destinations[country][place]['Place'],
        }
   dict_ID = create_dict_ID(df_sentences_cp,dict_vars_cp,lang=lang)
   
   list_ids = ['h2_overview','h2_temp','h3_temp_avg','h2_rain','h3_rain_sum','h3_prcp_sum','h3_rain_pct']
   dict_anchors = create_dict_anchors(list_ids,dict_ID)
   
   dict_page_meta = {
        'title':dict_ID['title'],
        'description':dict_ID['description'],
        'canonical':base_url+request.path,
        }
   
   return render_template(
      "country_place.html",
      dict_page_meta=dict_page_meta,
      dict_ID=dict_ID,
      dict_anchors=dict_anchors,
      country=country,place=place,
      dict_destination=dict_destination,
      dict_destinations_country=dict_destinations_clean[country],
      df_m=df_m,
      json_mm3=json.loads(df_mm3.to_json(orient='records')),
      json_m=json.loads(df_m.to_json(orient='records'))
   )




@app.route('/<string:country>/')
def country(country):
   if boolean_print:
      print(f'{country}')
   dict_destination = dict_destinations_clean[country]
   
   dict_topojson = {}
   for filename in os.listdir(folder_data_topojson):
      if filename.startswith(country+'_') or filename==f'{country}.json':
        
        dict_topojson[filename] = {
           'status': ('main' if (filename.endswith(f'{country}.json')) else 'secondary'),
        }

   def get_data_country(df_name,country,dict_destinations):
        place_dummy = list(dict_destinations[country].keys())[0]
        country_data = dict_destinations[country][place_dummy]['data_country']
        df_data_country = pd.read_csv(os.path.join(folder_data_processed,country_data,df_name+'.csv'))
        return(df_data_country)
    #   df_data_country = pd.read_csv(os.path.join(folder_data_processed,country,df_name+'.csv'))
    #   return(df_data_country)

   df_m_country = get_data_country('df_m_country',country,dict_destinations)
   dict_c = {
        'top_n':3,
        'months_n_always':10,
        'degrees_thresholds':[20,25,30],
        'degrees_delta':2,
        'c_dry':10,
        'c_warm':18,'c_hot':38,
        }
   dictQA_country = create_dictQA_country(df_m_country,**dict_c)

   def create_df_map(df_data_country,dict_destinations,cols_keep=['m','tavg_med']):
        df_out = df_data_country.copy()
        def get_v(row,v='Lat'):
            return dict_destinations[row['country']][row['place']][v]
        df_out['Lat'] = df_out.apply(get_v,args=('Lat',),axis=1)
        df_out['Lon'] = df_out.apply(get_v,args=('Lon',),axis=1)
        df_out['Place'] = df_out.apply(get_v,args=('Place',),axis=1)
        df_out['Map'] = df_out.apply(get_v,args=('Map',),axis=1)
        df_out['Label'] = df_out.apply(get_v,args=('Label',),axis=1)
        df_out = df_out[['Place','Map','Lat','Lon','Label']+cols_keep]
        return(df_out)

   df_map_m_country = create_df_map(df_data_country=df_m_country,dict_destinations=dict_destinations,cols_keep=['m','tavg_med','tmax_med','prcp_sum'])

   
   
   dict_vars_c = {
      'country_name':dict_countries[country]["country_name"],
      'n_places':str(len([x for x in dict_destination])),
      }
   dict_ID = create_dict_ID(df_sentences_c,dict_vars_c,lang=lang)

   list_ids = ['h2_temp','h3_temp_avg','h4_temp_avg_map','h4_temp_avg_table','h3_temp_max','h4_temp_max_map','h4_temp_max_table','h2_rain','h3_rain','h2_faq']
   dict_anchors = create_dict_anchors(list_ids,dict_ID)

   dict_page_meta = {
      'title':dict_ID['title'],
      'description':dict_ID['description'],
      'canonical':base_url+request.path,
      }

   return render_template(
      "country.html",
      dict_page_meta=dict_page_meta,
      dict_anchors=dict_anchors,
      country=country,
      dict_destination=dict_destination,
      dict_destinations_country=dict_destinations_clean[country],
      df_m_country=df_m_country,
      dictQA_country=dictQA_country,
      dict_ID=dict_ID,
      dict_vars_c=dict_vars_c,
      df_map_m_country = df_map_m_country,
      json_m_country = json.loads(df_m_country.to_json(orient='records')),
      json_map_m_country = json.loads(df_map_m_country.to_json(orient='records')),
      dict_topojson = dict_topojson
   )



# -------
# ------- MAIN -------------
# -------


if __name__ =='__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        app.config['FREEZER_DESTINATION'] = 'build_'+lang
        app.config['DEBUG'] = True

        # app.config['FREEZER_IGNORE_MIMETYPE_WARNINGS'] = True
        # app.config['FREEZER_IGNORE_404_NOT_FOUND'] = True

        freezer.freeze()
        
        # create_sitemap_xml(dict_website)
        # create_robots_txt(dict_website)
    else:
        # app.run(port=5000)
        app.run(host='0.0.0.0',debug=True,port=port)
