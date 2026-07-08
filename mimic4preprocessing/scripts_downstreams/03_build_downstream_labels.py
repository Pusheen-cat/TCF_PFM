import pandas as pd
import numpy as np
import os
from datetime import timedelta
from pathlib import Path
import pickle
import yaml
from multiprocessing import Pool
from functools import partial
from tqdm import tqdm  # 진행상황 확인용

# --- 기존 설정 값 및 process_one_patient 함수 유지 ---
min_admission_duration_hr = 6
min_admission_events = 20
ihm_label_hr = 48


# (process_one_patient 함수는 기존 코드와 동일하므로 생략하지 않고 그대로 두거나,
#  위의 코드 블록에 있는 내용을 그대로 사용하시면 됩니다.
#  여기서는 실행을 위해 선언이 필요합니다.)

def process_one_patient(stay_path, load_path, save_path, subject_id, df_arrest_subject, phenotypings, vasos, df_huo):
    # ... (기존 process_one_patient 로직 그대로 사용) ...
    # 경로 설정
    patient_dir = os.path.join(load_path, subject_id[:3])
    save_dir = os.path.join(save_path, subject_id[:3], subject_id)
    os.makedirs(save_dir, exist_ok=True)

    # 1. 데이터 로드 및 전처리
    patient_df = pd.read_csv(os.path.join(patient_dir, f'{subject_id}.csv'))
    patient_stay = pd.read_csv(os.path.join(stay_path, subject_id, 'stays.csv'))

    # charttime을 datetime으로 변환
    patient_df['charttime'] = patient_df['charttime'].astype(str)
    mask = patient_df['charttime'].str.match(r'^\d{4}-\d{2}-\d{2}$')
    patient_df.loc[mask, 'charttime'] += ' 00:00:00'
    patient_df['charttime'] = pd.to_datetime(patient_df['charttime'])
    patient_df["hadm_id"] = patient_df["hadm_id"].astype("Int64")

    # --- 검증 단계 ---

    # 1. hadm_id consistency 확인
    # patient_df에서 NaN이 아닌 hadm_id만 추출하여 정렬된 set 비교
    df_hadms = set(patient_df['hadm_id'].dropna().unique())
    stay_hadms = set(patient_stay['hadm_id'].unique())

    # assert df_hadms == stay_hadms, f"Mismatch in hadm_ids for {subject_id}"

    # 2. 각 hadm_id별 시간 정보 추출 및 검증
    # hadm_id를 key로 하고 info dict를 value로 갖는 딕셔너리 생성
    hadm_info = {}

    for hid in df_hadms:
        current_rows = patient_df[patient_df['hadm_id'] == hid]

        # min_time, max_time
        min_time = current_rows['charttime'].min()
        max_time = current_rows['charttime'].max()

        # adm_time
        adm_row = current_rows[(current_rows['itemid'] == 1000000) & (current_rows['value'] == 'admission')]
        assert len(adm_row) == 1, f"hadm_id {hid} has {len(adm_row)} admission rows (expected 1)"
        if len(adm_row) != 1: continue  # 예외 처리
        adm_time = adm_row.iloc[0]['charttime']

        # disch_time
        disch_row = current_rows[(current_rows['itemid'] == 1000000) & (current_rows['value'] == 'discharge')]
        assert len(disch_row) == 1, f"hadm_id {hid} has {len(disch_row)} discharge rows (expected 1)"
        if len(disch_row) != 1: continue  # 예외 처리
        disch_time = disch_row.iloc[0]['charttime']

        hadm_info[hid] = {
            'min_time': min_time,
            'max_time': min(max_time, disch_time + pd.Timedelta(hours=1)),
            # ! TODO ## Max time error 가 존재해서 disch_time으로 변경
            'adm_time': adm_time,
            'disch_time': disch_time
        }

    # hadm_info에 없는 hid가 patient_stay에 있을 수 있으므로 체크
    valid_hids = [h for h in patient_stay['hadm_id'].values if h in hadm_info]

    # --- 처리 및 저장 단계 ---

    # patient_stay 순서대로 처리
    for idx, hid in enumerate(valid_hids):
        info = hadm_info[hid]

        # Duration check
        duration_hr = (info['disch_time'] - info['adm_time']).total_seconds() / 3600
        if duration_hr <= min_admission_duration_hr:
            continue

        # Event num check
        # 기준: adm_time-1sec ~ disch_time+1sec, itemid < 1,000,000
        check_start = info['adm_time'] - timedelta(seconds=1)
        check_end = info['disch_time'] + timedelta(seconds=1)

        # 해당 시간 범위 내에 있고, itemid가 1,000,000 미만인(Clinical feature) row들만 필터링
        valid_events_mask = (patient_df['charttime'] >= check_start) & \
                            (patient_df['charttime'] <= check_end) & \
                            (patient_df['itemid'] < 1000000)

        # 개수가 min_admission_events 이하라면 건너뛰기
        if len(patient_df[valid_events_mask]) <= min_admission_events:
            continue

        # --- one_hadm_id DataFrame 생성 ---
        # 1. Static rows (처음 3줄)
        static_rows = patient_df.iloc[:3]
        # itemid 확인
        # assert set(static_rows['itemid'].values).issubset({1100000, 1100001, 1100002}), "Static row itemids mismatch"

        # 2. Dynamic rows (min_time-1s ~ max_time+1s)
        mask = (patient_df['charttime'] >= (info['min_time'] - timedelta(seconds=1))) & \
               (patient_df['charttime'] <= (info['max_time'] + timedelta(seconds=1)))
        dynamic_rows = patient_df[mask]

        # 순서 유지하며 결합 (static은 인덱스가 앞서있으므로 concat 후 sort_index 혹은 단순 concat)
        one_hadm_id = pd.concat([static_rows, dynamic_rows]).sort_index()

        # 중복 제거 (만약 static row가 dynamic range에 걸렸을 경우 대비)
        one_hadm_id = one_hadm_id[~one_hadm_id.index.duplicated(keep='first')]

        # 저장
        one_hadm_id.to_csv(os.path.join(save_dir, f'adm{idx}.csv'), index=False)

        # --- Helper Data for Labels ---
        admission_row = one_hadm_id[(one_hadm_id['itemid'] == 1000000) & (one_hadm_id['value'] == 'admission')].iloc[0]
        base_subject_id = admission_row['subject_id']  # should match subject_id
        base_hadm_id = admission_row['hadm_id']
        stay_name = f'adm{idx}'

        # ICU Intervals 구하기 (stay_id 매핑용)
        # itemid 1000000 인 row들 추출
        events_df = one_hadm_id[one_hadm_id['itemid'] == 1000000].sort_values('charttime')
        icu_intervals = []  # (start, end, stay_id)

        temp_in = None
        n_rows = len(events_df)
        for i, (_, r) in enumerate(events_df.iterrows()):
            is_last = (i == n_rows - 1)
            if r['value'] == 'icu-in':
                temp_in = r
            elif (r['value'] == 'icu_out' or is_last) and temp_in is not None:
                # icu_in 과 icu_out 사이
                icu_intervals.append((temp_in['charttime'], r['charttime'], temp_in['stay_id']))
                temp_in = None

        def get_stay_id(query_time, intervals):
            for start, end, s_id in intervals:
                if start <= query_time <= end:
                    return s_id
            return np.nan  # 빈칸

        # Death Event 확인
        death_rows = one_hadm_id[(one_hadm_id['itemid'] == 1200000) & (one_hadm_id['value'] == 'Death-event')]
        has_death = len(death_rows) > 0
        # if has_death: print('death',subject_id)
        death_time = death_rows.iloc[0]['charttime'] if has_death else None

        # ==========================================
        # Label 1: In-Hospital Mortality (IHM)
        # ==========================================
        ihm_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr', 'ihm']

        if (info['disch_time'] - info['adm_time']) <= timedelta(hours=ihm_label_hr):
            # 48시간 이하: 빈 DataFrame 저장
            pd.DataFrame(columns=ihm_cols).to_csv(os.path.join(save_dir, f'label_ihm_adm{idx}.csv'), index=False)
        else:
            # 48시간 초과
            target_time = info['adm_time'] + timedelta(hours=ihm_label_hr)
            curr_stay_id = get_stay_id(target_time, icu_intervals)

            ihm_val = 1 if has_death else 0

            ihm_data = {
                'subject_id': [base_subject_id],
                'hadm_id': [base_hadm_id],
                'stay_id': [curr_stay_id],
                'charttime': [target_time],
                'stay': [stay_name],
                'hosp_hr': [(target_time - info['min_time']).total_seconds() / 3600],
                'adm_hr': [float(ihm_label_hr)],
                'ihm': [ihm_val]
            }
            pd.DataFrame(ihm_data).to_csv(os.path.join(save_dir, f'label_ihm_adm{idx}.csv'), index=False)

        # ==========================================
        # Label 2: Decompensation-Death
        # ==========================================
        decomp_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr',
                       'decompensation_death']

        # adm_time + 4hr 부터 disch_time 사이의 정각 시간들
        start_hr = info['adm_time'] + timedelta(hours=4)
        # 정각으로 올림 (Ceil to hour)
        if start_hr.minute != 0 or start_hr.second != 0 or start_hr.microsecond != 0:
            start_hr = start_hr.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        # 범위 생성
        if start_hr > info['disch_time']:
            time_range = []
        else:
            time_range = pd.date_range(start=start_hr, end=info['disch_time'], freq='h')

        decomp_rows = []
        for t in time_range:
            label = 0
            if has_death:
                if (death_time - timedelta(hours=24)) <= t < death_time:
                    label = 1

            decomp_rows.append({
                'subject_id': base_subject_id,
                'hadm_id': base_hadm_id,
                'stay_id': get_stay_id(t, icu_intervals),
                'charttime': t,
                'stay': stay_name,
                'hosp_hr': (t - info['min_time']).total_seconds() / 3600,
                'adm_hr': (t - info['adm_time']).total_seconds() / 3600,
                'decompensation_death': label
            })

        pd.DataFrame(decomp_rows, columns=decomp_cols).to_csv(
            os.path.join(save_dir, f'label_decompensation_death_adm{idx}.csv'), index=False)

        # ==========================================
        # Label 3: Decompensation-Arrest
        # ==========================================
        decomp_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr',
                       'decompensation_arrest']

        # adm_time + 4hr 부터 disch_time 사이의 정각 시간들 (위에서 이미 구한 time_range 활용 가능하나 안전하게 다시 명시)
        # start_hr 로직 동일

        decomp_rows = []
        arrest_charttimes = df_arrest_subject.loc[df_arrest_subject['hadm_id'] == hid, 'charttime']

        for t in time_range:
            label = 0
            if has_death:
                if (death_time - timedelta(hours=24)) <= t < death_time:
                    label = 1
            if not arrest_charttimes.empty:
                for ct in arrest_charttimes:
                    if (ct - timedelta(hours=24)) <= t < ct:
                        label = 1

            decomp_rows.append({
                'subject_id': base_subject_id,
                'hadm_id': base_hadm_id,
                'stay_id': get_stay_id(t, icu_intervals),
                'charttime': t,
                'stay': stay_name,
                'hosp_hr': (t - info['min_time']).total_seconds() / 3600,
                'adm_hr': (t - info['adm_time']).total_seconds() / 3600,
                'decompensation_arrest': label
            })

        pd.DataFrame(decomp_rows, columns=decomp_cols).to_csv(
            os.path.join(save_dir, f'label_decompensation_arrest_adm{idx}.csv'), index=False)

        # ==========================================
        # Label 4: ICU-In
        # ==========================================
        icu_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr', 'icu_in']

        # icu_in 이벤트 시간들 수집
        icu_in_events = events_df[events_df['value'] == 'icu-in']['charttime'].tolist()

        icu_rows = []
        for t in time_range:
            curr_s_id = get_stay_id(t, icu_intervals)

            # ICU에 있는 경우(stay_id가 존재)는 제외
            if pd.notna(curr_s_id):
                continue

            # Label logic: [-24hr, 0) relative to icu_in event
            label = 0
            for event_t in icu_in_events:
                if (event_t - timedelta(hours=24)) <= t < event_t:
                    label = 1
                    break  # 하나라도 걸리면 1

            icu_rows.append({
                'subject_id': base_subject_id,
                'hadm_id': base_hadm_id,
                'stay_id': np.nan,  # 제외되었으므로 항상 빈칸이어야 함 (로직상)
                'charttime': t,
                'stay': stay_name,
                'hosp_hr': (t - info['min_time']).total_seconds() / 3600,
                'adm_hr': (t - info['adm_time']).total_seconds() / 3600,
                'icu_in': label
            })

        pd.DataFrame(icu_rows, columns=icu_cols).to_csv(os.path.join(save_dir, f'label_icu_in_adm{idx}.csv'),
                                                        index=False)

        # ==========================================
        # Label 5: Prognosis
        # ==========================================
        prog_days = [30, 90, 365]
        prog_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr'] + \
                    [f'readmission_{d}day' for d in prog_days] + \
                    [f'ohm_{d}day' for d in prog_days]

        if has_death:
            # 병원 내 사망(IHM=1)인 경우 row 없이 column만 저장
            pd.DataFrame(columns=prog_cols).to_csv(os.path.join(save_dir, f'label_prognosis_adm{idx}.csv'), index=False)
        else:
            prog_row = {
                'subject_id': base_subject_id,
                'hadm_id': base_hadm_id,
                'stay_id': np.nan,
                'charttime': info['disch_time'],
                'stay': stay_name,
                'hosp_hr': (info['disch_time'] - info['min_time']).total_seconds() / 3600,
                'adm_hr': (info['disch_time'] - info['adm_time']).total_seconds() / 3600,
            }

            max_t = info['disch_time']
            for day in prog_days:
                end_scan_time = max_t + timedelta(days=day)
                scan_mask = (patient_df['charttime'] > (max_t + timedelta(seconds=1))) & \
                            (patient_df['charttime'] <= end_scan_time)
                future_df = patient_df[scan_mask]

                # Readmission check
                has_readm = ((future_df['itemid'] == 1000000) & (future_df['value'] == 'admission')).any()
                prog_row[f'readmission_{day}day'] = 1 if has_readm else 0

                # OHM check (Out of Hospital Mortality)
                has_ohm = ((future_df['itemid'] == 1200000) & (future_df['value'] == 'Death-event')).any()
                prog_row[f'ohm_{day}day'] = 1 if has_ohm else 0

            pd.DataFrame([prog_row], columns=prog_cols).to_csv(os.path.join(save_dir, f'label_prognosis_adm{idx}.csv'),
                                                               index=False)

        # ==========================================
        # Label 6: LOS (Length of Stay)
        # ==========================================
        los_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr', 'adm_los', 'icu_los']

        los_rows = []
        for t in time_range:
            curr_stay_id = np.nan
            curr_icu_in = None
            curr_icu_out = None

            for start, end, s_id in icu_intervals:
                if start <= t <= end:
                    curr_stay_id = s_id
                    curr_icu_in = start
                    curr_icu_out = end
                    break

            adm_los = (info['disch_time'] - t).total_seconds() / 3600

            icu_los = -100
            if pd.notna(curr_stay_id) and curr_icu_in is not None:
                if t >= (curr_icu_in + timedelta(hours=4)):
                    icu_los = (curr_icu_out - t).total_seconds() / 3600

            los_rows.append({
                'subject_id': base_subject_id,
                'hadm_id': base_hadm_id,
                'stay_id': curr_stay_id,
                'charttime': t,
                'stay': stay_name,
                'hosp_hr': (t - info['min_time']).total_seconds() / 3600,
                'adm_hr': (t - info['adm_time']).total_seconds() / 3600,
                'adm_los': adm_los,
                'icu_los': icu_los
            })
        pd.DataFrame(los_rows, columns=los_cols).to_csv(os.path.join(save_dir, f'label_los_adm{idx}.csv'), index=False)

        # ==========================================
        # Label 7: Phenotyping
        # ==========================================
        (code_to_group, id_to_group, group_to_id, codes_in_benchmark, definitions) = phenotypings
        phenotype_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr'] + codes_in_benchmark
        patient_diagnosis = pd.read_csv(os.path.join(stay_path, subject_id, 'diagnoses.csv'), dtype={'ICD9_CODE': str})
        hadm_diagnosis = patient_diagnosis[patient_diagnosis['hadm_id'] == hid].copy()

        cur_labels = [0 for i in range(len(id_to_group))]

        hadm_diagnosis['USE_IN_BENCHMARK'] = (
            hadm_diagnosis['USE_IN_BENCHMARK']
            .fillna(False)
            .astype(bool)
        )

        for index, row in hadm_diagnosis.iterrows():
            if row['USE_IN_BENCHMARK']:
                code = row['ICD9_CODE']
                group = code_to_group[code]
                group_id = group_to_id[group]
                cur_labels[group_id] = 1

        cur_labels = [x for (i, x) in enumerate(cur_labels) if definitions[id_to_group[i]]['use_in_benchmark']]

        phenotype_row = {
            'subject_id': base_subject_id,
            'hadm_id': base_hadm_id,
            'stay_id': np.nan,
            'charttime': info['disch_time'],
            'stay': stay_name,
            'hosp_hr': (info['disch_time'] - info['min_time']).total_seconds() / 3600,
            'adm_hr': (info['disch_time'] - info['adm_time']).total_seconds() / 3600,
        }
        phenotype_row.update(dict(zip(codes_in_benchmark, cur_labels)))
        pd.DataFrame([phenotype_row], columns=phenotype_cols).to_csv(os.path.join(save_dir, f'label_phenotype_adm{idx}.csv'), index=False)

        # ==========================================
        # Label 8: Vasopressor
        # ==========================================
        vaso_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr', 'vaso']
        (vaso_exist, vaso_df) = vasos

        start_hr_vaso = info['adm_time'].ceil('h')
        if start_hr_vaso < info['adm_time']: start_hr_vaso += timedelta(hours=1)

        if start_hr_vaso > info['disch_time']:
            time_range_vaso = []
        else:
            time_range_vaso = pd.date_range(start=start_hr_vaso, end=info['disch_time'], freq='h')

        vaso_rows_list = []

        exist_rows = vaso_exist[(vaso_exist['hadm_id'] == base_hadm_id)]
        if len(exist_rows)>0:
            # print(type(base_subject_id)) # <class 'numpy.int64'>
            # print(type(base_hadm_id)) # <class 'numpy.int64'>
            curr_vaso_df = vaso_df[(vaso_df['subject_id'] == base_subject_id) & (vaso_df['hadm_id'] == base_hadm_id)]

            for t in time_range_vaso:
                curr_stay_id = get_stay_id(t, icu_intervals)
                if pd.isna(curr_stay_id): continue

                # print(type(curr_stay_id)) #<class 'float'>

                exists_in_master = (exist_rows['stay_id'] == curr_stay_id).any()
                if not exists_in_master: continue

                stay_vaso_records = curr_vaso_df[curr_vaso_df['stay_id'] == curr_stay_id]

                label = 0
                if not stay_vaso_records.empty:
                    for _, v_row in stay_vaso_records.iterrows():
                        v_start = v_row['starttime'] - timedelta(minutes=30)
                        v_end = v_row['endtime'] + timedelta(minutes=30)
                        if v_start <= t <= v_end:
                            label = 1
                            break
                vaso_rows_list.append({
                    'subject_id': base_subject_id,
                    'hadm_id': base_hadm_id,
                    'stay_id': curr_stay_id,
                    'charttime': t,
                    'stay': stay_name,
                    'hosp_hr': (t - info['min_time']).total_seconds() / 3600,
                    'adm_hr': (t - info['adm_time']).total_seconds() / 3600,
                    'vaso': label
                })
        pd.DataFrame(vaso_rows_list, columns=vaso_cols).to_csv(os.path.join(save_dir, f'label_vaso_adm{idx}.csv'), index=False)

        # ==========================================
        # Label 9: HUO
        # ==========================================
        huo_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr', 'oliguria', 'anuria']

        weight = None
        weight_items = [224639, 226512, 226531]
        w_rows = one_hadm_id[one_hadm_id['itemid'].isin(weight_items)]
        if not w_rows.empty:
            target_row = w_rows.iloc[0]
            val = float(target_row['value'])
            if target_row['itemid'] == 226531: val *= 0.4536
            weight = val
            if (weight > 300) or (weight <15):
                weight = None

        if weight is None:
            w_rows_all = patient_df[patient_df['itemid'].isin(weight_items)]
            if not w_rows_all.empty:
                target_row = w_rows_all.iloc[0]
                val = float(target_row['value'])
                if target_row['itemid'] == 226531: val *= 0.4536
                weight = val
                if (weight > 300) or (weight < 15):
                    weight = None

        if weight is None:
            pd.DataFrame(columns=huo_cols).to_csv(os.path.join(save_dir, f'label_huo_adm{idx}.csv'), index=False)
        else:
            curr_huo = df_huo[(df_huo['subject_id'] == base_subject_id) & (df_huo['hadm_id'] == base_hadm_id)]
            huo_rows_list = []
            for _, h_row in curr_huo.iterrows():
                t = h_row['charttime']
                if not (info['min_time'] <= t <= info['disch_time']): continue
                curr_stay_id = get_stay_id(t, icu_intervals)
                uo_val = h_row['AVG_HOURLY_URINE_OUTPUT']
                normalized_uo = uo_val / weight
                oliguria = 1 if normalized_uo < 0.5 else 0
                anuria = 1 if normalized_uo < 0.3 else 0

                huo_rows_list.append({
                    'subject_id': base_subject_id,
                    'hadm_id': base_hadm_id,
                    'stay_id': curr_stay_id,
                    'charttime': t,
                    'stay': stay_name,
                    'hosp_hr': (t - info['min_time']).total_seconds() / 3600,
                    'adm_hr': (t - info['adm_time']).total_seconds() / 3600,
                    'oliguria': oliguria,
                    'anuria': anuria
                })
            pd.DataFrame(huo_rows_list, columns=huo_cols).to_csv(os.path.join(save_dir, f'label_huo_adm{idx}.csv'),
                                                                 index=False)


