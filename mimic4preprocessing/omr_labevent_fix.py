import pandas as pd
from tqdm import tqdm
import os
# Allow running this file directly (python <path>): put the repo root on sys.path.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic4preprocessing.my_itemid import my_itemid
"""
220179	Non Invasive Blood Pressure systolic	NBPs	chartevents	Routine Vital Signs	mmHg	Numeric
220180	Non Invasive Blood Pressure diastolic	NBPd	chartevents	Routine Vital Signs	mmHg	Numeric
220181	Non Invasive Blood Pressure mean	NBPm	chartevents	Routine Vital Signs	mmHg	Numeric
224639	Daily Weight	Daily Weight	chartevents	General	kg	Numeric
226512	Admission Weight (Kg)	Admission Weight (Kg)	chartevents	General	kg	Numeric
226707	Height	Height	chartevents	General	Inch	Numeric


311,224639,311627,Daily Weight --- kg
699,226707,43616,Height --- inch
700,226730,43616,Height (cm)

"""

def split_blood_pressure_inplace(df):
    root = '/path/to/mimiciv/3.1/'
    df_admission = pd.read_csv(root + "hosp/admissions.csv")

    df_omr = df.copy()
    #df_omr = df_omr.reset_index(drop=False)
    df_omr['omr_idx'] = df_omr.index


    # [수정 2] Merge 키 타입 강제 통일
    df_omr['subject_id'] = df_omr['subject_id'].astype('int64')
    df_admission['subject_id'] = df_admission['subject_id'].astype('int64')

    # chartdate → charttime (그날 정오 or 09:00 등으로 가정)
    df_omr['charttime'] = pd.to_datetime(df_omr['chartdate']) + pd.Timedelta(hours=9)

    # 1) edregtime 먼저 datetime 변환 (실패하면 NaT)
    ed = pd.to_datetime(df_admission['edregtime'], errors='coerce')
    # 2) admittime을 fallback으로 datetime 변환
    adm = pd.to_datetime(df_admission['admittime'], errors='coerce')
    # 3) edregtime이 유효하면 사용, 아니면 admittime 사용
    df_admission['init_adm'] = ed.fillna(adm)

    df_admission['dischtime'] = pd.to_datetime(df_admission['dischtime'])

    merged = df_omr.merge(
        df_admission[['subject_id', 'hadm_id', 'init_adm', 'dischtime']],
        on='subject_id',
        how='left'
    )

    merged['in_interval'] = (
            (merged['charttime'] >= merged['init_adm']) &
            (merged['charttime'] <= merged['dischtime'])
    )

    # admission 중 하나라도 걸리면 inpatient
    inpatient_flag = merged.groupby('omr_idx')['in_interval'].any()

    df['is_inpatient'] = df_omr['omr_idx'].map(inpatient_flag).fillna(False).astype(bool)
    # -------------------------------
    # hadm_id 매핑 (inpatient만)
    # -------------------------------
    # in_interval == True 인 admission row만 선택
    matched = merged[merged['in_interval']]

    # 혹시 모를 중복 대비 (안전장치)
    matched = matched.sort_values(['omr_idx', 'init_adm'])

    # omr_idx → hadm_id 매핑
    hadm_map = matched.groupby('omr_idx')['hadm_id'].first()

    # df에 hadm_id 컬럼 추가
    df['hadm_id'] = (
        df_omr['omr_idx']
        .map(hadm_map)
        .fillna('')  # outpatient
    )

    # 1. 정렬
    df = df.sort_values(
        by=['subject_id', 'chartdate'],
        ascending=[True, True]
    ).reset_index(drop=True)


    rows = []

    prev_subject_id = None
    prev_chartdate = None

    for _, row in tqdm(
            df.iterrows(),
            total=len(df),
            desc="Splitting blood pressure"
    ):
        subject_id = row['subject_id']
        chartdate = row['chartdate']
        is_inpatient = row['is_inpatient']

        # 2. 새로운 chartdate 등장 시 outpatient_visit row 삽입
        if (
                (prev_subject_id != subject_id or
                (chartdate != prev_chartdate)) and not is_inpatient
        ):
            visit_row = row.copy()
            visit_row['seq_num'] = 1
            visit_row['result_name'] = 'outpatient_visit'
            visit_row['result_value'] = None
            rows.append(visit_row)

        prev_subject_id = subject_id
        prev_chartdate = chartdate

        # Blood Pressure가 아닌 경우 그대로 유지
        if row['result_name'] != 'Blood Pressure':
            try:
                new_row = row.copy()
                new_row['result_value'] = float(row['result_value'])
                rows.append(new_row)
            except (ValueError, TypeError):
                # float 변환 불가 → drop
                continue
            continue

        val = str(row['result_value'])

        # '/' 없는 Blood Pressure row는 drop
        if '/' not in val:
            continue

        try:
            sbp, dbp = val.split('/')
            sbp = int(sbp)
            dbp = int(dbp)
        except Exception:
            # parsing 실패 시 drop
            continue

        # SBP row
        sbp_row = row.copy()
        sbp_row['result_name'] = 'Non Invasive Blood Pressure systolic'
        sbp_row['result_value'] = sbp

        # DBP row
        dbp_row = row.copy()
        dbp_row['result_name'] = 'Non Invasive Blood Pressure diastolic'
        dbp_row['result_value'] = dbp

        # 같은 위치에 SBP → DBP 순서로 삽입
        rows.append(sbp_row)
        rows.append(dbp_row)


    return pd.DataFrame(rows).reset_index(drop=True)


