from datetime import datetime,timedelta
import matplotlib.pyplot as plt
from meteostat import Point, Daily, Hourly
from typing import List, Dict, Tuple, Optional
import pandas as pd
from openpyxl import load_workbook
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import numpy as np
import os
import math
import polars as pl
import polars.selectors as cs


## -------- Input data -------- 


def xlsx_sheet_to_df(filename:str,sheetname:str) -> pd.DataFrame:
    wb = load_workbook(filename)
    ws = wb[sheetname]
    data = list(ws.values)
    headers=next(iter(data))
    df_out = pd.DataFrame(data[1:],columns=headers)
    return(df_out)


def xlsx_add_latlon(filename:str,sheetname:str):
    df_xlsx = xlsx_sheet_to_df(filename,sheetname)
    geolocator = Nominatim(user_agent='myapplication')
    geocode = RateLimiter(geolocator.geocode,min_delay_seconds=1)
    boolean_overwrite = False
    for i,v in df_xlsx.iterrows():
        lat = v['Lat']
        # print(lat)
        # print(np.isnan(lat) or lat is None)
        if np.isnan(lat) or lat is None:
            boolean_overwrite = True
            dest = f"{v['Place']}, {v['Country']}"
            print(dest)
            # loc = geolocator.geocode(dest)
            
            loc = geocode(dest,language='nl')
            if loc is not None:
                df_xlsx.loc[i,('Lat')]=float(loc.raw['lat'])
                df_xlsx.loc[i,('Lon')]=float(loc.raw['lon'])
    if boolean_overwrite:
        print(f'Added latlon to {filename}')
        df_xlsx.to_excel(filename,sheet_name=sheetname,index=False)
    return(df_xlsx)


def create_dict_destinations(df_destinations):
    cols = list(df_destinations.columns)
    dict_destinations = {}
    for i,v in df_destinations.iterrows():
        country = v['Country'].lower().replace(' ','-')
        place = v['Place'].lower().replace(' ','-')
        lat = v['Lat']
        if country not in dict_destinations:
            dict_destinations[country]={}
        dict_destinations[country][place] = {col:v[col] for col in cols}
        
        # if lat is None or np.isnan(lat):
        #     dict_latlon = add_latlon(country=v['Country'],place=v['Place'])
        #     dict_destinations[country][place].update(dict_latlon)
    return(dict_destinations)


## -------- Download data (helper functions) -------- 


def get_weather(lat,lon,start,end,frequency='daily'):
    if frequency=='daily':
        data = Daily(Point(lat,lon),start,end)
    elif frequency=='hourly':
        data = Hourly(Point(lat,lon),start,end)
    data = data.fetch()
    data = data[data.index<(datetime.now()-timedelta(days=1))]
    return data


def download_add_daily(country,place,dict_destinations,last_n_years=7):
    dict_cp = dict_destinations[country][place]
    lat,lon = dict_cp['Lat'],dict_cp['Lon']
    days = math.ceil(last_n_years*365.25)
    start = (datetime.today()-timedelta(days=days))
    end = datetime.today()
    data_raw = get_weather(lat=lat,lon=lon,start=start,end=end,frequency='daily')
    if data_raw.shape[0]>0:
        df_cp_d = pl.from_pandas(data_raw,include_index=True).select(
            ['time','tavg','tmin','tmax','prcp','wspd','pres']
        ).cast(
            {'time':pl.Date,
            'tavg':pl.Float64,'tmin':pl.Float64,'tmax':pl.Float64,
            'prcp':pl.Float64,'wspd':pl.Float64,'pres':pl.Float64}
        ).filter(
            (pl.col('time').max()-pl.col('time')).dt.total_days()<=(365.25*last_n_years)
        ).with_columns(
            # pl.col('time').dt.strftime('%m-%d').alias('md'),
            pl.col('time').dt.year().alias('y'),
            # pl.col('time').dt.strftime('%m').alias('m_'),
            pl.col('time').dt.month().alias('m'),
            pl.when(pl.col("time").dt.day() > 20)
                .then(3)
                .when(pl.col("time").dt.day() > 10)
                .then(2)
                .otherwise(1)
                .alias("m3"),
            pl.col('time').dt.day().alias('d'),
            pl.when(pl.col('prcp')==0).then(0).when(pl.col('prcp')>0).then(1).otherwise(None).alias('rain')
        ).cast({'m3':pl.Int8,'rain':pl.Int8})
        return(df_cp_d)