# ==========================================
# Worker Process Initializer & Wrapper
# ==========================================
def init_worker(arrest_dict, phenotypings, vaso_dict, huo_dict):
    """
    각 워커 프로세스가 시작될 때 한 번만 실행되어
    공유 데이터를 전역 변수(Global)로 메모리에 로드합니다.
    이 방식은 매 Task마다 데이터를 Pickling해서 보내는 오버헤드를 제거합니다.
    """
    global G_ARREST_DICT, G_PHENOTYPINGS, G_VASO_DICT, G_HUO_DICT
    G_ARREST_DICT = arrest_dict
    G_PHENOTYPINGS = phenotypings
    G_VASO_DICT = vaso_dict
    G_HUO_DICT = huo_dict


def process_one_patient_wrapper_global(subject_id, pretraining_path, stay_path, save_path):
    # --- 핵심 변경점: 타입 분리 ---
    # 파일 경로 탐색용 (String)
    subj_str = str(subject_id)
    # 딕셔너리 검색용 (Integer)
    subj_int = int(subject_id)

    try:
        # 1. Arrest (정수형 Key 사용)
        df_arrest_subject = G_ARREST_DICT.get(subj_int)
        if df_arrest_subject is None:
            df_arrest_subject = pd.DataFrame(columns=['subject_id', 'hadm_id', 'charttime'])

        # 2. Vaso (정수형 Key 사용)
        vaso_data = G_VASO_DICT.get(subj_int)
        if vaso_data is None:
            vaso_exist_subject = pd.DataFrame(columns=['subject_id', 'hadm_id', 'stay_id'])
            vaso_df_subject = pd.DataFrame(columns=['subject_id', 'hadm_id', 'stay_id', 'starttime', 'endtime'])
        else:
            vaso_exist_subject, vaso_df_subject = vaso_data

        # 3. HUO (정수형 Key 사용)
        df_huo_subject = G_HUO_DICT.get(subj_int)
        if df_huo_subject is None:
            df_huo_subject = pd.DataFrame(columns=['subject_id', 'hadm_id', 'charttime', 'AVG_HOURLY_URINE_OUTPUT'])

        # 함수 호출 시에는 파일 경로용(String) 변수를 넘겨줍니다.
        process_one_patient(
            load_path=pretraining_path,
            stay_path=stay_path,
            save_path=save_path,
            subject_id=subj_str,  # <-- String 타입 전달 (슬라이싱 에러 방지)
            df_arrest_subject=df_arrest_subject,
            phenotypings=G_PHENOTYPINGS,
            vasos=(vaso_exist_subject, vaso_df_subject),
            df_huo=df_huo_subject
        )
    except Exception as e:
        print(f"Error processing {subj_str}: {e}")