def fix_omr(omr_df): #refine sub_df using times fo
    # =========================
    # 0. 전처리
    # =========================
    # seq_num >= 20 제거
    omr_df = omr_df[omr_df['seq_num'] < 6]

    # seq_num >= 2 이면서 Weight 계열 제거
    mask_weight = (
            (omr_df['seq_num'] >= 2) &
            (omr_df['result_name'].isin(['Weight (Lbs)', 'Weight']))
    )
    omr_df = omr_df[~mask_weight]

    # 특정 result_name 제거
    remove_names = [
        "Blood Pressure Standing (1 min)",
        "Blood Pressure Standing (3 mins)",
        "Blood Pressure Standing",
        "eGFR"
    ]

    omr_df = omr_df[~omr_df['result_name'].isin(remove_names)]

    # result_name 통일
    omr_df['result_name'] = omr_df['result_name'].replace({
        'Height (Inches)': 'Height',
        'Weight (Lbs)': 'Daily Weight',
        'Weight': 'Daily Weight',
        'Blood Pressure Sitting': 'Blood Pressure',
        'Blood Pressure Lying': 'Blood Pressure'
    })

    # SBP/DBP 분리
    omr_df = split_blood_pressure_inplace(omr_df)

    omr_df = omr_df.rename(columns={'result_value': 'value'})

    omr_df['stay_id'] = ''
    omr_df['charttime'] = (pd.to_datetime(omr_df['chartdate']) + pd.to_timedelta(8 + omr_df['seq_num'], unit='h')).dt.strftime('%Y-%m-%d %H:%M:%S')

    omr_df['valueuom'] = ''
    omr_df['itemid'] = ''

    # 1. Non Invasive Blood Pressure systolic
    mask = omr_df['result_name'] == 'Non Invasive Blood Pressure systolic'
    omr_df.loc[mask, 'itemid'] = 220179
    omr_df.loc[mask, 'valueuom'] = 'mmHg'

    # 2. Non Invasive Blood Pressure diastolic
    mask = omr_df['result_name'] == 'Non Invasive Blood Pressure diastolic'
    omr_df.loc[mask, 'itemid'] = 220180
    omr_df.loc[mask, 'valueuom'] = 'mmHg'

    # 3. Daily Weight (lbs -> kg)
    mask = omr_df['result_name'] == 'Daily Weight'
    omr_df.loc[mask, 'itemid'] = 224639
    omr_df.loc[mask, 'valueuom'] = 'kg'
    omr_df.loc[mask, 'value'] = omr_df.loc[mask, 'value'] * 0.453592

    # 4. Height
    mask = omr_df['result_name'] == 'Height'
    omr_df.loc[mask, 'itemid'] = 226707
    omr_df.loc[mask, 'valueuom'] = 'Inch'

    # 5. BMI (kg/m2)
    mask = omr_df['result_name'] == 'BMI (kg/m2)'
    omr_df.loc[mask, 'itemid'] = my_itemid['BMI (kg/m2)'][0]
    omr_df.loc[mask, 'valueuom'] = my_itemid['BMI (kg/m2)'][1]

    # 5-2. BMI
    mask = omr_df['result_name'] == 'BMI'
    omr_df.loc[mask, 'result_name'] = 'BMI (kg/m2)'
    omr_df.loc[mask, 'itemid'] = my_itemid['BMI (kg/m2)'][0]
    omr_df.loc[mask, 'valueuom'] = my_itemid['BMI (kg/m2)'][1]

    # 5. outpatient visit
    mask = omr_df['result_name'] == 'outpatient_visit'
    omr_df.loc[mask, 'itemid'] = my_itemid['Move']['itemid']
    omr_df.loc[mask, 'valueuom'] = my_itemid['Move']['unit']

    omr_df = omr_df.reset_index()

    return omr_df


if __name__ == '__main__':
    mimic4_path = os.environ.get("MIMIC4_ROOT", "/path/to/mimiciv/3.1")
    path = os.path.join(mimic4_path, 'hosp/omr.csv')
    df_omr = pd.read_csv(path)
    omr_df = fix_omr(df_omr)

    total_rows = len(omr_df)

    print('total_len omr: ', total_rows)

    omr_df.to_csv(
        mimic4_path + '/hosp/omr_v1.csv',
        index=False,
        chunksize=1_000_000  # 100만 row씩 write
    )