def download_add_hourly(country,place,dict_destinations,last_n_years=7):
    dict_cp = dict_destinations[country][place]
    lat,lon = dict_cp['Lat'],dict_cp['Lon']
    days = math.ceil(last_n_years*365.25)
    start = (datetime.today()-timedelta(days=days))
    end = datetime.today()
    data_raw = get_weather(lat=lat,lon=lon,start=start,end=end,frequency='hourly')
    if data_raw.shape[0]>0:
        df_cp_h = pl.from_pandas(data_raw,include_index=True).select(
            ['time','temp','rhum','prcp','wspd','pres','coco']
        ).cast(
            {'time':pl.Datetime,
            'temp':pl.Float64,'rhum':pl.Float64,
            'prcp':pl.Float64,'wspd':pl.Float64,'pres':pl.Float64,
            'coco':pl.Float64
            }
        ).with_columns(
            pl.col('time').dt.year().alias('y'),
            pl.col('time').dt.month().alias('m'),
            pl.col('time').dt.day().alias('d'),
            pl.col('time').dt.hour().alias('h'),
            pl.when(pl.col("time").dt.day() > 20)
                .then(3)
                .when(pl.col("time").dt.day() > 10)
                .then(2)
                .otherwise(1)
                .alias("m3"),
            pl.when(pl.col('prcp')==0).then(0).when(pl.col('prcp')>0).then(1).otherwise(None).alias('rain')
        ).cast({'m3':pl.Int8,'rain':pl.Int8})
        return (df_cp_h)


## -------- Preprocess and save data -------- 


def dictdfs_write_csv(dict_dfs,country,place=None,folder_data_processed='./data/processed'):
    dir_csv = os.path.join(folder_data_processed,'' if (country is None) else country,'' if (place is None) else place )
    for df in dict_dfs:
        os.makedirs(dir_csv,exist_ok=True)
        fp_csv = os.path.join(dir_csv,df+'.csv')
        dict_dfs[df].write_csv(fp_csv,separator=',')