# ==========================================
# Main Split Function
# ==========================================
def split_by_admission_optimized(pretraining_path, stay_path, save_path, arrest_path,
                                 phenotype_yaml_path, icu_path, tr_te):
    path = Path(pretraining_path)
    names = [
        csv_file.stem
        for subdir in path.iterdir()
        if subdir.is_dir()
        for csv_file in subdir.glob("*.csv")
    ]

    print(f"Loading shared data for {tr_te}...")

    # [Helper] 확실하게 subject_id를 컬럼으로 만드는 함수
    def prepare_df_for_grouping(df, required_cols=None):
        # 1. 인덱스에 subject_id가 있으면 끄집어냄
        if 'subject_id' not in df.columns:
            df = df.reset_index()

        # 2. 그래도 없으면 에러 (데이터 무결성 체크)
        if 'subject_id' not in df.columns:
            # 혹시 index 이름이 설정 안되어있을 경우 대비
            if df.index.name == 'subject_id':
                df = df.reset_index()
            else:
                # 최후의 수단: 첫번째 컬럼을 subject_id로 가정하거나 경고
                pass

                # 3. 필요한 컬럼만 필터링 (메모리 절약)
        if required_cols:
            # required_cols가 실제 있는지 확인 후 intersection만 가져오기
            existing_cols = [c for c in required_cols if c in df.columns]
            df = df[existing_cols]

        return df

    # 1. Arrest Data
    with open(arrest_path, "rb") as f:
        df_arrest = pickle.load(f)

    # [Fix] 전처리 및 Grouping 옵션 변경
    df_arrest = prepare_df_for_grouping(df_arrest)
    df_arrest['charttime'] = pd.to_datetime(df_arrest['charttime'])
    # as_index=False를 해야 그룹핑된 DF 안에 subject_id가 컬럼으로 남음
    arrest_dict = dict(list(df_arrest.groupby('subject_id', as_index=False)))

    # 2. Phenotyping (데이터프레임 아님, 기존 유지)
    with open(phenotype_yaml_path) as definitions_file:
        definitions = yaml.safe_load(definitions_file)
    code_to_group = {}
    for group in definitions:
        codes = definitions[group]['codes']
        for code in codes:
            code_to_group[code] = group
    id_to_group = sorted(definitions.keys())
    group_to_id = dict((x, i) for (i, x) in enumerate(id_to_group))
    codes_in_benchmark = [x for x in id_to_group if definitions[x]['use_in_benchmark']]
    phenotypings = (code_to_group, id_to_group, group_to_id, codes_in_benchmark, definitions)

    # 3. Vasopressor
    with open(icu_path + f'inputevents_{tr_te}_existence.pkl', "rb") as f:
        vaso_exist = pickle.load(f)
    with open(icu_path + f'inputevents_{tr_te}_vaso.pkl', "rb") as f:
        vaso_df = pickle.load(f)

    # [Fix] 컬럼 보장
    vaso_exist = prepare_df_for_grouping(vaso_exist)
    vaso_df = prepare_df_for_grouping(vaso_df,
                                      required_cols=['subject_id', 'hadm_id', 'stay_id', 'starttime', 'endtime'])

    vaso_df['starttime'] = pd.to_datetime(vaso_df['starttime'])
    vaso_df['endtime'] = pd.to_datetime(vaso_df['endtime'])

    print("Grouping Vaso data...")
    # [Fix] as_index=False 추가
    vaso_exist_grouped = dict(list(vaso_exist.groupby('subject_id', as_index=False)))
    vaso_df_grouped = dict(list(vaso_df.groupby('subject_id', as_index=False)))

    vaso_dict = {}
    # 빈 DataFrame 생성 시 사용할 컬럼 정의 (subject_id 포함 필수)
    empty_vaso_cols = ['subject_id', 'hadm_id', 'stay_id', 'starttime', 'endtime']
    empty_exist_cols = ['subject_id', 'hadm_id', 'stay_id']  # exist의 구조에 맞게 조정 필요

    # vaso_exist에 있는 subject 기준으로 루프 (포함관계 고려)
    for subj, v_ex in vaso_exist_grouped.items():
        v_df = vaso_df_grouped.get(subj)

        # [Fix] 데이터가 없는 경우 컬럼을 갖춘 빈 DF 생성
        if v_df is None:
            v_df = pd.DataFrame(columns=empty_vaso_cols)

        vaso_dict[subj] = (v_ex, v_df)

    # 4. HUO
    with open(icu_path + f'outputevents_huo.pkl', "rb") as f:
        df_huo = pickle.load(f)

    # [Fix] 컬럼 보장 및 Grouping
    df_huo = prepare_df_for_grouping(df_huo)
    print("Grouping HUO data...")
    huo_dict = dict(list(df_huo.groupby('subject_id', as_index=False)))

    print(f"Starting parallel processing for {len(names)} subjects...")

    pool_func = partial(
        process_one_patient_wrapper_global,
        pretraining_path=pretraining_path,
        stay_path=stay_path,
        save_path=save_path
    )

    num_processes = min(16, os.cpu_count())

    with Pool(processes=num_processes,
              initializer=init_worker,
              initargs=(arrest_dict, phenotypings, vaso_dict, huo_dict)) as pool:
        list(tqdm(pool.imap(pool_func, names, chunksize=10), total=len(names)))


