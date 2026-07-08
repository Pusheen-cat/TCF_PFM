"""
Step 01 - Extract per-subject tables from the raw MIMIC-IV CSVs.

Prerequisite: run `python mimic4preprocessing/omr_labevent_fix.py` first to build
hosp/omr_v1.csv, which the default --event_tables reads. To include both OMR passes,
run this script twice: first with the default tables (which include hosp/omr_v1),
then again with `-e hosp/omr` (per-subject events.csv is appended, not overwritten).

Usage (from the repo root):
    python mimic4preprocessing/scripts/01_extract_subjects.py <mimic4_root> <out_dir>

See the README "Preprocessing" section for the full, ordered pipeline.
"""
import argparse
import copy
import yaml

# Allow running this file directly (python <path>): put the repo root on sys.path.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mimic4preprocessing.mimic4csv import *
from mimic4preprocessing.preproc_fix import *
from mimic4preprocessing.preprocessing import add_hcup_ccs_2015_groups, make_phenotype_label_matrix, make_phenotype_label_matrix_v2
from mimic4preprocessing.util import dataframe_from_csv

parser = argparse.ArgumentParser(description='Extract per-subject data from MIMIC-IV CSV files.')
parser.add_argument('mimic4_path', type=str, help='Directory containing MIMIC-IV CSV files.')
parser.add_argument('output_path', type=str, help='Directory where per-subject data should be written.')
parser.add_argument('--event_tables', '-e', type=str, nargs='+', help='Tables from which to read events.',
                    default=['hosp/omr_v1', 'icu/chartevents', 'hosp/labevents', 'icu/outputevents'])
parser.add_argument('--phenotype_definitions', '-p', type=str,
                    default=os.path.join(os.path.dirname(__file__), '../resources/hcup_ccs_2015_definitions.yaml'),
                    help='YAML file with phenotype definitions.')
parser.add_argument('--itemids_file', '-i', type=str, help='CSV containing list of ITEMIDs to keep.')
parser.add_argument('--verbose', '-v', dest='verbose', action='store_true', help='Verbosity in output')
parser.add_argument('--quiet', '-q', dest='verbose', action='store_false', help='Suspend printing of details')
parser.set_defaults(verbose=True)
parser.add_argument('--test', action='store_true', help='TEST MODE: process only 1000 subjects, 1000000 events.')
args, _ = parser.parse_known_args()

try:
    os.makedirs(args.output_path)
except:
    pass

patients = read_patients_table(args.mimic4_path) #pats[['subject_id', 'gender', 'anchor_age', 'anchor_year', 'dod' , 'dob']]
admits = read_admissions_table(args.mimic4_path) #'subject_id', 'hadm_id', 'admittime', 'dischtime', 'deathtime', 'admission_type', 'admission_location', 'discharge_location', 'language', 'marital_status', 'race', 'hospital_expire_flag'
stays = read_icustays_table(args.mimic4_path) # subject_id	hadm_id	stay_id	first_careunit == last_careunit	intime	outtime	los
transfers = read_transfers_table(args.mimic4_path) # ['subject_id', 'hadm_id', 'transfer_id', 'eventtype', 'careunit', 'intime', 'outtime']
labevents_partial = read_lab_table(args.mimic4_path)
chartevents_partial, chartevents_partial_stay = read_chart_table(args.mimic4_path)
if args.verbose:
    print('START:\n\tstay_ids: {}\n\thadm_ids: {}\n\tsubject_ids: {}'.format(stays.stay_id.unique().shape[0],
          stays.hadm_id.unique().shape[0], stays.subject_id.unique().shape[0]))

## This is added mimimc4 preproc
patients, admits = remove_dual_death_err(patients, admits)
patients, admits, stays = remove_dod_err(patients, admits, stays)
admits, stays = remove_adm_disch_err(admits, stays, transfers, labevents_partial, chartevents_partial)
admits = refine_death_label(admits)
patients, admits, stays = remove_after_death(patients, admits, stays, labevents_partial, chartevents_partial, chartevents_partial_stay)

if args.verbose:
    print('REFINE Death labels:\n\tstay_ids: {}\n\thadm_ids: {}\n\tsubject_ids: {}'.format(stays.stay_id.unique().shape[0],
          stays.hadm_id.unique().shape[0], stays.subject_id.unique().shape[0]))

stays = remove_icustays_with_transfers(stays)
if args.verbose:
    print('REMOVE ICU TRANSFERS:\n\tstay_ids: {}\n\thadm_ids: {}\n\tsubject_ids: {}'.format(stays.stay_id.unique().shape[0],
          stays.hadm_id.unique().shape[0], stays.subject_id.unique().shape[0]))