def preprocess_daily(df_cp_d):
    """Create dict with multiple aggregate df's: mm3d, mm3, m
    All averages (except rain) are the averages of the upper and lower bound, defined as 90% quantile
    rain_pct, rain_sum is taken over all days (i.e. not deleting extreme points)
    """
    # df_cp_d = load_filter_add_daily(country=country,place=place,last_n_years=last_n_years,folder_data_raw=folder_data_raw)
    # df_cp_d = download_add_daily(country,place,dict_destinations,last_n_years=last_n_years)
    cols_d = ['tmin','tavg','tmax','prcp','wspd']
    df_ub_d = df_cp_d.group_by(['m','m3','d']).agg(
        pl.col(c).quantile(0.9,'lower').alias(str(c)+'_ub') for c in cols_d
    )
    df_lb_d = df_cp_d.group_by(['m','m3','d']).agg(
        pl.col(c).quantile(0.1,'higher').alias(str(c)+'_lb') for c in cols_d
    )
    df_rain = df_cp_d.group_by(['m','m3','d']).agg(
        pl.col('rain').mean().round(2).alias('rain_pct')
    )    
    df_mm3d = df_lb_d.join(
        df_ub_d,on=['m','m3','d'],how='full', coalesce=True
    ).join(
        df_rain,on=['m','m3','d'],how='full', coalesce=True
    ).with_columns(
        ((pl.col(str(c)+'_ub')+pl.col(str(c)+'_lb'))/2).round(1).alias(str(c)+'_avg') for c in cols_d
        ).select(
            cs.by_dtype([pl.Int8]),cs.matches('_avg$'),cs.matches('_pct$')
        ).sort(['m','d'])

    df_m = df_mm3d.group_by(['m']).agg(
        cs.matches('^tmin|^tmax|^tavg|^wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
        
        cs.matches('rain_pct').sum().round(0).alias('rain_sum'),
        cs.matches('rain_pct').mean().round(2).alias('rain_pct'),
        cs.matches('prcp').sum().round(0).name.map(lambda c:c.replace('_avg','_sum'))
    ).sort(['m'])

    df_mm3 = df_mm3d.group_by(['m','m3']).agg(
        cs.matches('^tmin|^tmax|^tavg|^wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
        cs.matches('rain_pct').sum().round(0).alias('rain_sum'),
        cs.matches('rain_pct').mean().round(2).alias('rain_pct'),
        cs.matches('prcp').sum().round(0).name.map(lambda c:c.replace('_avg','_sum'))
    ).sort(['m','m3'])
    return({'df_mm3d':df_mm3d,
            'df_mm3':df_mm3,
            'df_m':df_m
           })


def preprocess_hourly(df_cp_h):
    # df_cp_h = download_add_hourly(country,place,dict_destinations,last_n_years=last_n_years)
    cols_h = ['temp','rhum','prcp','wspd'] # and coco
    df_ub_h = df_cp_h.group_by(['m','m3','d','h']).agg(
        pl.col(c).quantile(0.9,'lower').alias(str(c)+'_ub') for c in cols_h
    )
    df_lb_h = df_cp_h.group_by(['m','m3','d','h']).agg(
        pl.col(c).quantile(0.1,'higher').alias(str(c)+'_lb') for c in cols_h
    )
    df_rain = df_cp_h.group_by(['m','m3','d','h']).agg(
        pl.col('rain').mean().round(2).alias('rain_pct')
    )  
    
    # df_mm3dh used for other calcs, not part of output:
    df_mm3dh = df_lb_h.join(
        df_ub_h,on=['m','m3','d','h'],how='full',coalesce=True
    ).join(
        df_rain,on=['m','m3','d','h'],how='full', coalesce=True
    ).with_columns(
        ((pl.col(str(c)+'_ub')+pl.col(str(c)+'_lb'))/2).round(1).alias(str(c)+'_avg') for c in cols_h
        ).select(
        cs.by_dtype([pl.Int8]),pl.col('temp_lb'),pl.col('temp_ub'),cs.matches('_avg$'),cs.matches('_pct$')
    )
    df_mm3h = df_mm3dh.group_by(['m','m3','h']).agg(
        cs.matches('temp|rhum|wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
        cs.matches('rain_pct').mean().round(2).alias('rain_pct'),
    ).sort(['m','m3','h'])
    df_mh = df_mm3dh.group_by(['m','h']).agg(
        cs.matches('temp|rhum|wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
        cs.matches('rain_pct').mean().round(2).alias('rain_pct')
    ).sort(['m','h'])

    # coco calculations, df_mm3dhc used for other calcs
    df_mm3dhc = df_cp_h.group_by(
        ['m','m3','d','h','coco']
    ).len().cast({'len':pl.Int8}).filter(
        pl.col('coco').is_not_null()
    ).filter(
        pl.col('coco')>0
    ).pivot(
        'coco',index=['m','m3','d','h'],values='len'
    ).fill_null(0).unpivot(
        cs.exclude('m','m3','d','h'),index=['m','m3','d','h']
    ).cast({'variable':pl.Float64}).with_columns(
        (pl.col('value')/pl.col('value').sum().over(['m','m3','d','h'])).round(3)
    ).rename({'variable':'coco','value':'coco_pct'})

    # df_mhc = df_mm3dhc.group_by(['m','h','coco']).agg(pl.col('coco_pct').mean().round(3))
    df_mc = df_mm3dhc.group_by(['m','coco']).agg(pl.col('coco_pct').mean().round(3))
    df_mm3c = df_mm3dhc.group_by(['m','m3','coco']).agg(pl.col('coco_pct').mean().round(3))
    
    return({
        'df_mc':df_mc,
        'df_mm3c':df_mm3c,
        'df_mm3h':df_mm3h,
        'df_mh':df_mh
    })


## -------- Postprocess and save data -------- 


def combine_csvs_country(country,folder_data_processed='./data/processed'):
    dict_dfs_country={}
    folder_country = os.path.join(folder_data_processed,country)
    # Create a dictionary of data frames that combines similar csvs:
    for p in [x for x in os.listdir(folder_country) if os.path.isdir(os.path.join(folder_country,x))]:
        csvs_p = os.listdir(os.path.join(folder_country,p))
        for csv_p in csvs_p:
            # print(f'{p} {csv_p}')
            csv_pc = csv_p.replace('.csv','_country')
            df_p = pl.read_csv(os.path.join(folder_country,p,csv_p))
            df_p = df_p.with_columns(
                pl.lit(country).alias('country'),
                pl.lit(p).alias('place'),
            )
            # Debug:
            for col in ['rain_pct','prcp_avg','wspd_avg','coco','coco_pct']:
                if col in df_p.columns:
                    df_p = df_p.cast({col:pl.Float64})
            for col in ['m','m3','d','h','rain']:
                if col in df_p.columns:
                    df_p = df_p.cast({col:pl.Int8})
            if csv_pc in dict_dfs_country:
                # print(f'{csv_pc} - {p}')
                dict_dfs_country[csv_pc]=pl.concat([dict_dfs_country[csv_pc],df_p])
            else:
                dict_dfs_country[csv_pc]=df_p
    # Sort the data frames:
    for k in dict_dfs_country:
        cols_sort = ['country','place']
        for col in ['m','m3','d','h','coco']:
            if col in dict_dfs_country[k].columns:
                cols_sort += [col]
        dict_dfs_country[k] = dict_dfs_country[k].sort(cols_sort)
    return(dict_dfs_country)