if __name__ == '__main__':
    # Edit or set these env vars (see README).
    MIMIC4_ROOT = os.environ.get("MIMIC4_ROOT", "/path/to/mimiciv/3.1")
    DATA_ROOT = os.environ.get("PFM_DATA_ROOT", "/path/to/PFM_data")
    _RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources")
    stay_path = os.path.join(DATA_ROOT, 'B_train_test_split')
    pretraining_path = os.path.join(DATA_ROOT, 'PFM_pretraining')
    save_path = os.path.join(DATA_ROOT, 'PFM_downstream')
    arrest_path = os.path.join(MIMIC4_ROOT, 'icu', 'chartevents_arrest.pkl')
    phenotype_yaml_path = os.path.join(_RESOURCES, 'hcup_ccs_2015_definitions.yaml')
    icu_path = os.path.join(MIMIC4_ROOT, 'icu') + os.sep

    for tmp in ['NOadd', 'addQ', ]:
        for tr_te in ['test', 'train']:
            print(f"Processing {tmp} / {tr_te}")
            split_by_admission_optimized(
                pretraining_path + f'/{tmp}/{tr_te}',
                stay_path + f'/{tr_te}',
                save_path + f'/{tmp}/{tr_te}',
                arrest_path,
                phenotype_yaml_path,
                icu_path,
                tr_te
            )

"""
Error processing 18954717: float division by zero
"""