stays_copy = copy.deepcopy(stays)
stays = outer_merge_on_subject_admission(stays, admits)
stays = merge_on_subject(stays, patients)
# stays = filter_admissions_on_nb_icustays(stays) #TODO - We keep No ICU admission & Mulit-ICU admission per hospitalization
if args.verbose:
    print('REMOVE MULTIPLE STAYS PER ADMIT:\n\tstay_ids: {}\n\thadm_ids: {}\n\tsubject_ids: {}'.format(stays.stay_id.unique().shape[0],
          stays.hadm_id.unique().shape[0], stays.subject_id.unique().shape[0]))

#stays = add_age_to_icustays(stays)
stays = add_age_to_admin(stays)
#stays = add_inunit_mortality_to_icustays(stays)
stays = add_inunit_mortality_to_icustays_v2(stays)
#stays = add_inhospital_mortality_to_icustays(stays)
stays = add_inhospital_mortality_to_icustays_v2(stays)
stays = filter_icustays_on_age(stays)

if args.verbose:
    print('REMOVE PATIENTS AGE < 18:\n\tstay_ids: {}\n\thadm_ids: {}\n\tsubject_ids: {}'.format(stays.stay_id.unique().shape[0],
          stays.hadm_id.unique().shape[0], stays.subject_id.unique().shape[0]))

stays.to_csv(os.path.join(args.output_path, 'all_stays.csv'), index=False)
diagnoses = read_icd_diagnoses_table(args.mimic4_path)
diagnoses = filter_diagnoses_on_stays(diagnoses, stays)
diagnoses.to_csv(os.path.join(args.output_path, 'all_diagnoses.csv'), index=False)
#count_icd_codes(diagnoses, output_path=os.path.join(args.output_path, 'diagnoses_counts.csv'))
diagnoses = count_icd_codes_v2(diagnoses, output_path=os.path.join(args.output_path, 'diagnoses_counts.csv'))
phenotypes = add_hcup_ccs_2015_groups(diagnoses, yaml.safe_load(open(args.phenotype_definitions, 'r')))
make_phenotype_label_matrix_v2(phenotypes, stays).to_csv(os.path.join(args.output_path, 'phenotype_labels.csv'),
                                                      index=False, quoting=csv.QUOTE_NONNUMERIC)

if args.test:
    pat_idx = np.random.choice(patients.shape[0], size=1000)
    patients = patients.iloc[pat_idx]
    stays = stays.merge(patients[['subject_id']], left_on='subject_id', right_on='subject_id')
    args.event_tables = [args.event_tables[0]]
    print('Using only', stays.shape[0], 'stays and only', args.event_tables[0], 'table')

subjects = stays.subject_id.unique()
break_up_stays_by_subject(stays, args.output_path, subjects=subjects)
break_up_diagnoses_by_subject_v2(phenotypes, args.output_path, subjects=subjects)
items_to_keep = set(
    [int(itemid) for itemid in dataframe_from_csv(args.itemids_file)['itemid'].unique()]) if args.itemids_file else None
for idx, table in enumerate(args.event_tables):
    read_events_table_and_break_up_by_subject(args.mimic4_path, table, args.output_path, items_to_keep=items_to_keep,
                                              subjects_to_keep=subjects)
"""
This is added to address ER-Adm/Disch, Hospital Adm/Disch, ICU In/Out, Death, extra labels in my_itemid.py

Order - @5 ER_ADM - @4 ADM/ER_DISCH - @3 #Admission location# - @2 ICU_IN - @1 #ICU class# - 0 - @-2 #'Death-event'/'Censored-event'# - @-3 ICU_OUT - @-4 DISCH - @-5 #Discharge location# - 
"""
read_adm_stay_table_and_break_up_by_subject(stays_copy, args.output_path, type = 'stay', items_to_keep=items_to_keep,
                                              subjects_to_keep=subjects)
read_adm_stay_table_and_break_up_by_subject(admits, args.output_path, type = 'admit', items_to_keep=items_to_keep,
                                              subjects_to_keep=subjects)
read_adm_stay_table_and_break_up_by_subject(stays, args.output_path, type = 'for_dob', items_to_keep=items_to_keep,
                                              subjects_to_keep=subjects)

merged = add_dod_to_admits(patients, admits) #dod를 하루 다음날로 미룸 (왜냐면 00:00:00으로 normalize 되었으므로)
read_adm_stay_table_and_break_up_by_subject(merged, args.output_path, type = 'for_dod', items_to_keep=items_to_keep,
                                              subjects_to_keep=subjects)

