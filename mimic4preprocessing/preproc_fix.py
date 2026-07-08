import pandas as pd
import numpy as np

def remove_dual_death_err(patients, admissions):
    '''
    There is a err that two hospital_expire_flag and two deathtime for one subject_id
    We remove one of them (hadm_ids) that is not 'dod' value // Note; we preserve all subject_ids
    '''
    print(f'patients.csv: {len(patients)} / admissions.csv: {len(admissions)}')
    df = admissions.copy()  # admissions dataframe 가정
    # hospital_expire_flag == 1인 row count
    expire_counts = df.groupby('subject_id')['hospital_expire_flag'].apply(lambda x: (x == 1).sum())
    # deathtime notna count
    deathtime_counts = df.groupby('subject_id')['deathtime'].apply(lambda x: x.notna().sum())
    # 조건을 만족하는 subject_id
    problem_ids = expire_counts[expire_counts >= 2].index.union(
        deathtime_counts[deathtime_counts >= 2].index
    )
    problem_ids = problem_ids.tolist()

    print("조건을 만족하는 subject_id 수:", len(problem_ids))
    # 해당 subject_id들의 admission row 출력
    problem_rows = df[df['subject_id'].isin(problem_ids)].sort_values(['subject_id', 'hadm_id'])

    print(problem_rows) #19931581

    removed_hadm_ids = []  # 여기 리스트에 남기지 않을 hadm_id 누적
    for sid in problem_ids:
        print(sid)
        sub = df[df['subject_id'] == sid]
        dod_row = patients[patients['subject_id'] == sid]['dod'].iloc[0]

        # hospital_expire_flag == 1인 row만 대상으로
        expire_rows = sub[sub['hospital_expire_flag'] == 1].copy()

        # 만약 1개 이하면 그대로 저장
        if len(expire_rows) <= 1:
            continue

        # dod와 deathtime 간 시간 차이 계산
        expire_rows['time_diff'] = (expire_rows['dischtime'] - dod_row).abs()
        # 가장 가까운 row
        closest_row = expire_rows.loc[expire_rows['time_diff'].idxmin()]

        # 나머지 hadm_id 수집
        other_rows = expire_rows[expire_rows.index != closest_row.name]
        removed_hadm_ids.extend(other_rows['hadm_id'].tolist())

    admissions = admissions[~admissions['hadm_id'].isin(removed_hadm_ids)]
    print('removed hadm_id:', removed_hadm_ids)
    print(f'---> patients.csv: {len(patients)} / admissions.csv: {len(admissions)}')


    """1이 존재하는 subject_id의 이전 admission에 대해 discharge_location이 'DIED'인 row가 있다면 
    discharge_location을 'DIED'에서 'OTHER FACILITY'로 변경"""
    dead_subject_ids = admissions.loc[
        admissions['hospital_expire_flag'] == 1, 'subject_id'
    ].unique()
    mask = (
            admissions['subject_id'].isin(dead_subject_ids) &
            (admissions['hospital_expire_flag'] != 1) &
            (admissions['discharge_location'] == 'DIED')
    )
    admissions.loc[mask, 'discharge_location'] = 'OTHER FACILITY'

    return patients, admissions


def remove_dod_err(patients, admissions, icustays):
    '''
    There is dod err that dod is >1days before the latest discharge of patients
    We remove the subject_ids that "dod" is >1days before the last discharge (if not "hospital_expire_flag")
    '''
    subject_to_remove1 = [11612789, 13120175, 13260040, 13609967, 14208738, 15208667, 15423070, 15579099, 15663600,
                          15755711, 16020189, 16302059, 16970078, 17049270, 17628877, 19956999, 16970078]
    '''
    There is dod - discharge_location mismatch
    we ignore 12 patienst; "DIED" in discharge_location-admissions.csv but No "dod"-patients.csv
    '''
    subject_to_remove2 = [16716163, 10288867, 19780070, 14316710, 12087055, 15209552, 16588213, 12110838, 19853557,
                          17012058, 16024669, 14113726]
    # These subject_ids <- from 1_stats_train_test.ipynb
    '''
    There is other dod - discharge_location mismatch 
    we ignore 16 patienst; "DIED" in discharge_location-admissions.csv but mismatch "dod"-patients.csv time with "dischtime"
    '''
    subject_to_remove3 = [10541652, 11347146, 11587714, 11856771, 14080908, 14753682, 15293266, 15844941, 16121107,
                          16553329, 16780157, 17445690, 18825925, 19324257, 19449975, 19936109]
    '''
    하나의 subject ID에 대해 expire flag가 두개의 hadm_id에 대해 있는 오류 발생. 
    "dod"기준으로 subject 19931581의 hadm 29435910제거
    '''
    hadm_to_remove = [29435910]

    # Remove subject_ids from all 3 dataframes
    subjects_to_remove = list(set(subject_to_remove1 + subject_to_remove2 + subject_to_remove3))

    patients = patients[~patients['subject_id'].isin(subjects_to_remove)].copy()
    admissions = admissions[~admissions['subject_id'].isin(subjects_to_remove)].copy()
    icustays = icustays[~icustays['subject_id'].isin(subjects_to_remove)].copy()

    # Remove specific hadm_ids (only admissions, icustays)
    admissions = admissions[~admissions['hadm_id'].isin(hadm_to_remove)].copy()
    icustays = icustays[~icustays['hadm_id'].isin(hadm_to_remove)].copy()

    return patients, admissions, icustays


