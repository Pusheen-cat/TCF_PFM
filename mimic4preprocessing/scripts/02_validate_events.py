import os
import argparse
import pandas as pd
from tqdm import tqdm
import shutil
import json
from collections import Counter, defaultdict
# Allow running this file directly (python <path>): put the repo root on sys.path.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mimic4preprocessing.my_itemid import my_itemid
from datetime import timedelta

def is_subject_folder(x):
    return str.isdigit(x)

def make_item_key(itemid, itemname, linksto):
    return f"{int(itemid)}||{itemname}||{linksto}"

def main():

    n_events = 0                   # total number of events
    empty_hadm = 0                 # HADM_ID is empty in events.csv. We exclude such events.
    no_hadm_in_stay = 0            # HADM_ID does not appear in stays.csv. We exclude such events.
    no_icustay = 0                 # ICUSTAY_ID is empty in events.csv. We try to fix such events.
    recovered = 0                  # empty ICUSTAY_IDs are recovered according to stays.csv files (given HADM_ID)
    could_not_recover = 0          # empty ICUSTAY_IDs that are not recovered. This should be zero.
    icustay_missing_in_stays = 0   # ICUSTAY_ID does not appear in stays.csv. We exclude such events.

    # -----------------------------
    # global accumulators
    # -----------------------------
    itemid_counter = Counter()  # ITEMID -> total count
    itemid_value_counter = defaultdict(Counter)  # ITEMID -> (VALUE -> count)
    itemid_unit_counter = defaultdict(Counter)  # ITEMID -> (UNIT -> count)
    itemid_unit_value_counter = defaultdict(lambda: defaultdict(Counter)) # ITEMID -> (UNIT -> (VALUE -> count))

    removed_subjects = []   # 제거된 subject_id 기록

    parser = argparse.ArgumentParser()
    parser.add_argument('subjects_root_path', type=str,
                        help='Directory containing subject subdirectories.')
    args = parser.parse_args()
    print(args)

    subdirectories = os.listdir(args.subjects_root_path)
    subjects = list(filter(is_subject_folder, subdirectories))

    for subject in tqdm(subjects, desc='Iterating over subjects'):
        subject_dir = os.path.join(args.subjects_root_path, subject)
        events_path = os.path.join(subject_dir, 'events.csv')
        stays_path = os.path.join(subject_dir, 'stays.csv')

        # ✅ events.csv가 없으면 subject 폴더 삭제
        if (not os.path.exists(events_path)) or (not os.path.exists(stays_path)):
            shutil.rmtree(subject_dir)
            removed_subjects.append(subject)
            continue

        stays_df = pd.read_csv(os.path.join(args.subjects_root_path, subject, 'stays.csv'), index_col=False,
                               dtype={'hadm_id': str, "stay_id": str})
        stays_df.columns = stays_df.columns.str.upper()

        # assert that there is no row with empty ICUSTAY_ID or HADM_ID
        #assert(not stays_df['STAY_ID'].isnull().any())
        assert(not stays_df['HADM_ID'].isnull().any())

        # assert there are no repetitions of ICUSTAY_ID or HADM_ID
        # since admissions with multiple ICU stays were excluded
        #assert(len(stays_df['STAY_ID'].unique()) == len(stays_df['STAY_ID']))
        assert stays_df['STAY_ID'].dropna().is_unique, "Duplicate STAY_ID found"
        #assert(len(stays_df['HADM_ID'].unique()) == len(stays_df['HADM_ID']))
        events_df = pd.read_csv(os.path.join(args.subjects_root_path, subject, 'events.csv'), index_col=False,
                                dtype={'hadm_id': str, "stay_id": str})
        events_df.columns = events_df.columns.str.upper()
        n_events += events_df.shape[0]

        # we drop all events for them HADM_ID is empty
        # TODO: maybe we can recover HADM_ID by looking at ICUSTAY_ID
        empty_hadm += events_df['HADM_ID'].isnull().sum()
        #events_df = events_df.dropna(subset=['HADM_ID'])

        merged_df = events_df
        merged_df['CHARTTIME'] = pd.to_datetime(merged_df['CHARTTIME'], errors='coerce')
        merged_df = (
            merged_df
            .sort_values(by=['CHARTTIME', 'ORDER'], ascending=[True, False])
            .reset_index(drop=True)
        )

        # merged_df = events_df.merge(stays_df, left_on=['HADM_ID'], right_on=['HADM_ID'],
        #                             how='left', suffixes=['', '_r'], indicator=True)

        # we drop all events for which HADM_ID is not listed in stays.csv
        # since there is no way to know the targets of that stay (for example mortality)
        # no_hadm_in_stay += (merged_df['_merge'] == 'left_only').sum()
        # merged_df = merged_df[merged_df['_merge'] == 'both']

        # if ICUSTAY_ID is empty in stays.csv, we try to recover it
        # we exclude all events for which we could not recover ICUSTAY_ID
        # cur_no_icustay = merged_df['STAY_ID'].isnull().sum()
        # no_icustay += cur_no_icustay
        # merged_df.loc[:, 'STAY_ID'] = merged_df['STAY_ID'].fillna(merged_df['STAY_ID_r'])
        # recovered += cur_no_icustay - merged_df['STAY_ID'].isnull().sum()
        # could_not_recover += merged_df['STAY_ID'].isnull().sum()
        # merged_df = merged_df.dropna(subset=['STAY_ID'])
        #
        # # now we take a look at the case when ICUSTAY_ID is present in events.csv, but not in stays.csv
        # # this mean that ICUSTAY_ID in events.csv is not the same as that of stays.csv for the same HADM_ID
        # # we drop all such events
        # icustay_missing_in_stays += (merged_df['STAY_ID'] != merged_df['STAY_ID_r']).sum()
        # merged_df = merged_df[(merged_df['STAY_ID'] == merged_df['STAY_ID_r'])]

        """ 
        여기서 GCS - Total 생성한다
        규칙은 1시간 이내에 3개의 GCS들 (E,V,M)이 존재하면 마지막 GCS 시간에 GCS-Total 추가
        """
        gcss = {220739: {'nan':1, 'Spontaneously': 4, 'To Speech': 3, 'To Pain': 2},
                223900: {'Oriented': 5, 'No Response-ETT': 1, 'Confused': 4, 'No Response': 1, 'Incomprehensible sounds': 2, 'Inappropriate Words': 3},
                223901: {'Obeys Commands': 6, 'Localizes Pain': 5, 'No response': 1, 'Flex-withdraws': 4, 'Abnormal Flexion': 3, 'Abnormal extension': 2},
        }
        GCS_ITEMIDS = set(gcss.keys())
        total_gcs_name = 'GCS - Total'
        TOTAL_ITEMID = my_itemid[total_gcs_name][0]
        # GCS row만 추출
        gcs_df = merged_df[merged_df['ITEMID'].isin(GCS_ITEMIDS)].copy()
        # 사용 여부 플래그
        gcs_df['used'] = False
        new_rows = []

        # 시간 순으로 순회
        for idx, row in gcs_df.iterrows():
            if row['used']:
                continue

            current_time = row['CHARTTIME']
            window_start = current_time - timedelta(hours=1)
            # 1시간 윈도우 내, 아직 사용되지 않은 GCS들
            window = gcs_df[
                (~gcs_df['used']) &
                (gcs_df['CHARTTIME'] >= window_start) &
                (gcs_df['CHARTTIME'] <= current_time)
                ]
            # ITEMID별 마지막 값
            last_rows = (
                window.sort_values('CHARTTIME')
                .groupby('ITEMID', as_index=False)
                .tail(1)
            )
            # 3종류 모두 있는지 확인
            if set(last_rows['ITEMID']) == GCS_ITEMIDS:
                total_score = 0
                for _, r in last_rows.iterrows():
                    itemid = r['ITEMID']
                    value = str(r['VALUE'])
                    score = gcss[itemid].get(value)

                    if score is None:
                        raise AttributeError
                    total_score += score
                else:
                    # 마지막 시간의 row를 기준으로 GCS-Total 생성
                    base_row = last_rows.sort_values('CHARTTIME').iloc[-1]

                    new_row = base_row.copy()
                    new_row['ITEMID'] = TOTAL_ITEMID
                    new_row['ITEMNAME'] = total_gcs_name
                    new_row['VALUE'] = str(total_score)
                    new_row['VALUEUOM'] = ''
                    new_row['LINKSTO'] = base_row['LINKSTO']
                    new_row['ORDER'] = int(base_row['ORDER'])-1
                    new_rows.append(new_row)
                    # 사용 처리
                    gcs_df.loc[window.index, 'used'] = True
        # GCS-Total row들을 DataFrame으로
        if new_rows:
            gcs_total_df = pd.DataFrame(new_rows)
            merged_df = pd.concat([merged_df, gcs_total_df], ignore_index=True)
        # 최종 정렬
        merged_df = (
            merged_df
            .sort_values(by=['CHARTTIME', 'ORDER'], ascending=[True, False])
            .reset_index(drop=True)
        )

        to_write = merged_df[['SUBJECT_ID', 'HADM_ID', 'STAY_ID', 'CHARTTIME', 'ITEMID', 'ITEMNAME', 'VALUE', 'VALUEUOM', 'LINKSTO', 'ORDER']]
        to_write.columns = to_write.columns.str.lower()
        to_write.to_csv(os.path.join(args.subjects_root_path, subject, 'events.csv'), index=False)

        # -------------------------------------------------
        # NaN 제거 (VALUE는 string으로 통일)
        sub_df = events_df[['ITEMID', 'ITEMNAME', 'VALUE', 'VALUEUOM', 'LINKSTO']].dropna(subset=['ITEMID'])
        sub_df['VALUE'] = sub_df['VALUE'].astype(str)
        sub_df['VALUEUOM'] = sub_df['VALUEUOM'].astype(str)  # ✅ 추가

        # ITEMID count 누적
        keys = [
            make_item_key(i, n, l)
            for i, n, l in zip(sub_df['ITEMID'], sub_df['ITEMNAME'], sub_df['LINKSTO'])
        ]
        itemid_counter.update(keys)

        # ITEMID - VALUE count 누적
        for i, n, l, value in zip(
                sub_df['ITEMID'],
                sub_df['ITEMNAME'],
                sub_df['LINKSTO'],
                sub_df['VALUE']
        ):
            key = make_item_key(i, n, l)
            itemid_value_counter[key][value] += 1
        for i, n, l, unit in zip(
                sub_df['ITEMID'],
                sub_df['ITEMNAME'],
                sub_df['LINKSTO'],
                sub_df['VALUEUOM']
        ):
            key = make_item_key(i, n, l)
            itemid_unit_counter[key][unit] += 1
        for i, n, l, value, unit in zip(
                sub_df['ITEMID'],
                sub_df['ITEMNAME'],
                sub_df['LINKSTO'],
                sub_df['VALUE'],
                sub_df['VALUEUOM']
        ):
            key = make_item_key(i, n, l)
            itemid_unit_value_counter[key][unit][value] += 1
        # -------------------------------------------------

    # ✅ 제거된 subject 개수 기록
    removed_txt_path = os.path.join(args.subjects_root_path, 'removed_subjects.txt')
    print('subjects removed: ', len(removed_subjects))
    with open(removed_txt_path, 'w') as f:
        f.write(f"Total removed subjects due to no events.csv : {len(removed_subjects)}\n")
        for sid in removed_subjects:
            f.write(f"{sid}\n")

    assert(could_not_recover == 0)
    print('n_events: {}'.format(n_events))
    print('empty_hadm: {}'.format(empty_hadm))
    print('no_hadm_in_stay: {}'.format(no_hadm_in_stay))
    print('no_icustay: {}'.format(no_icustay))
    print('recovered: {}'.format(recovered))
    print('could_not_recover: {}'.format(could_not_recover))
    print('icustay_missing_in_stays: {}'.format(icustay_missing_in_stays))

    # 1. ITEMID별 개수 dict (내림차순)
    # -------------------------------------------------
    itemid_count_dict = dict(
        sorted(itemid_counter.items(), key=lambda x: x[1], reverse=True)
    )

    # -------------------------------------------------
    # 2. ITEMID -> VALUE -> count (정렬 포함)
    #    - ITEMID: 전체 count 기준 내림차순
    #    - VALUE: 각 ITEMID 내에서 count 기준 내림차순
    # -------------------------------------------------
    itemid_value_dict = {}
    itemid_unit_dict = {}
    itemid_unit_value_dict = {}

    for itemid, _ in itemid_counter.most_common():

        # VALUE
        value_counter = itemid_value_counter[itemid]
        itemid_value_dict[itemid] = dict(
            sorted(value_counter.items(), key=lambda x: x[1], reverse=True)
        )

        # UNIT
        unit_counter = itemid_unit_counter[itemid]
        itemid_unit_dict[itemid] = dict(
            sorted(unit_counter.items(), key=lambda x: x[1], reverse=True)
        )

        # UNIT -> VALUE
        unit_value_dict = {}
        for unit, v_counter in itemid_unit_value_counter[itemid].items():
            unit_value_dict[unit] = dict(
                sorted(v_counter.items(), key=lambda x: x[1], reverse=True)
            )

        itemid_unit_value_dict[itemid] = unit_value_dict

    # -------------------------------------------------
    # JSON 각각 저장
    # -------------------------------------------------
    out_root = args.subjects_root_path

    itemid_count_path = os.path.join(out_root, 'itemid_count.json')
    itemid_value_count_path = os.path.join(out_root, 'itemid_value_count.json')
    itemid_unit_count_path = os.path.join(out_root, 'itemid_unit_count.json')
    itemid_unit_value_count_path = os.path.join(out_root, 'itemid_unit_value_count.json')

    with open(itemid_count_path, 'w') as f:
        json.dump(itemid_count_dict, f, indent=2)

    with open(itemid_value_count_path, 'w') as f:
        json.dump(itemid_value_dict, f, indent=2)

    with open(itemid_unit_count_path, 'w') as f:
        json.dump(itemid_unit_dict, f, indent=2)

    with open(itemid_unit_value_count_path, 'w') as f:
        json.dump(itemid_unit_value_dict, f, indent=2)

    print(f"Saved ITEMID count     → {itemid_count_path}")
    print(f"Saved ITEMID-VALUE map → {itemid_value_count_path}")
    print(f"Saved ITEMID-UNIT map → {itemid_unit_count_path}")
    print(f"Saved ITEMID-UNIT-VALUE map → {itemid_unit_value_count_path}")


if __name__ == "__main__":
    main()
