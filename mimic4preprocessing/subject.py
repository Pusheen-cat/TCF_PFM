import numpy as np
import os
import pandas as pd

from mimic4preprocessing.util import dataframe_from_csv

def read_stays(subject_path):
    stays = dataframe_from_csv(os.path.join(subject_path, 'stays.csv'), index_col=None)
    stays.columns = stays.columns.str.upper()
    stays.INTIME = pd.to_datetime(stays.INTIME, errors='coerce')
    stays.OUTTIME = pd.to_datetime(stays.OUTTIME, errors='coerce')
    stays.ADMITTIME = pd.to_datetime(stays.ADMITTIME)
    stays.DISCHTIME = pd.to_datetime(stays.DISCHTIME)
    stays.DOB = pd.to_datetime(stays.DOB)
    stays.DOD = pd.to_datetime(stays.DOD)
    stays.DEATHTIME = pd.to_datetime(stays.DEATHTIME, errors='coerce')
    stays.sort_values(by=['ADMITTIME', 'DISCHTIME'], inplace=True)

    stays['edregtime_dt'] = pd.to_datetime(stays['EDREGTIME'], errors='coerce')
    stays['EDREGTIME'] = stays['edregtime_dt'].where(stays['edregtime_dt'].notna(), None)

    stays['STAY_ID'] = stays['STAY_ID'].astype('Int64')
    return stays


def read_diagnoses(subject_path):
    return dataframe_from_csv(os.path.join(subject_path, 'diagnoses.csv'), index_col=None)


def read_events(subject_path, remove_null=True):
    events = dataframe_from_csv(os.path.join(subject_path, 'events.csv'), index_col=None)
    events.columns = events.columns.str.upper()
    if remove_null:
        events = events[events.VALUE.notnull()]
    events.CHARTTIME = pd.to_datetime(events.CHARTTIME)
    events.HADM_ID = events.HADM_ID.fillna(value=-1).astype(int)
    events.STAY_ID = events.STAY_ID.fillna(value=-1).astype(int)
    events.VALUEUOM = events.VALUEUOM.fillna('').astype(str)
    # events.sort_values(by=['CHARTTIME', 'ITEMID', 'STAY_ID'], inplace=True)
    return events


def get_events_for_stay(events, icustayid, intime=None, outtime=None):
    idx = (events.STAY_ID == icustayid)
    if intime is not None and outtime is not None:
        idx = idx | ((events.CHARTTIME >= intime) & (events.CHARTTIME <= outtime))
    events = events[idx]
    del events['STAY_ID']
    return events

def get_events_for_hosp(events, admittime=None, dischtime=None, pre_admin_hr = 24, post_disch_hr = 0):
    if admittime is not None and dischtime is not None:
        idx = (events.CHARTTIME >= (admittime - pd.Timedelta(hours=pre_admin_hr))) & (events.CHARTTIME <= (dischtime + pd.Timedelta(hours=post_disch_hr)))
    events = events[idx]
    del events['HADM_ID']
    return events


def add_hours_elpased_to_events(events, dt, remove_charttime=False):
    events = events.copy()
    events['HOURS'] = (events.CHARTTIME - dt).apply(lambda s: s / np.timedelta64(1, 's')) / 60./60
    if remove_charttime:
        del events['CHARTTIME']
    return events


def convert_events_to_timeseries(events, variable_column='VARIABLE', variables=[]):
    metadata = events[['CHARTTIME', 'STAY_ID']].sort_values(by=['CHARTTIME', 'STAY_ID'])\
                    .drop_duplicates(keep='first').set_index('CHARTTIME')
    timeseries = events[['CHARTTIME', variable_column, 'VALUE']]\
                    .sort_values(by=['CHARTTIME', variable_column, 'VALUE'], axis=0)\
                    .drop_duplicates(subset=['CHARTTIME', variable_column], keep='last')
    timeseries = timeseries.pivot(index='CHARTTIME', columns=variable_column, values='VALUE')\
                    .merge(metadata, left_index=True, right_index=True)\
                    .sort_index(axis=0).reset_index()
    for v in variables:
        if v not in timeseries:
            timeseries[v] = np.nan
    return timeseries

def convert_events_to_timeseries_v2(events, variable_column='VARIABLE', variables=[]):
    # CHARTTIME 기준으로 STAY_ID, HADM_ID 메타데이터 유지
    metadata = (
        events[['CHARTTIME', 'STAY_ID', 'HADM_ID']]
        .sort_values(by=['CHARTTIME', 'STAY_ID', 'HADM_ID'])
        .drop_duplicates(subset=['CHARTTIME'], keep='first')
        .set_index('CHARTTIME')
    )

    # (CHARTTIME, VARIABLE) 당 하나의 VALUE만 남김
    timeseries = (
        events[['CHARTTIME', variable_column, 'VALUE']]
        .sort_values(by=['CHARTTIME', variable_column, 'VALUE'], axis=0)
        .drop_duplicates(subset=['CHARTTIME', variable_column], keep='last')
    )

    # long → wide + metadata 병합
    timeseries = (
        timeseries
        .pivot(index='CHARTTIME', columns=variable_column, values='VALUE')
        .merge(metadata, left_index=True, right_index=True)
        .sort_index(axis=0)
        .reset_index()
    )

    # 반드시 포함되어야 하는 변수 컬럼 보장
    for v in variables:
        if v not in timeseries:
            timeseries[v] = np.nan

    timeseries['HADM_ID'] = timeseries['HADM_ID'].astype('Int64')
    timeseries['STAY_ID'] = timeseries['STAY_ID'].astype('Int64')

    return timeseries

def get_first_valid_from_timeseries(timeseries, variable):
    if variable in timeseries:
        idx = timeseries[variable].notnull()
        if idx.any():
            loc = np.where(idx)[0][0]
            return timeseries[variable].iloc[loc]
    return np.nan
