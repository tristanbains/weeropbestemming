import os
import polars as pl
import polars.selectors as cs
import pandas as pd
import numpy as np
from datetime import date


def dictdfs_write_csv(dict_dfs,country,place=None,folder_data_processed='./data/processed'):
    dir_csv = os.path.join(folder_data_processed,'' if (country is None) else country,'' if (place is None) else place )
    for df in dict_dfs:
        os.makedirs(dir_csv,exist_ok=True)
        fp_csv = os.path.join(dir_csv,df+'.csv')
        dict_dfs[df].write_csv(fp_csv,separator=',')


def preprocess_daily(country,place,dict_destinations,last_n_years=7):
    """Create dict with multiple aggregate df's: mm3d, mm3, m
    All averages (except rain) are the averages of the upper and lower bound, defined as 90% quantile
    rain_pct, rain_sum is taken over all days (i.e. not deleting extreme points)
    """
    # df_cp_d = load_filter_add_daily(country=country,place=place,last_n_years=last_n_years,folder_data_raw=folder_data_raw)
    df_cp_d = download_add_daily(country,place,dict_destinations,last_n_years=last_n_years)
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


def preprocess_hourly(country,place,dict_destinations,last_n_years=5):
    df_cp_h = download_add_hourly(country,place,dict_destinations,last_n_years=last_n_years)
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




# def load_filter_add_daily(country,place,last_n_years=7,folder_data_raw='./data/raw'):
#     # Load daily data:
#     fp_cp_d = os.path.join(folder_data_raw,country,place,'weather_daily.csv')
#     df_cp_d = pl.read_csv(fp_cp_d,try_parse_dates=True).select(
#         ['time','tavg','tmin','tmax','prcp','wspd','pres']
#     ).cast(
#         {'time':pl.Date,
#          'tavg':pl.Float64,'tmin':pl.Float64,'tmax':pl.Float64,
#          'prcp':pl.Float64,'wspd':pl.Float64,'pres':pl.Float64}
#     ).filter(
#         (pl.col('time').max()-pl.col('time')).dt.total_days()<=(365.25*last_n_years)
#     ).with_columns(
#         # pl.col('time').dt.strftime('%m-%d').alias('md'),
#         pl.col('time').dt.year().alias('y'),
#         # pl.col('time').dt.strftime('%m').alias('m_'),
#         pl.col('time').dt.month().alias('m'),
#         pl.when(pl.col("time").dt.day() > 20)
#             .then(3)
#             .when(pl.col("time").dt.day() > 10)
#             .then(2)
#             .otherwise(1)
#             .alias("m3"),
#         pl.col('time').dt.day().alias('d'),
#         pl.when(pl.col('prcp')==0).then(0).when(pl.col('prcp')>0).then(1).otherwise(None).alias('rain')
#     ).cast({'m3':pl.Int8,'rain':pl.Int8})
#     return(df_cp_d)


# def preprocess_daily(country,place,last_n_years=7,folder_data_raw='./data/raw'):
#     """Create dict with multiple aggregate df's: mm3d, mm3, m
#     All averages (except rain) are the averages of the upper and lower bound, defined as 90% quantile
#     rain_pct, rain_sum is taken over all days (i.e. not deleting extreme points)
#     """
#     df_cp_d = load_filter_add_daily(country=country,place=place,last_n_years=last_n_years,folder_data_raw=folder_data_raw)
#     cols_d = ['tmin','tavg','tmax','prcp','wspd']
#     df_ub_d = df_cp_d.group_by(['m','m3','d']).agg(
#         pl.col(c).quantile(0.9,'lower').alias(str(c)+'_ub') for c in cols_d
#     )
#     df_lb_d = df_cp_d.group_by(['m','m3','d']).agg(
#         pl.col(c).quantile(0.1,'higher').alias(str(c)+'_lb') for c in cols_d
#     )
#     df_rain = df_cp_d.group_by(['m','m3','d']).agg(
#         pl.col('rain').mean().round(2).alias('rain_pct')
#     )    
#     df_mm3d = df_lb_d.join(
#         df_ub_d,on=['m','m3','d'],how='full', coalesce=True
#     ).join(
#         df_rain,on=['m','m3','d'],how='full', coalesce=True
#     ).with_columns(
#         ((pl.col(str(c)+'_ub')+pl.col(str(c)+'_lb'))/2).round(1).alias(str(c)+'_avg') for c in cols_d
#         ).select(
#             cs.by_dtype([pl.Int8]),cs.matches('_avg$'),cs.matches('_pct$')
#         ).sort(['m','d'])

