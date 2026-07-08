import argparse
import os
import sys
from tqdm import tqdm
import pandas as pd

# Allow running this file directly (python <path>): put the repo root on sys.path.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mimic4preprocessing.subject import read_stays, read_diagnoses, read_events, get_events_for_stay, get_events_for_hosp,\
    add_hours_elpased_to_events
from mimic4preprocessing.subject import convert_events_to_timeseries, get_first_valid_from_timeseries, convert_events_to_timeseries_v2
from mimic4preprocessing.preprocessing import read_itemid_to_variable_map, map_itemids_to_variables, clean_events
from mimic4preprocessing.preprocessing import assemble_episodic_data
"""
Step 03 - Extract per-admission episodes / timeseries from the per-subject data.
Usage:  python mimic4preprocessing/scripts/03_extract_episodes.py <A_extract_subjects_dir>
"""

parser = argparse.ArgumentParser(description='Extract episodes from per-subject data.')
parser.add_argument('subjects_root_path', type=str, help='Directory containing subject sub-directories.')
parser.add_argument('--variable_map_file', type=str,
                    default=os.path.join(os.path.dirname(__file__), '../resources/itemid_to_variable_map.csv'),
                    help='CSV containing ITEMID-to-VARIABLE map.')
parser.add_argument('--reference_range_file', type=str,
                    default=os.path.join(os.path.dirname(__file__), '../resources/variable_ranges.csv'),
                    help='CSV containing reference ranges for VARIABLEs.')
args, _ = parser.parse_known_args()

var_map = read_itemid_to_variable_map(args.variable_map_file)
variables = var_map.VARIABLE.unique()

for subject_dir in tqdm(os.listdir(args.subjects_root_path), desc='Iterating over subjects'):
    dn = os.path.join(args.subjects_root_path, subject_dir)
    try:
        subject_id = int(subject_dir)
        if not os.path.isdir(dn):
            raise Exception
    except:
        continue

    try:
        # reading tables of this subject
        stays = read_stays(os.path.join(args.subjects_root_path, subject_dir))
        diagnoses = read_diagnoses(os.path.join(args.subjects_root_path, subject_dir))
        events = read_events(os.path.join(args.subjects_root_path, subject_dir))
    except:
        sys.stderr.write('Error reading from disk for subject: {}\n'.format(subject_id))
        raise AttributeError
        continue

    episodic_data = assemble_episodic_data(stays, diagnoses)

    # cleaning and converting to time series
    events = map_itemids_to_variables(events, var_map)
    events = clean_events(events)
    if events.shape[0] == 0:
        # no valid events for this subject
        continue
    timeseries = convert_events_to_timeseries_v2(events, variables=variables)

    # extracting separate episodes
    icu_idx = 0
    for i in range(stays.shape[0]):
        hadm_id = stays.HADM_ID.iloc[i]
        stay_id = stays.STAY_ID.iloc[i]
        intime = stays.INTIME.iloc[i]
        outtime = stays.OUTTIME.iloc[i]
        edregtime = stays.EDREGTIME.iloc[i]
        admittime = stays.ADMITTIME.iloc[i]
        dischtime = stays.DISCHTIME.iloc[i]
        dob = stays.DOB.iloc[i]
        # print(subject_dir, stay_id, intime, outtime)
        # if i == 3: raise AttributeError

        if i == 0:
            episode = timeseries.copy()
            episode = add_hours_elpased_to_events(episode, dob).set_index('HOURS').sort_index(axis=0)
            columns = list(episode.columns)
            columns_sorted = sorted(columns, key=(lambda x: "" if x == "Hours" else x))
            episode = episode[columns_sorted]
            episode.to_csv(
                os.path.join(args.subjects_root_path, subject_dir, 'full_timeseries.csv'.format(icu_idx)),
                index_label='Hours')


        episode = get_events_for_stay(timeseries.copy(), stay_id, intime, outtime)
        if episode.shape[0] == 0:
            pass
            #assert pd.isna(stay_id)
            # no data for this episode
        else:
            icu_idx +=1
            episode = add_hours_elpased_to_events(episode, intime).set_index('HOURS').sort_index(axis=0)
            if hadm_id in episodic_data.index:
                episodic_data.loc[hadm_id, 'Weight'] = get_first_valid_from_timeseries(episode, 'Weight')
                episodic_data.loc[hadm_id, 'Height'] = get_first_valid_from_timeseries(episode, 'Height')
            episodic_data.loc[episodic_data.index == hadm_id].to_csv(os.path.join(args.subjects_root_path, subject_dir, 'episode{}.csv'.format(icu_idx)), index_label='Icustay')
            columns = list(episode.columns)
            columns_sorted = sorted(columns, key=(lambda x: "" if x == "Hours" else x))
            episode = episode[columns_sorted]
            episode.to_csv(os.path.join(args.subjects_root_path, subject_dir, 'episode{}_timeseries.csv'.format(icu_idx)),
                           index_label='Hours')

        episode_adm = get_events_for_hosp(timeseries, admittime if edregtime is None else edregtime, dischtime)
        if not episode_adm.shape[0] == 0:
            episode_adm = add_hours_elpased_to_events(episode_adm, admittime).set_index('HOURS').sort_index(axis=0)
            if hadm_id in episodic_data.index:
                episodic_data.loc[hadm_id, 'Weight'] = get_first_valid_from_timeseries(episode_adm, 'Weight')
                episodic_data.loc[hadm_id, 'Height'] = get_first_valid_from_timeseries(episode_adm, 'Height')
            episodic_data.loc[episodic_data.index == hadm_id].to_csv(os.path.join(args.subjects_root_path, subject_dir, 'adm_episode{}.csv'.format(i+1)), index_label='Hadm_id')
            columns = list(episode_adm.columns)
            columns_sorted = sorted(columns, key=(lambda x: "" if x == "Hours" else x))
            episode_adm = episode_adm[columns_sorted]
            episode_adm.to_csv(
                os.path.join(args.subjects_root_path, subject_dir, 'adm_episode{}_timeseries.csv'.format(i+1)),
                index_label='Hours')