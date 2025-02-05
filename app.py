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


# -------
# ------- LOAD DATA ------------- 
# -------


from python_code.download import *

df_destinations = xlsx_sheet_to_df(filename=r'./data/destinations.xlsx',sheetname='Destinations')
dict_destinations = create_dict_destinations(df_destinations)

df_months = xlsx_sheet_to_df(filename=r'./data/months.xlsx',sheetname='Months')

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


def slug(text):
   return(text.replace(' ','-').lower())


def clean_dict_destinations(dict_destinations,folder_data_processed='./data/processed'):
   """Checks if data exist for all locations in dict_destinations and returns a cleaned up version"""
   dict_destinations_clean = {}
   for country in dict_destinations:
      for place in dict_destinations[country]:
        boolean_add_key = True
        fp = os.path.join(folder_data_processed,country,place)
        if os.path.exists(fp):
            list_csvs = ['df_mm3d.csv','df_mm3h.csv']
            for lc in list_csvs:
               fpc=os.path.join(fp,lc)
               if os.path.exists(fpc):
                  if os.path.getsize(fpc) <= 5:
                    boolean_add_key = False   
               else:
                  boolean_add_key = False
        else:
           boolean_add_key = False
        if boolean_add_key:
           if (country in dict_destinations_clean):
              dict_destinations_clean[country].update({
                 place:dict_destinations[country][place]
                 })
           else:
              dict_destinations_clean.update({
                 country:{place:dict_destinations[country][place]}
                 })
              
   return dict_destinations_clean


dict_destinations_clean = clean_dict_destinations(dict_destinations)

def create_dict_countries(dict_destinations_clean):
   dict_countries={}
   for k1,v1 in sorted(dict_destinations_clean.items()):
      
      k2s = sorted(v1.keys())
      dict_countries[k1]={
         'country_name':dict_destinations_clean[k1][k2s[0]]['Country'],
         'n_places':len(list(k2s)),
         'list_place_slugs':list(k2s),
         'list_place_names':[dict_destinations_clean[k1][k2]['Place'] for k2 in k2s]
         }
   return dict_countries

dict_countries = create_dict_countries(dict_destinations_clean)
   
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

list_months = df_months[lang].to_list()
list_months_slug = [slug(m) for m in list_months]
list_months3 = df_months[lang+'3'].to_list()