#     df_m = df_mm3d.group_by(['m']).agg(
#         cs.matches('^tmin|^tmax|^tavg|^wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
        
#         cs.matches('rain_pct').sum().round(0).alias('rain_sum'),
#         cs.matches('rain_pct').mean().round(2).alias('rain_pct'),
#         cs.matches('prcp').sum().round(0).name.map(lambda c:c.replace('_avg','_sum'))
#     ).sort(['m'])

#     df_mm3 = df_mm3d.group_by(['m','m3']).agg(
#         cs.matches('^tmin|^tmax|^tavg|^wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
#         cs.matches('rain_pct').sum().round(0).alias('rain_sum'),
#         cs.matches('rain_pct').mean().round(2).alias('rain_pct'),
#         cs.matches('prcp').sum().round(0).name.map(lambda c:c.replace('_avg','_sum'))
#     ).sort(['m','m3'])
#     return({'df_mm3d':df_mm3d,
#             'df_mm3':df_mm3,
#             'df_m':df_m
#            })



# def preprocess_hourly(country,place,dict_destinations,last_n_years=5):
#     df_cp_h = download_add_hourly(country,place,dict_destinations,last_n_years=last_n_years)
#     cols_h = ['temp','rhum','prcp','wspd'] # and coco
#     df_ub_h = df_cp_h.group_by(['m','m3','d','h']).agg(
#         pl.col(c).quantile(0.9,'lower').alias(str(c)+'_ub') for c in cols_h
#     )
#     df_lb_h = df_cp_h.group_by(['m','m3','d','h']).agg(
#         pl.col(c).quantile(0.1,'higher').alias(str(c)+'_lb') for c in cols_h
#     )
#     df_rain = df_cp_h.group_by(['m','m3','d','h']).agg(
#         pl.col('rain').mean().round(2).alias('rain_pct')
#     )  
    
#     # df_mm3dh used for other calcs, not part of output:
#     df_mm3dh = df_lb_h.join(
#         df_ub_h,on=['m','m3','d','h'],how='full',coalesce=True
#     ).join(
#         df_rain,on=['m','m3','d','h'],how='full', coalesce=True
#     ).with_columns(
#         ((pl.col(str(c)+'_ub')+pl.col(str(c)+'_lb'))/2).round(1).alias(str(c)+'_avg') for c in cols_h
#         ).select(
#         cs.by_dtype([pl.Int8]),pl.col('temp_lb'),pl.col('temp_ub'),cs.matches('_avg$'),cs.matches('_pct$')
#     )
#     df_mm3h = df_mm3dh.group_by(['m','m3','h']).agg(
#         cs.matches('temp|rhum|wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
#         cs.matches('rain_pct').mean().round(2).alias('rain_pct'),
#     ).sort(['m','m3','h'])
#     df_mh = df_mm3dh.group_by(['m','h']).agg(
#         cs.matches('temp|rhum|wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
#         cs.matches('rain_pct').mean().round(2).alias('rain_pct')
#     ).sort(['m','h'])

#     # coco calculations, df_mm3dhc used for other calcs
#     df_mm3dhc = df_cp_h.group_by(
#         ['m','m3','d','h','coco']
#     ).len().cast({'len':pl.Int8}).filter(
#         pl.col('coco').is_not_null()
#     ).filter(
#         pl.col('coco')>0
#     ).pivot(
#         'coco',index=['m','m3','d','h'],values='len'
#     ).fill_null(0).unpivot(
#         cs.exclude('m','m3','d','h'),index=['m','m3','d','h']
#     ).cast({'variable':pl.Float64}).with_columns(
#         (pl.col('value')/pl.col('value').sum().over(['m','m3','d','h'])).round(3)
#     ).rename({'variable':'coco','value':'coco_pct'})