def remove_adm_disch_err(admissions, icustays, transfers, labevents_partial, chartevents_partial):
    original_admissions_columns = admissions.columns.tolist()
    """다음번의 hospitalization의 admittime을 next_admittime이라는 column으로 추가"""
    admissions = admissions.sort_values(['subject_id', 'admittime'])
    admissions['next_admittime'] = admissions.groupby('subject_id')['admittime'].shift(-1)

    print('Original admission length',len(admissions))
    """1. Admin이 Transfer의 시간보다 늦은 경우"""
    # ------------------------------------------------
    # 1. transfers 요약 (ED 제외)
    # ------------------------------------------------
    transfer_summary = (
        transfers
        .dropna(subset=['hadm_id'])
        .loc[transfers['careunit'] != 'Emergency Department']
        .groupby('hadm_id')
        .agg(
            transfer_intime_min=('intime', 'min'),
            transfer_outtime_max=('outtime', 'max')
        )
        .reset_index()
    )

    # ------------------------------------------------
    # 2. admissions에 merge
    # ------------------------------------------------
    admissions = admissions.merge(
        transfer_summary,
        on='hadm_id',
        how='left'
    )

    # ------------------------------------------------
    # 3. 컬럼 순서 정리 (dischtime 뒤에 추가)
    # ------------------------------------------------
    new_cols = ['transfer_intime_min', 'transfer_outtime_max']
    cols = list(admissions.columns)

    if 'dischtime' in cols:
        idx = cols.index('dischtime')
        new_order = (
                cols[:idx + 1] +
                new_cols +
                [c for c in cols if c not in new_cols and c not in cols[:idx + 1]]
        )
        admissions = admissions[new_order]

    # print(admissions[admissions['admittime'] > (admissions['edouttime'] + pd.Timedelta(hours=12))])  # 302
    # print(admissions[admissions['admittime'] > (admissions['transfer_intime_min'] + pd.Timedelta(hours=12))]) # 845
    # print(admissions[(admissions['edouttime'] -admissions['transfer_intime_min']).abs() > pd.Timedelta(hours=12)]) # 14580

    # 조건
    mask = admissions['edouttime'].notna() & (
            admissions['admittime'] > admissions['edouttime'] + pd.Timedelta(hours=12)
    )
    print(f"Rows to be fixed - admittime: {mask.sum()}")
    # 시간 차이
    time_diff = admissions.loc[mask, 'admittime'] - admissions.loc[mask, 'edouttime']
    # 몇 일을 당겨야 하는지 (floor)
    days_to_shift = (time_diff.dt.total_seconds() // (24 * 3600)).astype(int)
    # 최소 1일은 이동
    days_to_shift = days_to_shift.clip(lower=1)
    # admittime 보정
    admissions.loc[mask, 'admittime'] = (
            admissions.loc[mask, 'admittime'] -
            pd.to_timedelta(days_to_shift, unit='D')
    )

    # discharge event만 필터
    transfer_discharge = (
        transfers
        .loc[
            (transfers['eventtype'] == 'discharge') &
            (transfers['hadm_id'].notna())
            ]
        .groupby('hadm_id')['intime']
        .min()  # 혹시 여러 개면 가장 이른 discharge
    )

    # admissions에 컬럼 추가 (map 사용 → 컬럼 구조 안정)
    admissions['transfers_discharge'] = admissions['hadm_id'].map(transfer_discharge)

    # 조건:
    # 1) transfers_discharge 가 존재하고
    # 2) 두 값이 다를 때
    mask = (
            admissions['transfers_discharge'].notna() &
            (admissions['transfer_outtime_max'] != admissions['transfers_discharge'])
    )
    # replace
    admissions.loc[mask, 'transfer_outtime_max'] = admissions.loc[mask, 'transfers_discharge']

    """
    labevents_partial, chartevents_partial를 사용해서
    admissions에 hadm_id에 따라 'last_event' column을 생성"""
    # 1. 병합을 위해 필요한 컬럼만 추출하고 이름 변경 (충돌 방지)
    # 가정: 시간 컬럼명이 'charttime'이라고 가정 (이전 코드 문맥상)
    lab_times = labevents_partial[['hadm_id', 'charttime']].rename(columns={'charttime': 'lab_last_time'})
    chart_times = chartevents_partial[['hadm_id', 'charttime']].rename(columns={'charttime': 'chart_last_time'})

    # 2. admissions 기준으로 Left Join 수행
    # admissions의 hadm_id는 유니크하다고 했으므로 1:1 매핑됩니다.
    admissions = admissions.merge(lab_times, on='hadm_id', how='left')
    admissions = admissions.merge(chart_times, on='hadm_id', how='left')

    # 3. 두 시간 컬럼 중 더 늦은 시간(Max) 선택
    # axis=1: 행(row) 방향으로 비교
    # skipna=True가 기본값이므로, 둘 중 하나가 NaT(Time NaN)여도 존재하는 시간을 선택함
    admissions['last_event'] = admissions[['lab_last_time', 'chart_last_time']].max(axis=1)

    #print(admissions[admissions['dischtime'] < (admissions['last_event'] - pd.Timedelta(hours=1))]) #4032
    """
    1. dischtime 이 transfer_outtime_max보다 1시간 이상 이전
    2. lab_last_time, chart_last_time 둘중 하나라도 transfer_outtime_max보다 이전
    3. dischtime이 transfer_outtime_max보다 이전인 lab_last_time 및 chart_last_time보다 이전인 경우 (둘중 하나라도)"""
    cond0 = admissions['dischtime'] < (admissions['next_admittime'] - pd.Timedelta(hours=24.0))
    cond1 = admissions['dischtime'] < (admissions['transfer_outtime_max'] - pd.Timedelta(hours=0.0))
    cond1_d = admissions['deathtime'] < (admissions['transfer_outtime_max'] - pd.Timedelta(hours=0.0))
    is_lab_before_trans = admissions['lab_last_time'] < admissions['transfer_outtime_max']
    is_chart_before_trans = admissions['chart_last_time'] < admissions['transfer_outtime_max']
    cond2 = is_lab_before_trans | is_chart_before_trans
    # 3-1. 전원 전 Lab보다 2시간 이상 빨리 퇴원 처리됨
    anom_lab = is_lab_before_trans & (admissions['dischtime'] < (admissions['lab_last_time']))
    anom_lab_d = is_lab_before_trans & (admissions['deathtime'] < (admissions['lab_last_time']))
    # 3-2. 전원 전 Chart보다 2시간 이상 빨리 퇴원 처리됨
    anom_chart = is_chart_before_trans & (admissions['dischtime'] < (admissions['chart_last_time']))
    anom_chart_d = is_chart_before_trans & (admissions['deathtime'] < (admissions['chart_last_time']))
    # 둘 중 하나라도 만족하면 조건 3 충족
    cond3 = anom_lab | anom_chart
    target_mask = cond0 & cond1 & cond2 & cond3
    # print(admissions[target_mask]) #4927
    # print(admissions[(admissions['transfer_outtime_max'] < (admissions['lab_last_time']))&(admissions['transfer_outtime_max'] < (admissions['chart_last_time']))]) #None
    # print(admissions[(admissions['dischtime'] < (admissions['lab_last_time']))&(admissions['dischtime'] < (admissions['chart_last_time']))]) #599
    # print(admissions[(admissions['deathtime'] < (admissions['lab_last_time'])) & (admissions['deathtime'] < (admissions['chart_last_time']))& (admissions['transfer_outtime_max'] < (admissions['last_event']))]) #6
    # print(len(admissions)) # 545825

    """
    target_mask에 해당하는 row에 대해
    dischtime +1day, +2day...를 통해
    dischtime <=transfer_outtime_max & (dischtime >lab_last_time or dischtime >chart_last_time) 를 달성. 
    Up to transfer_outtime_max"""
    # ---------------------------------------------------------
    # 1. Dischtime 업데이트
    # ---------------------------------------------------------
    sub = admissions.loc[target_mask].copy()
    valid_chart = sub['chart_last_time'].where(sub['chart_last_time'] <= sub['transfer_outtime_max'])
    valid_lab = sub['lab_last_time'].where(sub['lab_last_time'] <= sub['transfer_outtime_max'])
    max_event_time = pd.concat([valid_chart, valid_lab], axis=1).max(axis=1)
    time_diff = max_event_time - sub['dischtime']
    days_to_add = (time_diff / pd.Timedelta(days=1)).apply(np.ceil)
    days_to_add = days_to_add.fillna(0).clip(lower=0)
    candidate_time = sub['dischtime'] + pd.to_timedelta(days_to_add, unit='D')
    final_time = pd.concat([candidate_time, sub['transfer_outtime_max']], axis=1).min(axis=1)
    admissions.loc[target_mask, 'dischtime'] = final_time
    # ---------------------------------------------------------
    # 2. Deathtime 업데이트 (값이 존재하는 경우만)
    # ---------------------------------------------------------
    target_mask_d = cond0 & cond1_d&cond2&(anom_lab_d | anom_chart_d)
    sub = admissions.loc[target_mask_d].copy()
    valid_chart = sub['chart_last_time'].where(sub['chart_last_time'] <= sub['transfer_outtime_max'])
    valid_lab = sub['lab_last_time'].where(sub['lab_last_time'] <= sub['transfer_outtime_max'])
    max_event_time = pd.concat([valid_chart, valid_lab], axis=1).max(axis=1)
    time_diff = max_event_time - sub['deathtime']
    days_to_add = (time_diff / pd.Timedelta(days=1)).apply(np.ceil)
    days_to_add = days_to_add.fillna(0).clip(lower=0)
    candidate_time = sub['deathtime'] + pd.to_timedelta(days_to_add, unit='D')
    final_time = pd.concat([candidate_time, sub['transfer_outtime_max']], axis=1).min(axis=1)
    admissions.loc[target_mask_d, 'deathtime'] = final_time
    # ---------------------------------------------------------
    # 3. transfer_outtime_max < last_event
    # 인 경우 -->
    # dischtime / deathtime을 transfer_outtime_max로 변경. Up to 48hr
    # ---------------------------------------------------------
    cond_event_anomaly = admissions['transfer_outtime_max'] < admissions['last_event']
    cond_event_anomaly = cond_event_anomaly & (admissions['dischtime'] < (admissions['next_admittime'] - pd.Timedelta(hours=24.0)))
    limit = pd.Timedelta(hours=48)
    # 3-1. Dischtime 업데이트
    # 대상 데이터 추출
    sub = admissions.loc[cond_event_anomaly]
    # (1) 시간 차이 계산: 목표 시간(Transfer) - 현재 시간(Disch)
    # 예: Transfer가 1일, Disch가 5일이면 delta는 -4일
    delta_disch = sub['transfer_outtime_max'] - sub['dischtime']
    # (2) 변화량 제한 (Clamping): 차이를 [-24h, +24h] 범위로 자름
    # 예: -4일 -> -1일로 제한됨
    clipped_delta_disch = delta_disch.clip(lower=-limit, upper=limit)
    # (3) 원본 업데이트: 현재 시간 + 제한된 변화량
    admissions.loc[cond_event_anomaly, 'dischtime'] = sub['dischtime'] + clipped_delta_disch
    # 3-2. Deathtime 업데이트 (값이 있는 경우만)
    # 조건 만족 & Deathtime이 존재하는(Not NaT) 행
    mask_death = cond_event_anomaly & admissions['deathtime'].notna()
    sub_death = admissions.loc[mask_death]
    # (1) 시간 차이 계산
    delta_death = sub_death['transfer_outtime_max'] - sub_death['deathtime']
    # (2) 변화량 제한
    clipped_delta_death = delta_death.clip(lower=-limit, upper=limit)
    # (3) 원본 업데이트
    admissions.loc[mask_death, 'deathtime'] = sub_death['deathtime'] + clipped_delta_death


    """admissions[(admissions['dischtime'] <= (admissions['admittime'])이 경우
    admittime을 transfer_intime_min로
    dischtime을 transfer_outtime_max로 바꾸는데 변화하는 시간이 최대 24hr로 변경"""
    # 1. 대상 선정: 퇴원시간 <= 입원시간
    mask = admissions['dischtime'] <= admissions['admittime']
    limit = pd.Timedelta(hours=24)
    # -------------------------------------------------------
    # 함수: 목표 시간(target)으로 이동하되, 최대 limit까지만 이동
    # -------------------------------------------------------
    def clip_time_shift(current_times, target_times, limit):
        # 1. 이동해야 할 시간 차이 계산 (Target - Current)
        delta = target_times - current_times

        # 2. 시간 차이를 [-24h, +24h] 범위로 자름 (Clamping)
        #    - delta가 24h보다 크면 -> 24h
        #    - delta가 -24h보다 작으면 -> -24h
        #    - 그 사이면 -> delta 그대로
        clamped_delta = delta.clip(lower=-limit, upper=limit)

        # 3. 현재 시간에 제한된 차이를 더함
        return current_times + clamped_delta
    # -------------------------------------------------------
    # 실제 적용
    # -------------------------------------------------------
    # 대상 데이터 추출
    subset = admissions.loc[mask]
    # 1. Admittime 업데이트 (Target: transfer_intime_min)
    admissions.loc[mask, 'admittime'] = clip_time_shift(
        subset['admittime'],
        subset['transfer_intime_min'],
        limit
    )
    mask = mask & (admissions['dischtime'] < (admissions['next_admittime'] - pd.Timedelta(hours=24.0)))
    # 2. Dischtime 업데이트 (Target: transfer_outtime_max)
    admissions.loc[mask, 'dischtime'] = clip_time_shift(
        subset['dischtime'],
        subset['transfer_outtime_max'],
        limit
    )

    """이렇게 admissions 갖고 다 조정 했으니
    이제 stays랑 비교해서 admit-discharge 사이에 icu event가 잘 위치하는지 확인"""
    # 그룹화 및 집계 (Named Aggregation 사용)
    icustay_partial_ = icustays.groupby(['subject_id', 'hadm_id']).agg(
        min_intime=('intime', 'min'),
        max_outtime=('outtime', 'max')
    ).reset_index()
    # ---------------------------------------------------------
    # 1. hadm_id 존재 여부 확인 (Validation)
    # ---------------------------------------------------------
    icustay_ids = set(icustay_partial_['hadm_id'])
    admission_ids = set(admissions['hadm_id'])
    missing_ids = icustay_ids - admission_ids
    if missing_ids:
        print(f"[Warning] icustay에는 있지만 admissions에 없는 hadm_id 개수: {len(missing_ids)}")
        raise AttributeError
        # 필요하다면 missing_ids를 출력해볼 수 있습니다.
    else:
        print("[Check] icustay의 모든 hadm_id가 admissions에 존재합니다.")
    # ---------------------------------------------------------
    # 2. 데이터 병합 및 시간 비교
    # ---------------------------------------------------------
    # 'min_intime', 'max_outtime'이 있는 데이터만 비교하면 되므로 inner merge 사용
    # (admissions에 컬럼이 붙습니다)
    merged_df = pd.merge(
        admissions,
        icustay_partial_[['hadm_id', 'min_intime', 'max_outtime']],
        on='hadm_id',
        how='inner'
    )
    # ---------------------------------------------------------
    # 3. 조건 위반 데이터 찾기 (아닌 row들)
    # 정상 조건: admittime <= min_intime  AND  dischtime >= max_outtime
    # 위반 조건: admittime > min_intime   OR   dischtime < max_outtime
    # ---------------------------------------------------------
    error_mask = (
            (merged_df['admittime'] > merged_df['min_intime']) |
            (merged_df['dischtime'] < merged_df['max_outtime'])
    )
    anomalous_rows = merged_df[error_mask]
    # 결과 출력
    print(f"\n시간 논리 오류가 발견된 row 개수: {len(anomalous_rows)}")
    # print(merged_df[merged_df['admittime'] > merged_df['min_intime']])#421
    # print(merged_df[merged_df['dischtime'] < merged_df['max_outtime']])#12892
    #
    # print(merged_df[merged_df['transfer_intime_min'] > merged_df['min_intime']])  # 0
    # print(merged_df[merged_df['transfer_outtime_max'] < merged_df['max_outtime']])  # 0

    # 1. 조건에 맞는 행 찾기 (입원시간이 ICU 입실시간보다 늦은 경우)
    cond = merged_df['admittime'] > merged_df['min_intime']
    # 대상 데이터만 추출
    target_rows = merged_df.loc[cond]
    # 2. 새로운 시간 계산 (Logic: Max 함수 사용)
    # - 목표 시간: min_intime
    # - 제한 시간: admittime - 24시간
    # - 둘 중 더 늦은 시간을 선택하면 "최대 24시간까지만 당겨지는" 효과가 남
    limit_time = target_rows['admittime'] - pd.Timedelta(hours=24)
    new_admittime = pd.concat([target_rows['min_intime'], limit_time], axis=1).max(axis=1)
    # 3. 원본 admissions 데이터프레임 업데이트
    # hadm_id를 키로 사용하여 값을 매핑합니다.
    # (admissions의 순서가 merged_df와 다를 수 있으므로 map 방식 권장)
    # 업데이트할 hadm_id가 있는 행만 선택
    mask_in_admissions = admissions['hadm_id'].isin(target_rows['hadm_id'])
    # hadm_id를 기준으로 매핑하여 값 업데이트
    # new_admittime은 hadm_id가 인덱스가 아니므로, 매핑을 위해 인덱스 설정이 필요할 수 있습니다.
    # 가장 확실한 방법: Series로 변환 (Index: hadm_id, Value: new_time)
    update_map = pd.Series(new_admittime.values, index=target_rows['hadm_id'])
    admissions.loc[mask_in_admissions, 'admittime'] = admissions.loc[mask_in_admissions, 'hadm_id'].map(update_map)
    # 결과 확인
    print(f"Updated {len(target_rows)} admittime rows.")

    # 1. 조건에 맞는 행 찾기 (퇴원시간이 ICU 퇴실시간보다 이른 경우)
    cond = merged_df['dischtime'] < merged_df['max_outtime']
    cond = cond & (merged_df['dischtime'] < (merged_df['next_admittime'] - pd.Timedelta(hours=24.0)))
    target_rows = merged_df.loc[cond]
    # 2. 새로운 시간 계산 (Logic: Min 함수 사용)
    # - 목표 시간: max_outtime
    # - 제한 시간: dischtime + 24시간
    # - 둘 중 더 이른 시간을 선택하면 "최대 24시간까지만 뒤로 밀리는" 효과가 남
    limit_time = target_rows['dischtime'] + pd.Timedelta(hours=48)
    new_dischtime = pd.concat([target_rows['max_outtime'], limit_time], axis=1).min(axis=1)
    # 3. 원본 admissions 데이터프레임 업데이트
    # 업데이트할 hadm_id가 있는 행만 선택
    mask_in_admissions = admissions['hadm_id'].isin(target_rows['hadm_id'])
    # hadm_id를 기준으로 매핑하여 값 업데이트 (인덱스 매칭을 위해 Series 생성)
    update_map = pd.Series(new_dischtime.values, index=target_rows['hadm_id'])
    admissions.loc[mask_in_admissions, 'dischtime'] = admissions.loc[mask_in_admissions, 'hadm_id'].map(update_map)
    # 결과 확인
    print(f"Updated {len(target_rows)} rows for dischtime adjustment.")

    admissions = admissions[original_admissions_columns].copy()
    print('Processed admission length', len(admissions))

    return admissions, icustays

def refine_death_label(admissions):
    '''
    in-hosp mortality labels ('DIED' or 'flag' or 'deathtime') ==> In hospital mortality;; time to 'dischtime'
    '''
    # 1. in-hospital death condition
    death_mask = (
            admissions['deathtime'].notna() |
            (admissions['hospital_expire_flag'] == 1) |
            (admissions['discharge_location'] == 'DIED')
    )

    # ------------------------------------------------
    # (1) deathtime이 NaN → dischtime로 채움
    # ------------------------------------------------
    fill_mask = death_mask & admissions['deathtime'].isna()
    admissions.loc[fill_mask, 'deathtime'] = admissions.loc[fill_mask, 'dischtime']

    # ------------------------------------------------
    # (2) deathtime > dischtime → dischtime을 deathtime으로 미룸
    # ------------------------------------------------
    shift_mask = death_mask & (admissions['deathtime'] > admissions['dischtime'])
    admissions.loc[shift_mask, 'dischtime'] = admissions.loc[shift_mask, 'deathtime']

    # 조건:
    # 1) deathtime < dischtime
    # 2) deathtime 시각이 00:00:00
    mask_midnight_error = (
            admissions['deathtime'].notna() &
            (admissions['deathtime'] < admissions['dischtime']) &
            (admissions['deathtime'].dt.time == pd.to_datetime("00:00:00").time())
    )

    # deathtime을 dischtime으로 교체
    admissions.loc[mask_midnight_error, 'deathtime'] = admissions.loc[mask_midnight_error, 'dischtime']

    # 2. 수정할 row들만 데이터프레임에 반영
    admissions.loc[death_mask, 'hospital_expire_flag'] = 1
    admissions.loc[death_mask, 'discharge_location'] = 'DIED'

    return admissions


def remove_after_death(patients, admits, stays, labevents_partial, chartevents_partial, chartevents_partial_stay):
    admissions = admits
    icustays = stays
    """
    hospital_expire_flag이 1이 존재하는 subject_id에 대해
    - admissions: admittime > deathtime 인 row 제거
    - icustays:  intime    > deathtime 인 row 제거
    """
    # datetime 타입 보장
    admissions['admittime'] = pd.to_datetime(admissions['admittime'])
    admissions['deathtime'] = pd.to_datetime(admissions['deathtime'])
    icustays['intime'] = pd.to_datetime(icustays['intime'])
    icustays['outtime'] = pd.to_datetime(icustays['outtime'])

    # subject_id별 사망 시점 (hospital_expire_flag == 1)
    death_time_map = (
        admissions.loc[admissions['hospital_expire_flag'] == 1]
        .dropna(subset=['deathtime'])
        .groupby('subject_id')['deathtime']
        .min()
    )

    # 삭제 대상 mask (Series.map 사용 → 컬럼 추가 없음)
    mask_del = (
            (admissions['hospital_expire_flag']!=1) &
            admissions['subject_id'].isin(death_time_map.index) &
            (admissions['admittime'] > admissions['subject_id'].map(death_time_map))
    )

    # 삭제 개수
    n_adm_deleted = mask_del.sum()

    del_admissions = admissions.loc[mask_del].copy()

    # row 삭제 (컬럼/순서 그대로 유지)
    admissions = admissions.loc[~mask_del].reset_index(drop=True)

    # ------------------------------------------------
    # 4. icustays 정리
    # ------------------------------------------------
    expire_flag_map = admissions.set_index('hadm_id')['hospital_expire_flag']
    mask_icu_del = (
            icustays['subject_id'].isin(death_time_map.index) &
            (icustays['intime'] > icustays['subject_id'].map(death_time_map))
            #& (icustays['hadm_id'].map(expire_flag_map) != 1)  # 조건 추가: flag가 1이 아닌 경우
    )

    # 🔑 삭제될 row 미리 저장
    icu_removed = icustays.loc[mask_icu_del].copy()

    n_icu_deleted = mask_icu_del.sum()
    del_icustays = icustays.loc[mask_icu_del].copy()
    icustays = icustays.loc[~mask_icu_del].reset_index(drop=True)

    # ------------------------------------------------
    # 5. 결과 출력
    # ------------------------------------------------
    print(f"Deleted admissions rows: {n_adm_deleted}")
    print(f"Deleted icustays rows:   {n_icu_deleted}")

    print(del_admissions)
    print(del_icustays)

    """del_admissions df에 대해
    각 hadm_id에 대해서 labevents_partial 과 chartevents_partial의 hadm_id에 대해 대응되는 'charttime'이 NaT인것을 확인"""
    target_ids = del_admissions[['subject_id', 'hadm_id']].copy()
    # 2. Labevents와 병합 (Left Join)
    # charttime 컬럼만 가져와서 병합합니다.
    # suffixes를 사용하여 이름 충돌을 방지합니다 (_lab, _chart)
    merged = target_ids.merge(
        labevents_partial[['hadm_id', 'charttime']],
        on='hadm_id',
        how='left'
    ).rename(columns={'charttime': 'lab_time'})
    # 3. Chartevents와 병합 (Left Join)
    merged = merged.merge(
        chartevents_partial[['hadm_id', 'charttime']],
        on='hadm_id',
        how='left'
    ).rename(columns={'charttime': 'chart_time'})
    # 4. 검증: Lab이나 Chart 둘 중 하나라도 시간이 존재하는(NaT가 아닌) 데이터 찾기
    # notna()는 값이 존재하면 True입니다.
    has_valid_event = merged['lab_time'].notna() | merged['chart_time'].notna()
    anomalies = merged[has_valid_event]
    # 5. 결과 출력
    print(f"검사 대상 hadm_id 개수: {len(target_ids)}")
    if anomalies.empty:
        print("✅ 확인 완료: 모든 hadm_id에 대해 charttime이 NaT이거나 데이터가 없습니다.")
    else:
        print(f"⚠️ 경고: {len(anomalies)}개의 hadm_id에서 유효한 charttime이 발견되었습니다.")
        raise "ERR"

    """del_icustays df에 대해
    각 stay_id에 대해서 chartevents_partial_stay의 stay_id에 대해 대응되는 값이 없거나 'charttime'이 NaT인것을 확인"""
    print(chartevents_partial_stay)
    check_df = pd.merge(
        del_icustays,
        chartevents_partial_stay[['stay_id', 'charttime']],
        on='stay_id',
        how='left'
    )
    # 2. 조건 확인
    # Case A: chartevents_partial_stay에 stay_id가 아예 없어서 NaN이 된 경우
    # Case B: 있긴 하지만 원래 데이터가 NaT인 경우
    # 위 두 경우 모두 pd.isna()로 한 번에 감지 가능합니다.
    problematic_rows = check_df[check_df['charttime'].isna()]
    # 결과 출력
    print(f"문제가 있는 행의 개수: {len(problematic_rows)}")
    # 문제가 있는 유니크한 stay_id 목록 확인
    problem_stay_ids = problematic_rows['stay_id'].unique()
    print(f"문제가 있는 stay_id 개수: {len(problem_stay_ids)}")


    return patients, admissions, icustays


def add_dod_to_admits(patients, admissions): # Out of hospital death
    patients = patients.copy()
    admissions = admissions.copy()

    # 1. patients의 subject_id에 중복이 없는지 확인
    assert not patients['subject_id'].duplicated().any(), \
        "patients에 중복된 subject_id가 존재합니다"

    # 2. patients ⊇ admissions subject_id 확인
    missing = set(admissions['subject_id']) - set(patients['subject_id'])
    assert not missing, \
        f"patients에 없는 subject_id가 admissions에 존재: {len(missing)}개"

    # 3. patients에서 admissions에 존재하는 subject_id만 유지
    patients = patients[
        patients['subject_id'].isin(admissions['subject_id'])
    ].copy()

    # 4. admissions 처리
    #   - subject_id별 dischtime 정렬
    #   - 마지막 row 제외한 나머지는 hospital_expire_flag != 1 확인
    #   - subject_id별 마지막 row만 유지
    admissions = admissions.sort_values(['subject_id', 'dischtime'])

    for sid, g in admissions.groupby('subject_id'):
        try:
            if len(g) > 1:
                assert (g.iloc[:-1]['hospital_expire_flag'] != 1).all(), \
                    f"subject_id {sid}: 마지막 admission 이전에 hospital_expire_flag=1 존재"
        except:
            print(g)
            print(sid)

    admissions_last = (
        admissions
        .groupby('subject_id', as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )

    # 5. patients와 admissions_last merge
    merged = patients.merge(
        admissions_last,
        on='subject_id',
        how='inner',
        suffixes=('_pat', '_adm')
    )

    assert len(merged) == len(patients) == len(admissions_last)
    assert set(merged['subject_id']) == set(patients['subject_id'])

    # 6 & 7. dod 처리
    merged['dod'] = pd.to_datetime(merged['dod'])
    merged['dischtime'] = pd.to_datetime(merged['dischtime'])

    merged = merged[merged['hospital_expire_flag'] != 1]

    merged['dod'] = merged['dod'] + pd.Timedelta(days=1)

    # --------------------------------------------------
    # patients / admissions 형태로 다시 분리
    # --------------------------------------------------
    # patients_out = merged[patients.columns].copy()
    # admissions_out = merged[admissions_last.columns].copy()

    return merged
