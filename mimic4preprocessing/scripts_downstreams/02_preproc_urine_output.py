import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
from collections import Counter

# Preprocessing roots (edit or set these env vars; see README).
MIMIC4_ROOT = os.environ.get("MIMIC4_ROOT", "/path/to/mimiciv/3.1")
_ICU = os.path.join(MIMIC4_ROOT, "icu")

# 샘플 데이터 (실제 사용시에는 pd.read_csv('your_file.csv')로 대체)
path = os.path.join(_ICU, 'outputevents.csv')
icustay_path = os.path.join(_ICU, 'icustays.csv')

# CSV 데이터 읽기
df = pd.read_csv(path)
icustay_df = pd.read_csv(icustay_path)

# ICUSTAY 데이터 전처리
icustay_df['intime'] = pd.to_datetime(icustay_df['intime'])
icustay_df['outtime'] = pd.to_datetime(icustay_df['outtime'])

print("원본 데이터:")
print(df)
print()

# mL이 아닌 경우 VALUE 값들의 분포 확인
df_filtered = df[df['itemid'].isin([226559,226560])].copy()
print("1. ITEMID foley-226559, void-226560 필터링 완료")
print("VALUEUOM 값들:", df_filtered['valueuom'].unique())
print("모든 VALUEUOM이 'mL'인가?", all(df_filtered['valueuom'] == 'mL'))

# mL이 아닌 경우 VALUE 값들의 분포 확인 (NaN 값 포함)
print("\nvalueuom 값별 상세 분석:")
for uom in df_filtered['valueuom'].unique():
    if pd.isna(uom):
        subset = df_filtered[df_filtered['valueuom'].isna()]
        print(f"  valueuom = NaN:")
    else:
        subset = df_filtered[df_filtered['valueuom'] == uom]
        print(f"  valueuom = '{uom}':")

    if not subset.empty:
        value_counter = Counter(subset['value'])
        print(f"    VALUE 분포: {dict(value_counter)}")
        print(f"    총 {len(subset)}개 행")
    else:
        print(f"    데이터 없음")

# 1. mL 데이터만 필터링
df_filtered = df_filtered[df_filtered['valueuom'] == 'mL']

# mL이 아닌 경우 VALUE 값들의 분포 확인 (NaN 값 포함)
print("\nVALUE 값별 상세 분석:")
subset = df_filtered[df_filtered['value'].isna()]
print(f"  VALUE = NaN: {len(subset)}")

# CHARTTIME을 datetime으로 변환
df_filtered['charttime'] = pd.to_datetime(df_filtered['charttime'])


# HADM_ID, ICUSTAY_ID가 NaN인 경우 ICUSTAY.csv에서 매칭하여 가져오기
def fill_missing_ids(row):
    if pd.isna(row['hadm_id']) or pd.isna(row['stay_id']):
        subject_id = row['subject_id']
        charttime = row['charttime']

        # 해당 SUBJECT_ID에 대해 CHARTTIME이 INTIME과 OUTTIME 사이에 있는 레코드 찾기
        matching_records = icustay_df[
            (icustay_df['subject_id'] == subject_id) &
            (icustay_df['intime'] <= charttime) &
            (icustay_df['outtime'] >= charttime)
            ]

        if len(matching_records) > 0:
            # 첫 번째 매칭 레코드 사용
            matched_record = matching_records.iloc[0]
            if pd.isna(row['hadm_id']):
                row['hadm_id'] = matched_record['hadm_id']
            if pd.isna(row['stay_id']):
                row['stay_id'] = matched_record['stay_id']
            print(
                f"매칭 성공: SUBJECT_ID {subject_id}, CHARTTIME {charttime} -> HADM_ID {matched_record['hadm_id']}, ICUSTAY_ID {matched_record['stay_id']}")
        else:
            print(
                f"매칭 실패: SUBJECT_ID {subject_id}, CHARTTIME {charttime}에 해당하는 HADM_ID, ICUSTAY_ID를 ICUSTAY.csv에서 찾을 수 없습니다.")

    return row


# 각 행에 대해 missing ID 채우기
print("\n=== HADM_ID, ICUSTAY_ID 매칭 시작 ===")
df_filtered = df_filtered.apply(fill_missing_ids, axis=1)
print("=== HADM_ID, ICUSTAY_ID 매칭 완료 ===\n")

# NaN 값이 남아있는 행 제거
# df_filtered = df_filtered.dropna(subset=['HADM_ID', 'ICUSTAY_ID'])

# ID 컬럼들을 int로 변환
df_filtered['subject_id'] = df_filtered['subject_id'].astype("Int64")
df_filtered['hadm_id'] = df_filtered['hadm_id'].astype("Int64")
df_filtered['stay_id'] = df_filtered['stay_id'].astype("Int64")

# 2. 정렬
df_filtered['charttime'] = pd.to_datetime(df_filtered['charttime'])
df_sorted = df_filtered.sort_values(['subject_id', 'hadm_id', 'stay_id', 'charttime']).reset_index(drop=True)
print("2. 정렬 완료")
print(df_sorted[['subject_id', 'hadm_id', 'stay_id', 'charttime', 'value']])
print()