#     # df_mhc = df_mm3dhc.group_by(['m','h','coco']).agg(pl.col('coco_pct').mean().round(3))
#     df_mc = df_mm3dhc.group_by(['m','coco']).agg(pl.col('coco_pct').mean().round(3))
#     df_mm3c = df_mm3dhc.group_by(['m','m3','coco']).agg(pl.col('coco_pct').mean().round(3))

    
    
#     return({
#         'df_mc':df_mc,
#         'df_mm3c':df_mm3c,
#         'df_mm3h':df_mm3h,
#         'df_mh':df_mh
#     })


# def dictdfs_write_csv(dict_dfs,country,place=None,folder_data_processed='./data/processed'):
#     dir_csv = os.path.join(folder_data_processed,'' if (country is None) else country,'' if (place is None) else place )
#     for df in dict_dfs:
#         os.makedirs(dir_csv,exist_ok=True)
#         fp_csv = os.path.join(dir_csv,df+'.csv')
#         dict_dfs[df].write_csv(fp_csv,separator=',')


# # def load_filter_add_cp(country,place,last_n_years=5,folder_data_raw='./data/raw'):
# #     # Load daily data:
# #     fp_cp_d = os.path.join(folder_data_raw,country,place,'weather_daily.csv')
# #     df_cp_d = pl.read_csv(fp_cp_d,try_parse_dates=True).select(
# #         ['time','tavg','tmin','tmax','prcp','wspd','pres']
# #     ).cast(
# #         {'time':pl.Date,
# #          'tavg':pl.Float64,'tmin':pl.Float64,'tmax':pl.Float64,
# #          'prcp':pl.Float64,'wspd':pl.Float64,'pres':pl.Float64}
# #     ).filter(
# #         (pl.col('time').max()-pl.col('time')).dt.total_days()<=(365.25*last_n_years)
# #     ).with_columns(
# #         pl.col('time').dt.year().alias('y'),
# #         pl.col('time').dt.month().alias('m'),
# #         pl.when(pl.col("time").dt.day() > 20)
# #             .then(3)
# #             .when(pl.col("time").dt.day() > 10)
# #             .then(2)
# #             .otherwise(1)
# #             .alias("m3"),
# #         pl.col('time').dt.day().alias('d'),
# #         pl.when(pl.col('prcp')==0).then(0).when(pl.col('prcp')>0).then(1).otherwise(None).alias('rain')
# #     ).cast({'m3':pl.Int8,'rain':pl.Int8})
# #     # Load hourly data:
# #     fp_cp_h = os.path.join(folder_data_raw,country,place,'weather_hourly.csv')
# #     df_cp_h = pl.read_csv(fp_cp_h,try_parse_dates=True).select(
# #         ['time','temp','rhum','prcp','wspd','pres','coco']
# #     ).cast(
# #         {'time':pl.Datetime,
# #          'temp':pl.Float64,'rhum':pl.Float64,
# #          'prcp':pl.Float64,'wspd':pl.Float64,'pres':pl.Float64,
# #          'coco':pl.Float64
# #         }
# #     ).filter(
# #         (pl.col('time').max()-pl.col('time')).dt.total_days()<=(365.25*last_n_years)
# #     ).with_columns(
# #         pl.col('time').dt.year().alias('y'),
# #         pl.col('time').dt.month().alias('m'),
# #         pl.col('time').dt.day().alias('d'),
# #         pl.col('time').dt.hour().alias('h'),
# #         pl.when(pl.col("time").dt.day() > 20)
# #             .then(3)
# #             .when(pl.col("time").dt.day() > 10)
# #             .then(2)
# #             .otherwise(1)
# #             .alias("m3"),
# #         pl.when(pl.col('prcp')==0).then(0).when(pl.col('prcp')>0).then(1).otherwise(None).alias('rain')
# #     ).cast({'m3':pl.Int8,'rain':pl.Int8})
# #     return({'df_cp_h':df_cp_h,'df_cp_d':df_cp_d})