# Dictionary object available in all templates:
@app.context_processor
def dict_all():
    return dict(
       dict_config = dict_config,
       dict_destinations = dict_destinations,
       dict_destinations_clean = dict_destinations_clean,
       dict_countries = dict_countries,
       df_months = df_months,
       list_months =list_months,
       list_months_slug=list_months_slug,
       list_months3=list_months3,
       bg_page='bg-gray-50',
        # dict_website = dict_website,
        # dict_menu = dict_menu,
        # dict_schema_all = dict_schema_all,
        # dict_md_all_yaml = dict_md_all_yaml,
        # Some dummy values, edit/add your own:

        value1='val1',
        value2='val2',
        dict1={'key1':'keyval1','key2':'keyval2'},
        # list_md_all=[p.path for p in pages],
        # dict_md_all=pages.get_all(),
        # dict_md_all={(p.path,str(dir(p))) for p in pages},
        # dict_md_all={(p.path,str(p.meta)) for p in pages},
        # dict_md_all={p.path:str(p.meta.get('title','NO TITLE FOR '+p.path)) for p in pages},
        
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
    dict_page_meta = {'title':'Some dummy index title'}
    return render_template(
       'index.html',
       dict_page_meta=dict_page_meta)

@app.route('/<string:country>/<string:place>/<string:month>/')
def country_place_month(country,place,month):

   month_index = list_months_slug.index(slug(month))+1
   month_index_prev2 = (month_index-3)%12 + 1
   month_index_prev = (month_index-2)%12 + 1
   month_index_next = (month_index-12)%12 + 1
   month_index_next2 = (month_index-11)%12 + 1
   
   month_name = list_months[month_index-1]
   month_name_prev2 = list_months[month_index_prev2-1]
   month_name_prev = list_months[month_index_prev-1]
   month_name_next = list_months[month_index_next-1]
   month_name_next2 = list_months[month_index_next2-1]

   month_slug = list_months_slug[month_index-1]
   month_slug_prev2 = list_months_slug[month_index_prev2-1]
   month_slug_prev = list_months_slug[month_index_prev-1]
   month_slug_next = list_months_slug[month_index_next-1]
   month_slug_next2 = list_months_slug[month_index_next2-1]
   
   list_links_month_name = [month_name_prev2,month_name_prev,month_name,month_name_next,month_name_next2]
   list_links_month_slug = [month_slug_prev2,month_slug_prev,month_slug,month_slug_next,month_slug_next2]

    
#    dict_destination = dict_destinations_clean[country][place]
   dict_destination = {}
   dict_destination = dict_destinations_clean[country][place]
   dict_destination['month_index_prev2']=month_index_prev2
   dict_destination['month_index_prev']=month_index_prev
   dict_destination['month_index']=month_index
   dict_destination['month_index_next']=month_index_next
   dict_destination['month_index_next2']=month_index_next2
   dict_destination['month_name']=month_name
   dict_destination['month_name_prev2']=month_name_prev2
   dict_destination['month_name_prev']=month_name_prev
   dict_destination['month_name_next']=month_name_next
   dict_destination['month_name_next2']=month_name_next2
   dict_destination['month_slug']=month_slug
   dict_destination['month_slug_prev2']=month_slug_prev2
   dict_destination['month_slug_prev']=month_slug_prev
   dict_destination['month_slug_next']=month_slug_next
   dict_destination['month_slug_next2']=month_slug_next2
   dict_destination['list_links_month_name']=list_links_month_name
   dict_destination['list_links_month_slug']=list_links_month_slug
   

   dict_page_meta = {
      'title':f'Weer in {dict_destination["Place"]}, {dict_destination["Country"]} in {month} - Temperatuur en kans op regen'
      }
   
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

   dict_stats = {}
   



   return render_template(
      "country_place_month.html",
      dict_page_meta=dict_page_meta,
      country=country,place=place,month=month,
    #   Country=Country,
      json_mm3=json.loads(df_mm3.to_json(orient='records')),
      json_mm3d=json.loads(df_mm3d.to_json(orient='records')),
      json_mh=json.loads(df_mh.to_json(orient='records')),
      json_mm3h=json.loads(df_mm3h.to_json(orient='records')),
      month_index=month_index,
      dict_stats=dict_stats,
      dict_destination=dict_destination,
      dict_destinations_country=dict_destinations_clean[country]
   )




@app.route('/<string:country>/<string:place>/')
def country_place(country,place):
#    dict_destination = {}
   dict_destination = dict_destinations_clean[country][place]
   def get_data_place(df_name,country,place):
      df_data_place = pd.read_csv(os.path.join(folder_data_processed,country,place,df_name+'.csv'))
      df_data_place['m_abbr']=df_data_place['m'].map(lambda x: list_months3[x-1])
      return df_data_place
   
   df_mm3 = get_data_place('df_mm3',country,place)
   df_m = get_data_place('df_m',country,place)

   dict_page_meta = {
      'title':f'Weer in {dict_destination["Place"]}, {dict_destination["Country"]} - Temperatuur en kans op regen'
      }
   return render_template(
      "country_place.html",
      dict_page_meta=dict_page_meta,
      country=country,place=place,
      dict_destination=dict_destination,
      dict_destinations_country=dict_destinations_clean[country],
      df_m=df_m,
      json_mm3=json.loads(df_mm3.to_json(orient='records'))
   )




@app.route('/<string:country>/')
def country(country):
   dict_destination = dict_destinations_clean[country]
   
   dict_topojson = {}
   for filename in os.listdir(folder_data_topojson):
      if filename.startswith(country+'_') or filename==f'{country}.json':
        
        dict_topojson[filename] = {
           'status': ('main' if (filename.endswith(f'{country}.json')) else 'secondary'),
        }

   def get_data_country(df_name,country):
      df_data_country = pd.read_csv(os.path.join(folder_data_processed,country,df_name+'.csv'))
      return(df_data_country)

   df_m_country = get_data_country('df_m_country',country)
   
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

   dict_page_meta = {
      'title':f'Weer en klimaat in {dict_countries[country]["country_name"]}'
      }
   dict_anchors = {
            'h2_temp':{'el':'h2',
                       'text':f'Temperatuur in {dict_countries[country]["country_name"]}'},
            'heatmap_tavg_med':{'el':'h3',
                                'text':'Gemiddelde temperatuur per maand'},
            'mapview_tavg_med':{'el':'h4',
                                'text':'Kaart (animatie) gemiddelde temperatuur'},
            'tableview_tavg_med':{'el':'h4',
                                'text':'Tabel gemiddelde temperatuur'},                                
            'heatmap_tmax_med':{'el':'h3',
                                'text':'Maximum temperatuur per maand'},
            'mapview_tmax_med':{'el':'h4',
                                'text':'Kaart (animatie) maximum temperatuur'},
            'tableview_tmax_med':{'el':'h4',
                                'text':'Tabel maximum temperatuur'},                                
            'h2_rain':{'el':'h2',
                       'text':f'Regen in {dict_countries[country]["country_name"]}'},
            'heatmap_prcp_sum':{'el':'h3',
                                'text':'Regen per maand'},
        }
   return render_template(
      "country.html",
      dict_page_meta=dict_page_meta,
      dict_anchors=dict_anchors,
      country=country,
      dict_destination=dict_destination,
      dict_destinations_country=dict_destinations_clean[country],
      df_m_country=df_m_country,
      df_map_m_country = df_map_m_country,
      json_m_country = json.loads(df_m_country.to_json(orient='records')),
      json_map_m_country = json.loads(df_map_m_country.to_json(orient='records')),
      dict_topojson = dict_topojson
   )

@app.route("/<path:path>/")
def page(path):
    page = pages.get_or_404(path)
    # dict_page_meta = {**dict_meta_empty, **dict_md_all_yaml[path], 'new_val': 'abc'}
    return render_template(
        "page.html",
        page=page,
        # dict_page_meta=dict_page_meta,
        # df_dummy_md=df_dummy
        )


# -------
# ------- MAIN -------------
# -------


if __name__ =='__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        freezer.freeze()
        # create_sitemap_xml(dict_website)
        # create_robots_txt(dict_website)
    else:
        # app.run(port=5000)
        app.run(host='0.0.0.0',debug=True,port=5777)