# 3. 각 ICUSTAY_ID별로 6시간 평균 urine output 계산
def calculate_hourly_urine_output(group):
    # 시간순으로 정렬 (이미 정렬되어 있지만 확실히)
    group = group.sort_values('charttime').reset_index(drop=True)

    if len(group) < 2:
        return pd.DataFrame()  # 데이터가 부족하면 빈 DataFrame 반환

    # NaN 값 처리
    # 1. 제일 처음 위치가 nan인 경우 처리
    while len(group) > 0 and pd.isna(group.iloc[0]['value']):
        if len(group) > 1 and not pd.isna(group.iloc[1]['value']):
            # 다음 행의 value가 nan이 아니라면 첫번째 행의 value를 0으로 변경
            group.iloc[0, group.columns.get_loc('value')] = 0
            break
        else:
            # 다음 행의 value가 nan이거나 행이 하나뿐이라면 첫번째 행 제거
            group = group.iloc[1:].reset_index(drop=True)

    # 2. 남은 nan value 행들 제거
    group = group.dropna(subset=['value']).reset_index(drop=True)

    if len(group) < 2:
        return pd.DataFrame()  # 처리 후 데이터가 부족하면 빈 DataFrame 반환

    group = group.iloc[0:].reset_index(drop=True)

    if len(group) == 0:
        return pd.DataFrame()

    # 시간별 urine rate 계산 (mL/hour)
    rates = []
    for i in range(1,len(group)):# 첫 번째 데이터는 무시 (시작점 모름)

        prev_time = group.iloc[i - 1]['charttime']

        curr_time = group.iloc[i]['charttime']
        time_diff = (curr_time - prev_time).total_seconds() / 3600  # hours

        if time_diff > 0:
            if group.iloc[i]['value'] is not None: # None -> use prev rate
                rate = group.iloc[i]['value'] / time_diff  # mL/hour
            rates.append({
                'start_time': prev_time,
                'end_time': curr_time,
                'rate': rate,
                'volume': group.iloc[i]['value']
            })

    # 첫 번째 CHARTTIME + 6시간부터 시작
    first_time = group.iloc[0]['charttime']
    last_time = group.iloc[-1]['charttime']

    # 시작 시간을 정각으로 맞춤 (6시간 후)
    start_time = first_time + pd.Timedelta(hours=6)
    start_time = start_time.replace(minute=0, second=0, microsecond=0)

    # 종료 시간을 정각으로 맞춤
    end_time = last_time.replace(minute=0, second=0, microsecond=0)
    if last_time.minute > 0 or last_time.second > 0:
        end_time += pd.Timedelta(hours=1)

    if start_time > end_time:
        return pd.DataFrame()

    # 1시간 간격으로 시간 생성
    time_points = pd.date_range(start=start_time, end=end_time, freq='1h')

    result_rows = []

    for time_point in time_points:
        # 이전 6시간 동안의 평균 urine output 계산
        period_start = time_point - pd.Timedelta(hours=6)
        period_end = time_point

        total_output = 0

        # 해당 6시간 기간에 해당하는 rates 찾기
        for rate_info in rates:
            # 겹치는 시간 구간 계산
            overlap_start = max(period_start, rate_info['start_time'])
            overlap_end = min(period_end, rate_info['end_time'])

            if overlap_start < overlap_end:
                overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                total_output += rate_info['rate'] * overlap_hours

        # 6시간 평균으로 변환
        avg_hourly_output = total_output / 6

        result_rows.append({
            'subject_id': group.iloc[0]['subject_id'],
            'hadm_id': group.iloc[0]['hadm_id'],
            'stay_id': group.iloc[0]['stay_id'],
            'charttime': time_point,
            'AVG_HOURLY_URINE_OUTPUT': avg_hourly_output
        })

    return pd.DataFrame(result_rows)


# 각 ICUSTAY_ID별로 처리
result_dfs = []
for icustay_id in df_sorted['stay_id'].unique():
    group = df_sorted[df_sorted['stay_id'] == icustay_id]
    result_df = calculate_hourly_urine_output(group)
    if not result_df.empty:
        result_dfs.append(result_df)

# 최종 결과 합치기
if result_dfs:
    final_result = pd.concat(result_dfs, ignore_index=True)
    final_result = final_result.sort_values(['subject_id', 'hadm_id', 'stay_id', 'charttime']).reset_index(drop=True)

    # 최종 결과에서도 ID 컬럼들이 int인지 확인
    final_result['subject_id'] = final_result['subject_id'].astype("Int64")
    final_result['hadm_id'] = final_result['hadm_id'].astype("Int64")
    final_result['stay_id'] = final_result['stay_id'].astype("Int64")

    print("3. 최종 결과 - 6시간 평균 hourly urine output:")
    print(final_result)
    print()

    # 결과를 pkl 저장
    final_result.to_pickle(os.path.join(_ICU, 'outputevents_huo.pkl'))
    print("결과가 'outputevents_huo.pkl'로 저장되었습니다.")
else:
    print("처리할 수 있는 데이터가 없습니다.")