# # def create_output_cp(country,place,last_n_years=5,folder_data_raw='./data/raw'):
# #     data_cp = load_filter_add_cp(country,place,last_n_years=last_n_years,folder_data_raw=folder_data_raw)
# #     df_cp_d = data_cp['df_cp_d']
# #     df_cp_h = data_cp['df_cp_h']
# #     cols_d = ['tmin','tavg','tmax','prcp','rain','wspd']
# #     cols_h = ['temp','rhum','prcp','rain','wspd'] # and coco
# #     df_ub_d = df_cp_d.group_by(['m','m3','d']).agg(
# #         pl.col(c).quantile(0.9,'lower').alias(str(c)+'_ub') for c in cols_d
# #     )
# #     df_lb_d = df_cp_d.group_by(['m','m3','d']).agg(
# #         pl.col(c).quantile(0.1,'higher').alias(str(c)+'_lb') for c in cols_d
# #     )
# #     df_ub_h = df_cp_h.group_by(['m','m3','d','h']).agg(
# #         pl.col(c).quantile(0.9,'lower').alias(str(c)+'_ub') for c in cols_h
# #     )
# #     df_lb_h = df_cp_h.group_by(['m','m3','d','h']).agg(
# #         pl.col(c).quantile(0.1,'higher').alias(str(c)+'_lb') for c in cols_h
# #     )
# #     # Aggregates based on hourly data:
# #     # df_mm3dh used for other calcs, not part of output:
# #     df_mm3dh = df_lb_h.join(df_ub_h,on=['m','m3','d','h'],how='full',coalesce=True).with_columns(
# #         ((pl.col(str(c)+'_ub')+pl.col(str(c)+'_lb'))/2).round(1).alias(str(c)+'_avg') for c in cols_h
# #         ).select(
# #         cs.by_dtype([pl.Int8]),pl.col('temp_lb'),pl.col('temp_ub'),cs.matches('avg')
# #     )
# #     df_mm3h = df_mm3dh.group_by(['m','m3','h']).agg(
# #         cs.matches('temp|rhum|wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med'))
# #     ).sort(['m','m3','h'])
# #     df_mh = df_mm3dh.group_by(['m','h']).agg(
# #         cs.matches('temp|rhum|wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med'))
# #     ).sort(['m','h'])
# #     # Aggregates based on daily data:
# #     df_mm3d = df_lb_d.join(df_ub_d,on=['m','m3','d'],how='full', coalesce=True).with_columns(
# #         ((pl.col(str(c)+'_ub')+pl.col(str(c)+'_lb'))/2).round(1).alias(str(c)+'_avg') for c in cols_d
# #         ).select(
# #             cs.by_dtype([pl.Int8]),cs.matches('_avg$')
# #         ).sort(['m','d'])
# #     df_m = df_mm3d.group_by(['m']).agg(
# #         cs.matches('t|wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
# #         cs.matches('rain|prcp').sum().round(0).name.map(lambda c:c.replace('_avg','_sum'))
# #     ).sort(['m'])
# #     df_mm3 = df_mm3d.group_by(['m','m3']).agg(
# #         cs.matches('t|wspd').median().round(1).name.map(lambda c:c.replace('_avg','_med')),
# #         cs.matches('rain|prcp').sum().round(0).name.map(lambda c:c.replace('_avg','_sum'))
# #     ).sort(['m','m3'])
# #     return({
# #         'df_mm3h':df_mm3h,
# #         'df_mh':df_mh,
# #         # 'df_mm3dh':df_mm3dh,
# #         'df_mm3d':df_mm3d,
# #         'df_mm3':df_mm3,
# #         'df_m':df_m,
# #     })

