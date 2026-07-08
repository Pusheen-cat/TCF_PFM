import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple
# from prepocessing.mimic3.lab_unit_numeric_matching.itemid_reference_range import reference_range_dict
# Allow running this file directly (python <path>): put the repo root on sys.path.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from functools import reduce
import pickle
import gc
import time
from mimic4preprocessing.my_itemid import my_itemid
from pfm_mimic4.dataset.ETHOS_row_add import ethos_array_label
from collections import Counter, defaultdict

def encode_with_given_tokenizer(input_data: List[Tuple], label_data: np.array, tokenizer) -> np.array:
    """
    주어진 tokenizer를 사용하여 input_data를 토큰화
    Args:
        input_data: [(time_str, datatype, [value]), ...]
        label_data: [np.array, np.array,...]
        tokenizer: tokenizer.encode(input_data) 메소드를 가진 객체
    Returns:
        [(time_str, datatype, token_idx), ...]
    """
    # tokenizer.encode()를 호출하여 토큰화
    encoded_result, encoded_labels = tokenizer.encode(input_data, label_data)
    return encoded_result, encoded_labels


def parse_csv_to_input_data(csv_path: str, subject_id_str, adm_str, processor) -> List[Tuple]:
    """
    CSV 파일을 input_data 형태로 변환 (pandas 벡터화 연산 사용)
    """
    df = pd.read_csv(csv_path / subject_id_str[:3] / subject_id_str / f'{adm_str}.csv')  #
    # /path/to/PFM_data/PFM_pretraining/addQ/test, 162/16228161.csv

    df['time'] = pd.to_datetime(df['charttime'], format='mixed')
    assert df['time'].is_monotonic_increasing, f"{csv_path}/{subject_id_str[:3]} / {subject_id_str} / {adm_str}.csv"

    # time을 문자열로 변환
    df['time'] = df['time'].astype(str)

    # print(df.columns)
    '''['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'itemname', 'value', 'valueuom', 'linksto', 'order', 'time']'''
    # --------------------------------------------------------------------------
    # 1. Parallel 실행
    # --------------------------------------------------------------------------
    # Parallel 결과는 원본 df의 index를 유지해야 정확한 비교가 가능합니다.
    df = processor.encode_parallel(df)

    out_path = (
            csv_path.parent.parent
            / f"processed_{processor.criteria_name}"
            / csv_path.parent.name
            / csv_path.name
            / subject_id_str[:3] / subject_id_str / f'{adm_str}.pkl'
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(out_path)

    # # 조건에 따라 value 변환 (완전 벡터화)
    # mask = df['itemid'].astype(int) > 1_000_000
    # df['converted_value'] = df['value'].astype(str)  # 먼저 모두 string으로
    # df.loc[~mask, 'converted_value'] = df.loc[~mask, 'value'].astype(float)  # 조건에 따라 float로
    """-> 위 코드가 이미 되어서 나옴 """


def find_split_position(sample: List[Tuple], max_length: int) -> int:
    """
    max_length를 넘지 않으면서 question 앞에서 자를 위치 찾기
    """
    if len(sample) <= max_length:
        return len(sample)

    # max_length 범위 내에서 마지막 question 찾기
    last_question_idx = -1
    find_question = False
    for i in range(max_length):
        if sample[(max_length - 1 - i)][1] == my_itemid['Question']['itemid']:
            find_question = True
            last_question_idx = max_length - 1 - i
        else:
            if find_question:
                break

    if last_question_idx == -1:
        # question이 없으면 max_length에서 자르기
        return max_length

    return last_question_idx


def split_sample_with_overlap(sample: np.array, label: np.array, max_length: int, overlap_size: int, subject_id_str, adm_str) -> List[
    np.array]:
    """
    긴 sample을 여러 개로 분할 (overlap 포함)
    """
    if len(sample) <= max_length:
        return [sample], [label]

    # 처음 3개의 meta 정보 추출
    meta_prefix = sample[:3]
    meta_label_prefix = label[:3]
    for idx in range(3):
        assert meta_prefix[idx, 1] <= 6, f'{meta_prefix} / {subject_id_str}, {adm_str} \n {sample}'

    splits = []
    splits_labels = []
    current_pos = 0

    while current_pos < len(sample):
        # 현재 위치에서 시작하는 부분 샘플
        if current_pos == 0:
            # 첫 번째 분할: 원본 그대로 시작
            remaining_sample = sample[current_pos:]
            remaining_label = label[current_pos:]
        else:
            # 이후 분할: meta prefix + overlap + 새로운 부분
            overlap_start = find_split_position(remaining_sample, max_length - overlap_size)
            assert 3 < overlap_start
            # If error happens/ this means too long ans sequence compair to max length

            remaining_sample = np.concatenate([meta_prefix, remaining_sample[overlap_start:]], axis=0)
            remaining_label = np.concatenate([meta_label_prefix, remaining_label[overlap_start:]], axis=0)

        if len(remaining_sample) <= max_length:
            # 마지막 분할
            splits.append(remaining_sample)
            splits_labels.append(remaining_label)
            break
        else:
            # 분할 위치 찾기
            split_pos = find_split_position(remaining_sample, max_length)
            assert 3 < split_pos
            # If error happens/ this means too long ans sequence compair to max length

            splits.append(remaining_sample[:split_pos])
            splits_labels.append(remaining_label[:split_pos])
            current_pos = split_pos

    return splits, splits_labels


def _list_csv_filenames(dst_dir):
    """
    dst_dir / *1 / *2 / adm*.csv 구조에서
    (*2, 파일명(csv 확장자 제거)) tuple 리스트 반환
    """
    filenames = []

    with os.scandir(dst_dir) as it1:
        for entry1 in it1:
            if not entry1.is_dir():
                continue  # *1

            with os.scandir(entry1.path) as it2:
                for entry2 in it2:
                    if not entry2.is_dir():
                        continue  # *2

                    group_name = entry2.name  # *2

                    with os.scandir(entry2.path) as file_it:
                        for f in file_it:
                            if (
                                f.is_file()
                                and f.name.startswith("adm")
                                and f.name.endswith(".csv")
                            ):
                                filename_wo_ext = os.path.splitext(f.name)[0]
                                filenames.append((group_name, filename_wo_ext))

    return filenames

def _add_dt_token_gen_label(df, folder_path, subject_id_str, adm_str, ethos, tokenizer, max_length, overlap_size, tokenize_split_path, raw):
    ###########################################################
    # 중복제거처리
    ###########################################################
    df['charttime'] = pd.to_datetime(df['charttime'], format='mixed', errors='coerce')
    df['subject_id'] = df['subject_id'].astype(int)
    #before = len(df)
    df = df.drop_duplicates(subset=['subject_id', 'charttime', 'itemid', 'value']).reset_index(drop=True)
    df_len = len(df)
    #print(f"Dropped rows: {before - df_len}")
    df_data = df

    ###########################################################
    # 유의미한 event 남은거 min_events개 미만이면 제거
    ###########################################################
    min_events = 20
    if len(df_data[df_data['itemid'].astype(int) < 1000000]) <= min_events:
        return None

    ###########################################################
    # Label 컬럼 정의
    ###########################################################
    common_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'hosp_hr', 'adm_hr']

    ihm_col_1 = ['ihm']
    dec_d_col_2 = ['decompensation_death']
    dec_d_col_3 = ['decompensation_arrest']
    icu_in_col_4 = ['icu_in']
    prog_days = [30, 90, 365]
    prog_col_5 = [f'readmission_{d}day' for d in prog_days] + [f'ohm_{d}day' for d in prog_days]
    los_col_6 = ['adm_los', 'icu_los']
    phe_col_7 = ['Acute and unspecified renal failure','Acute cerebrovascular disease','Acute myocardial infarction','Cardiac dysrhythmias','Chronic kidney disease',
                 'Chronic obstructive pulmonary disease and bronchiectasis','Complications of surgical procedures or medical care','Conduction disorders','Congestive heart failure; nonhypertensive','Coronary atherosclerosis and other heart disease',
                 'Diabetes mellitus with complications','Diabetes mellitus without complication','Disorders of lipid metabolism','Essential hypertension','Fluid and electrolyte disorders',
                 'Gastrointestinal hemorrhage','Hypertension with complications and secondary hypertension','Other liver diseases','Other lower respiratory disease','Other upper respiratory disease',
                 'Pleurisy; pneumothorax; pulmonary collapse','Pneumonia (except that caused by tuberculosis or sexually transmitted disease)','Respiratory failure; insufficiency; arrest (adult)','Septicemia (except in labor)','Shock']
    vaso_col_8 = ['vaso']
    huo_col_9 = ['oliguria', 'anuria']

    each_label_cols = (ihm_col_1 + dec_d_col_2 + dec_d_col_3 + icu_in_col_4 +
                       prog_col_5 + los_col_6 + phe_col_7 + vaso_col_8 + huo_col_9)

    ###########################################################
    # Label 데이터 로드
    ###########################################################
    df_ihm_1 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_ihm_{adm_str}.csv')
    df_dec_d_2 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_decompensation_death_{adm_str}.csv')
    df_dec_a_3 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_decompensation_arrest_{adm_str}.csv')
    df_icu_in_4 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_icu_in_{adm_str}.csv')
    df_prog_5 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_prognosis_{adm_str}.csv')
    df_los_6 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_los_{adm_str}.csv')
    df_phe_7 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_phenotype_{adm_str}.csv')
    df_vaso_8 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_vaso_{adm_str}.csv')
    df_huo_9 = pd.read_csv(folder_path / subject_id_str[:3] / subject_id_str / f'label_huo_{adm_str}.csv')

    ###########################################################
    # LOS (Length of Stay) Label 양자화 (Binning)
    ###########################################################
    # los_binning 함수의 조건에 맞춘 구간(bins)과 라벨(labels) 설정
    bins = [-np.inf, 24, 48, 72, 96, 120, 144, 168, 192, 336, np.inf]
    labels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    # 'adm_los'와 'icu_los' 컬럼에 대해 binning 적용 후 정수형(int)으로 변환
    for col in los_col_6:
        mask = df_los_6[col] == -100  # 원래 -100인 위치

        df_los_6.loc[~mask, col] = (
            pd.cut(
                df_los_6.loc[~mask, col],
                bins=bins,
                labels=labels
            )
            .astype(int)
        )

        # -100 복원 (사실상 안전장치)
        df_los_6.loc[mask, col] = -100

    ###########################################################
    # [STEP 1] Label 데이터 처리 및 병합
    ###########################################################
    label_dfs = [df_ihm_1, df_dec_d_2, df_dec_a_3, df_icu_in_4, df_prog_5, df_los_6, df_phe_7, df_vaso_8, df_huo_9]

    for l_df in label_dfs:
        l_df['charttime'] = pd.to_datetime(l_df['charttime'], format='mixed', errors='coerce')

    df_label_merged = reduce(lambda left, right: pd.merge(left, right, on=common_cols, how='outer'), label_dfs)
    df_label_merged[each_label_cols] = df_label_merged[each_label_cols].infer_objects(copy=False).fillna(-100)

    final_label_cols = common_cols + each_label_cols
    df_label_merged = df_label_merged[final_label_cols]
    df_label_merged = df_label_merged.sort_values(by='charttime').reset_index(drop=True)

    ###########################################################
    # [STEP 2] df_label_merged 및 df_data 병합 준비
    ###########################################################
    # df_label_merged: common_cols 중 'charttime' -> 'time' 변경, 나머지 drop, order에 -1 추가
    df_label_merged = df_label_merged.rename(columns={'charttime': 'time'})
    cols_to_drop = [c for c in common_cols if c != 'charttime']
    df_label_merged = df_label_merged.drop(columns=cols_to_drop)
    df_label_merged['order'] = -1  # df_data의 기존 order와 상호작용할 값

    # df_data: 기존 'order'는 그대로 유지
    df_data = df_data.drop(columns=['time']).rename(columns={'charttime': 'time'})
    df_data = df_data[['time', 'itemid', 'value', 'order']]

    ###########################################################
    # [STEP 3] 컬럼 맞추기 및 원래 순서 보존을 위한 index 추가
    ###########################################################
    # 기존 순서 보존을 위한 새로운 컬럼 'orig_idx' 생성
    df_data['orig_idx'] = range(len(df_data))
    # df_data의 인덱스 다음부터 시작하는 값으로 df_label_merged의 'orig_idx' 생성
    df_label_merged['orig_idx'] = range(len(df_data), len(df_data) + len(df_label_merged))

    target_cols = ['time', 'itemid', 'value', 'order', 'orig_idx'] + each_label_cols

    # df_data에 label 컬럼들 추가 및 -100으로 채우기
    for col in each_label_cols:
        df_data[col] = -100

    # df_label_merged에 itemid, value 추가
    df_label_merged['itemid'] = '2100000'
    df_label_merged['value'] = ''

    # 컬럼 순서 일치시키기
    df_data = df_data[target_cols]
    df_label_merged = df_label_merged[target_cols]

    # 데이터 병합
    data_label_merged = pd.concat([df_data, df_label_merged], ignore_index=True)

    ###########################################################
    # [STEP 4] 정렬 및 분리
    ###########################################################
    # 1. time (오름차순)
    # 2. order (내림차순) - 기존 order와 라벨(-1) 비교
    # 3. orig_idx (오름차순) - time과 order가 모두 같을 때 원래 순서 유지
    data_label_merged = data_label_merged.sort_values(
        by=['time', 'order', 'orig_idx'],
        ascending=[True, False, True]
    ).reset_index(drop=True)

    # 최종 DataFrames 분리
    df_data_dt = data_label_merged[['time', 'itemid', 'value']]
    df_label_dt = data_label_merged[each_label_cols]

    ###########################################################
    # [NEW] dt_label_counter_dict 생성 (-100 제외)
    ###########################################################
    dt_label_counter_dict = {}
    for col in each_label_cols:
        # 해당 컬럼에서 값이 -100이 아닌 것만 필터링
        valid_values = df_label_dt[df_label_dt[col] != -100][col]

        # value_counts()의 key(라벨 값)와 value(개수)를 모두 표준 int로 변환
        dt_label_counter_dict[col] = {
            int(k): int(v) for k, v in valid_values.value_counts().items()
        }

    ###########################################################
    # tokenization, ethos변환 (필요시), max_len이하로 분할, 패딩, 저장
    ###########################################################
    # 패딩용 기본값 설정
    padding_sample = np.array([0, 0, 0], dtype=int)
    padding_label = np.array([-100, ] * len(each_label_cols), dtype=int)

    # 리스트로 감싸기 & 튜플 리스트 변환
    df_data_dt['value'] = df_data_dt['value'].apply(lambda x: [x])
    one_sample = list(df_data_dt[['time', 'itemid', 'value']].itertuples(index=False, name=None))
    one_label = df_label_dt.to_numpy(dtype=int)

    encoded_sample, encoded_labels = encode_with_given_tokenizer(one_sample, one_label, tokenizer)

    if ethos:
        encoded_sample, encoded_labels = ethos_array_label(encoded_sample, encoded_labels, [-100, ] * len(each_label_cols))
        assert np.issubdtype(encoded_sample.dtype, np.integer), "encoded_sample dtype is not integer"
        assert np.issubdtype(encoded_labels.dtype, np.integer), "encoded_labels dtype is not integer"
    # 분할
    split_samples, split_labels = split_sample_with_overlap(encoded_sample, encoded_labels, max_length, overlap_size, subject_id_str, adm_str)

    # 각 분할된 샘플을 4096 크기로 패딩해서 추가
    for idx__, (split_sample, split_label) in enumerate(zip(split_samples, split_labels)):
        assert len(split_sample) == len(split_label)
        # 샘플 패딩
        if not raw:
            padded_sample = np.full((max_length, 3), padding_sample, dtype=int)
            actual_len = len(split_sample)
            padded_sample[:actual_len] = split_sample[:actual_len].astype(int)
        else:
            padded_sample = np.full((max_length, 3), padding_sample, dtype=float)
            actual_len = len(split_sample)
            padded_sample[:actual_len] = split_sample[:actual_len].astype(float)

        # 라벨 패딩
        padded_label = np.full((max_length, len(each_label_cols)), padding_label, dtype=np.int8)
        padded_label[:actual_len] = split_label[:actual_len].astype(np.int8)

        assert len(padded_sample) == len(padded_label)
        """
        Save
        나중에 processed_samples.append(np.expand_dims(padded_sample, axis=0)) 이렇게 합침
        """
        save_path = (tokenize_split_path / f"{subject_id_str[:3]}/{str(subject_id_str)}/{adm_str}/{idx__}.pkl")
        os.makedirs(save_path.parent, exist_ok=True)
        with open(save_path, "wb") as f:
            pickle.dump(padded_sample, f)

        label_save_path = (tokenize_split_path / f"{subject_id_str[:3]}/{str(subject_id_str)}/{adm_str}/{idx__}_label.pkl")
        os.makedirs(label_save_path.parent, exist_ok=True)
        with open(label_save_path, "wb") as f:
            pickle.dump(padded_label, f)

    return dt_label_counter_dict

def process_folder_to_dataset(folder_path: str, tokenizer, processor, max_length: int = 1000,
                              overlap_size: int = 50, basic_dir=None, dt_label_dir=None, addQ=True,
                              ethos=False, raw=False):
    """
    비병렬 버전
    """
    folder_path = Path(folder_path)  # /path/to/PFM_data/PFM_downstream/addQ/test
    csv_files = _list_csv_filenames(folder_path)  # ['16837862.csv', ...]
    csv_files.sort()
    num_files = len(csv_files)
    print(f"처리할 CSV 파일 수: {num_files}") # [('11622111', 'adm0'), ...]

    # 1단계: 모든 CSV를 input_data 형태로 변환
    print('1 Processing', end='')
    processed_path = (folder_path.parent.parent / f"processed_{processor.criteria_name}" / folder_path.parent.name / folder_path.name)
    # /path/to/PFM_data/PFM_downstream/f"processed_{processor.criteria_name}"/addQ/test
    if not os.path.exists(os.path.join(processed_path, "done.txt")):
        for idx, (subject_id_str, adm_str) in enumerate(csv_files):
            parse_csv_to_input_data(folder_path, subject_id_str, adm_str, processor)

        with open(os.path.join(processed_path, "done.txt"), "w") as f:
            f.write("done")
        print(' End')
    print('1 Processing - DONE')


    # 패딩용 기본값 설정
    padding_sample = np.array([0, 0, 0], dtype=int)

    # 각 라벨 컬럼(key)마다 Counter 객체를 생성하도록 설정
    dt_label_counter_dict_all = defaultdict(Counter)

    print('2 Processing', end='')
    tokenize_split_path = (folder_path.parent.parent / f"processed_{processor.criteria_name}" / "tokenized_splited" /
                           f"maxlen{max_length}_overlap{overlap_size}_processed_{processor.criteria_name}_share{0 if tokenizer.args.bin.startswith('bin') else tokenizer.args.share_tokens}_ethos{ethos}_{tokenizer.args.bin}" /
                           folder_path.parent.name / folder_path.name)

    for idx__, (subject_id_str, adm_str) in enumerate(csv_files):  # Parallelization point 2: processed_samples order must be preserved
        """
        확장자 pkl로 바꿔서 processed_path 에서 불러오기
        """
        subject_id = int(subject_id_str)
        pkl_path = (processed_path / subject_id_str[:3] / subject_id_str / f'{adm_str}.pkl')
        with open(pkl_path, "rb") as f:
            df = pickle.load(f)

        df_len = len(df)
        print(idx__, "-", df_len)

        result = _add_dt_token_gen_label(df, folder_path, subject_id_str, adm_str, ethos, tokenizer, max_length, overlap_size, tokenize_split_path, raw)

        if result is not None:
            for col, counts in result.items():
                # Counter.update()를 사용하면 키가 겹치는 경우 값(int)이 자동으로 더해집니다.
                dt_label_counter_dict_all[col].update(counts)

    print(' End')
    print('2 Processing - DONE')
    # =========================================================================
    # [추가된 부분] 누락되었던 dt_label_counter_dict_all 저장 로직
    # =========================================================================
    if len(dt_label_counter_dict_all) > 0:
        counter_save_path = tokenize_split_path / "dt_label_counter_all.pkl"
        with open(counter_save_path, "wb") as f:
            # defaultdict를 일반 dict로 변환 후 저장 (병렬 버전과 동일)
            pickle.dump(dict(dt_label_counter_dict_all), f)
        print(f"✅ dt_label_counter_dict_all 저장 완료: {counter_save_path}")
    # =========================================================================

    """
    정리해서 1000개씩 묶어서 dataset 만드는 코드
    """
    triplet_samples = _collect_subject_idx_triplets(tokenize_split_path)
    # subject_id / admission_idx / split_idx : triplet
    # 1. Triplet 정렬: subject_id -> adm_str -> split_idx 순서
    triplet_samples.sort(key=lambda x: (x[0], x[1], x[2]))
    num_samples = len(triplet_samples)
    batch_size = 1000
    num_batches = (num_samples + batch_size - 1) // batch_size  # 올림 계산
    print(f"Total samples: {num_samples}, Total batches: {num_batches}")

    # 2. Batch 단위로 순회
    for batch_idx in tqdm(range(num_batches), desc="Processing Batches"):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, num_samples)
        batch_triplets = triplet_samples[start_idx:end_idx]

        batch_samples = []
        batch_labels = []

        # 3. 개별 파일 로드
        for subject_id, adm_str, split_idx in batch_triplets:
            subject_id_str = str(subject_id)
            sub3 = subject_id_str[:3]

            # 경로 복원
            sample_path = tokenize_split_path / sub3 / subject_id_str / adm_str / f"{split_idx}.pkl"
            label_path = tokenize_split_path / sub3 / subject_id_str / adm_str / f"{split_idx}_label.pkl"

            # 데이터 로드
            with open(sample_path, "rb") as f:
                sample = pickle.load(f)
            with open(label_path, "rb") as f:
                label = pickle.load(f)

            batch_samples.append(sample)
            batch_labels.append(label)

        # 4. 차원 추가 및 Concat (np.stack 사용)
        # 개별 (max_len, 3) -> 합쳐서 (1000, max_len, 3) 형태로 변환됨
        stacked_samples = np.stack(batch_samples, axis=0)
        stacked_labels = np.stack(batch_labels, axis=0)

        # 5. 최종 배치 파일 저장 (0.pkl, 1.pkl ...)
        sample_save_path = basic_dir / f"{batch_idx}.pkl"
        label_save_path = dt_label_dir / f"{batch_idx}.pkl"

        with open(sample_save_path, "wb") as f:
            pickle.dump(stacked_samples, f)

        with open(label_save_path, "wb") as f:
            pickle.dump(stacked_labels, f)

    print("✅ All batched files saved successfully.")


""" ##Parallel## """
from multiprocess import Pool, current_process
import glob
from typing import List, Tuple
from tqdm import tqdm

# -------------------------------------------------------------------------
# Worker Function (병렬로 실행될 함수)
# -------------------------------------------------------------------------
def _collect_subject_idx_triplets(base_path: Path):
    """
    base_path/
      └── 123/
          └── 123456/ (subject_id)
              └── adm1/ (adm_str)
                  └── 0.pkl, 1.pkl, ... (split_idx)
    에서 (subject_id, adm_str, split_idx) triplet 수집
    """
    triplets = []

    # 1. sub3 폴더 탐색 (예: 123)
    for sub3 in base_path.iterdir():
        if not sub3.is_dir() or not sub3.name.isdigit() or len(sub3.name) != 3:
            continue

        # 2. subject_id 폴더 탐색 (예: 123456)
        for subject_dir in sub3.iterdir():
            if not subject_dir.is_dir() or not subject_dir.name.isdigit():
                continue

            subject_id = subject_dir.name

            # 3. adm_str 폴더 탐색 (예: adm1, adm2 ...)
            for adm_dir in subject_dir.iterdir():
                # 'adm'으로 시작하는 폴더만 필터링
                if not adm_dir.is_dir() or not adm_dir.name.startswith("adm"):
                    continue

                adm_str = adm_dir.name

                # 4. pkl 파일(split_idx) 탐색 (예: 0.pkl)
                for pkl in adm_dir.iterdir():
                    if pkl.suffix != ".pkl":
                        continue

                    # _label.pkl 등은 제외하고 순수 숫자 이름(0, 1, 2...)만 필터링
                    idx__ = pkl.stem
                    if not idx__.isdigit():
                        continue

                    # (int, str, int) 형태로 저장
                    triplets.append((int(subject_id), adm_str, int(idx__)))

    return triplets


def _parse_single_file(file_info):
    """
    Pool에서 호출하기 위해 단일 인자(tuple)를 받는 래퍼 함수입니다.
    """
    (subject_id_str, adm_str), folder_path, processor = file_info

    try:
        parse_csv_to_input_data(folder_path, subject_id_str, adm_str, processor)
    except Exception as e:
        print(f"Error processing {subject_id_str}, {adm_str}: {e}")
        return None  # 에러 발생 시 None 반환


# -------------------------------------------------------------------------
# Worker 2: Tokenization & Labeling (Phase 2)
# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
# Worker 2: Tokenization & Labeling (Phase 2)
# -------------------------------------------------------------------------
def _tokenization_worker(args):
    """
    개별 파일에 대해 Tokenization, TTE Labeling, Splitting을 수행하고,
    완료 시 자신의 PID를 파일명으로 하는 로그에 기록하는 워커
    """
    (subject_id_str, adm_str, processed_path, folder_path, ethos,
     tokenizer, max_length, overlap_size, tokenize_split_path, logs_dir, raw) = args  # logs_dir 추가

    subject_id = int(subject_id_str)
    pkl_path = (processed_path / subject_id_str[:3] / subject_id_str / f'{adm_str}.pkl')

    try:
        with open(pkl_path, "rb") as f:
            df = pickle.load(f)

        result_counter = _add_dt_token_gen_label(
            df, folder_path, subject_id_str, adm_str, ethos,
            tokenizer, max_length, overlap_size, tokenize_split_path, raw
        )

        del df
        gc.collect()

        # =========================================================
        # [사용자 제안 반영] PID 기반 로그 작성 (Lock 없이 병렬 I/O)
        # =========================================================
        pid = current_process().pid
        log_file_path = os.path.join(logs_dir, f"done_{pid}.txt")
        with open(log_file_path, "a") as f:
            f.write(f"{subject_id_str}_{adm_str}\n")

        return (subject_id_str, adm_str, result_counter, True)
    except Exception as e:
        print(f"Error in tokenization {subject_id_str}, {adm_str}: {e}")
        return (subject_id_str, adm_str, None, False)


# -------------------------------------------------------------------------
# Worker 3: Batch Stacking & Saving (Phase 3)
# -------------------------------------------------------------------------
def _batch_worker(args):
    """
    1000개의 split된 pkl 파일을 읽어 하나의 tensor(numpy) 파일로 병합하는 워커
    """
    batch_idx, batch_triplets, tokenize_split_path, basic_dir, dt_label_dir = args

    batch_samples = []
    batch_labels = []

    if True:
        # 개별 split 파일 로드
        for subject_id, adm_str, split_idx in batch_triplets:
            subject_id_str = str(subject_id)
            sub3 = subject_id_str[:3]

            sample_path = tokenize_split_path / sub3 / subject_id_str / adm_str / f"{split_idx}.pkl"
            label_path = tokenize_split_path / sub3 / subject_id_str / adm_str / f"{split_idx}_label.pkl"

            with open(sample_path, "rb") as f:
                batch_samples.append(pickle.load(f))
            with open(label_path, "rb") as f:
                batch_labels.append(pickle.load(f))

        # 차원 추가 및 Concat (np.stack)
        stacked_samples = np.stack(batch_samples, axis=0)
        stacked_labels = np.stack(batch_labels, axis=0)

        # 저장 경로 생성 및 파일 저장
        basic_dir = Path(basic_dir)
        dt_label_dir = Path(dt_label_dir)
        sample_save_path = basic_dir / f"{batch_idx}.pkl"
        label_save_path = dt_label_dir / f"{batch_idx}.pkl"

        os.makedirs(sample_save_path.parent, exist_ok=True)
        os.makedirs(label_save_path.parent, exist_ok=True)

        with open(sample_save_path, "wb") as f:
            pickle.dump(stacked_samples, f)
        with open(label_save_path, "wb") as f:
            pickle.dump(stacked_labels, f)

        return (batch_idx, True)
    # except Exception as e:
    #     print(f"Error in batch {batch_idx}: {e}")
    #     return (batch_idx, False)


# -------------------------------------------------------------------------
# Main Function
# -------------------------------------------------------------------------
def process_folder_to_dataset_parallel(folder_path: str, tokenizer, processor,
                                       max_length: int = 1000,
                                       overlap_size: int = 50, basic_dir=None, dt_label_dir=None,
                                       addQ=True,
                                       ethos=False, raw=False):
    # (선택사항) 토크나이저 내부 병렬화와 충돌 방지를 위해 환경변수 설정
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    folder_path = Path(folder_path)
    csv_files = _list_csv_filenames(folder_path)
    csv_files.sort()
    num_files = len(csv_files)
    num_cores = 40  # args.sample_n_workers 등 외부 변수와 연동 권장

    processed_path = (folder_path.parent.parent / f"processed_{processor.criteria_name}" / folder_path.parent.name / folder_path.name)

    # --------------------------------------------------------------------------
    # [Phase 1: CSV Parsing] (작성해주신 부분)
    # --------------------------------------------------------------------------
    print('1 Processing with Parallelism...')
    if not os.path.exists(os.path.join(processed_path, "done.txt")):
        tasks_1 = [(csv_file, folder_path, processor) for csv_file in csv_files]
        with Pool(processes=num_cores) as pool:
            list(tqdm(pool.imap_unordered(_parse_single_file, tasks_1), total=num_files, desc="Phase 1: Parsing"))

        with open(os.path.join(processed_path, "done.txt"), "w") as f:
            f.write("done")
    else:
        print('Phase 1 Loaded (already done)')

    # --------------------------------------------------------------------------
    # [Phase 2: Tokenization & TTE Labeling]
    # --------------------------------------------------------------------------
    tokenize_split_path = (folder_path.parent.parent / f"processed_{processor.criteria_name}" / "tokenized_splited" /
                           f"maxlen{max_length}_overlap{overlap_size}_processed_{processor.criteria_name}_share{0 if tokenizer.args.bin.startswith('bin') else tokenizer.args.share_tokens}_ethos{ethos}_{tokenizer.args.bin}" /
                           folder_path.parent.name / folder_path.name)

    logs_dir = tokenize_split_path / "process_logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Resume Logic: 이미 처리된 파일 확인
    done_files = set()
    log_files = glob.glob(os.path.join(logs_dir, "done_*.txt"))
    for log_file in log_files:
        with open(log_file, "r") as f:
            for line in f:
                done_files.add(line.strip())

    files_to_process = [f for f in csv_files if f"{f[0]}_{f[1]}" not in done_files]
    print(f"Phase 2: 이미 처리된 파일: {len(done_files)}, 남은 파일: {len(files_to_process)}")

    # 각 라벨 컬럼마다 카운터를 합치기 위한 전역 Dict
    dt_label_counter_dict_all = defaultdict(Counter)

    if len(files_to_process) > 0:
        tasks_2 = [(subject_id_str, adm_str, processed_path, folder_path, ethos,
                    tokenizer, max_length, overlap_size, tokenize_split_path, logs_dir, raw)
                   for subject_id_str, adm_str in files_to_process]

        print('2 Processing with Parallelism...')
        with Pool(processes=num_cores) as pool:
            # ✅ 메인 프로세스는 로그를 쓰지 않고 카운터 합치기(Reduce)만 수행 (안전함)
            for result in tqdm(pool.imap_unordered(_tokenization_worker, tasks_2), total=len(tasks_2),
                               desc="Phase 2: Tokenizing"):
                sub_str, adm_str, counter_result, success = result

                if success and counter_result is not None:
                    for col, counts in counter_result.items():
                        dt_label_counter_dict_all[col].update(counts)
    else:
        print('Phase 2 Tokenization & TTE labeling already done')
    # =========================================================================
    # [추가] dt_label_counter_dict_all 저장
    # =========================================================================
    if len(dt_label_counter_dict_all) > 0:
        counter_save_path = tokenize_split_path / "dt_label_counter_all.pkl"
        with open(counter_save_path, "wb") as f:
            # defaultdict를 일반 dict로 변환 후 저장
            pickle.dump(dict(dt_label_counter_dict_all), f)
        print(f"✅ dt_label_counter_dict_all 저장 완료: {counter_save_path}")
    # =========================================================================

    # [검증] 빠진 파일이 있는지 확인
    done_files = set()
    log_files = glob.glob(os.path.join(logs_dir, "done_*.txt"))
    for log_file in log_files:
        with open(log_file, "r") as f:
            for line in f:
                done_files.add(line.strip())

    files_to_process = [f for f in csv_files if f"{f[0]}_{f[1]}" not in done_files]
    if len(files_to_process) > 0:
        raise Exception(f"오류: 코드를 돌렸는데도 처리 안된 파일이 {len(files_to_process)}개 남았습니다.")

    # --------------------------------------------------------------------------
    # [Phase 3: Batch Stacking & Save]
    # I/O Bound 작업이므로 Batch 단위로 병렬화
    # --------------------------------------------------------------------------
    print('3 Batching with Parallelism...')

    triplet_samples = _collect_subject_idx_triplets(tokenize_split_path)
    triplet_samples.sort(key=lambda x: (x[0], x[1], x[2]))
    num_samples = len(triplet_samples)
    batch_size = 1000
    num_batches = (num_samples + batch_size - 1) // batch_size
    print(f"Total samples: {num_samples}, Total batches: {num_batches}")

    # 배치 태스크 생성 (batch_idx, batch에 속한 1000개의 triplet list, ...)
    tasks_3 = []
    for batch_idx in range(num_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, num_samples)
        batch_triplets = triplet_samples[start_idx:end_idx]
        tasks_3.append((batch_idx, batch_triplets, tokenize_split_path, basic_dir, dt_label_dir))

    # 병렬 저장 실행 (I/O 부하를 고려하여 코어 수를 절반 정도로 조절할 수도 있음)
    with Pool(processes=num_cores) as pool:
        results = list(
            tqdm(pool.imap_unordered(_batch_worker, tasks_3), total=num_batches, desc="Phase 3: Saving Batches"))

    # 검증
    failed_batches = [res[0] for res in results if not res[1]]
    if failed_batches:
        raise Exception(f"배치 저장 실패 발생: {failed_batches}")

    print("✅ All batched files saved successfully in parallel.")



def csv_to_tensor_dt(folder_path: str, tokenizer, processor, max_length: int = 1000,
                     overlap_size: int = 50,
                     basic_dir=None, dt_label_dir=None, n_workers: int = None, addQ=True,
                     ethos=False, raw=False):
    """basic_dir / dt_label_dir: "/path/to/PFM_data/PFM_downstream/tensor_dt_saved/~~/~~: 저장할 경로")"""
    # 타입별 정보 출력
    if basic_dir is not None:
        print(os.path.dirname(os.path.dirname(basic_dir)) + '/tokenizer.txt')
        with open(os.path.dirname(os.path.dirname(basic_dir)) + '/tokenizer.txt', 'w', encoding='utf-8') as f:
            print("\n=== Tokenizer 설명 ===")
            type_info = tokenizer.get_type_info()
            for data_type, info in type_info.items():
                if data_type != 'total_vocab_size' and data_type != 'tokenizer_ranges':
                    print(
                        f"{data_type}: idx={info['tokenizer_idx']}, vocab_size={info['vocab_size']}, offset={info['token_offset']}, type={info['type']}")
                    f.write(
                        f"{data_type}: idx={info['tokenizer_idx']}, vocab_size={info['vocab_size']}, offset={info['token_offset']}, type={info['type']}" + '\n')
            print(f"Total vocabulary size: {type_info['total_vocab_size']}")
            print(f"Total tokenizer_ranges: {type_info['tokenizer_ranges']}")
            f.write(f"Total vocabulary size: {type_info['total_vocab_size']}" + '\n')
            f.write(f"Total tokenizer_ranges: {type_info['tokenizer_ranges']}")

    print("=== Dataset Tensor 생성 시작 ===")
    start = time.time()

    if (n_workers is None) or (n_workers == 1):
        """
        기존 비병렬 버전 (호환성 유지)
        """
        print("=> 비병렬 버전")
        process_folder_to_dataset(folder_path, tokenizer, processor, max_length, overlap_size,
                                  basic_dir, dt_label_dir, addQ, ethos, raw)
    else:
        process_folder_to_dataset_parallel(folder_path, tokenizer, processor, max_length, overlap_size,
                                           basic_dir, dt_label_dir, addQ, ethos, raw)

    basic_dir = Path(basic_dir)
    with open(basic_dir.parent / f'{basic_dir.name}_done.txt', 'w', encoding='utf-8') as f:
        f.write('done')

    end = time.time()
    print(f"\n=== 결과 ===")

    print(f"  - 총 처리 시간: {(end - start) / 3600:.2f} 시간")
    print(f"  - 사용된 워커 수: {n_workers}")

    return True


# 사용 예시
if __name__ == "__main__":
    from pfm_mimic4.tokenizer.multitype_tokenizer import MultiTypeTokenizer
    from pfm_mimic4.tokenizer.tokenizing_setting import token_bin_range
    from mimic4preprocessing.key_value_unit_processer import key_value_unit_processer

    import argparse

    _DR = os.environ.get("PFM_DATA_ROOT", "/path/to/PFM_data")
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample_max_length", type=int, default=2048)
    parser.add_argument("--sample_overlap", type=int, default=512)
    parser.add_argument("--sample_n_workers", type=int, default=16)
    parser.add_argument("--data_dir", type=str, default=os.path.join(_DR, "PFM_pretraining", "tensor_saved") + os.sep)
    parser.add_argument("--qa_table_dir", type=str, default=os.path.join(_DR, "PFM_pretraining") + os.sep)
    parser.add_argument("--binning_threshold", type=str, default="mimic4preprocessing/unit_value_cleaning/data/")
    parser.add_argument("--tte_threshold", type=str, default="mimic4preprocessing/unit_value_cleaning/data/for_tte/edge-[0.01, 0.05].pkl")
    parser.add_argument("--data", type=str, default='criteria1', help='criteria is in - mimic4preprocessing/scripts/inclusion_criteria')
    parser.add_argument("--bin", type=str, default='bin10_exp0.5_th10',
                        help='value binning; thresholds live in mimic4preprocessing/unit_value_cleaning/data/ (generated by mimic4preprocessing/unit_value_cleaning/binning/make_bin.py). bin{N}_exp{E}_th{T} = N percentile bins, density-weight exponent E (exp0 = no weighting), weight-clip threshold T. Used: bin10_exp1_th10 [OURS], bin10_exp0_th10 [ETHOS generation baseline]. Also generated: bin10_exp{0.5,1.5,2}_th10.')
    parser.add_argument("--share_tokens", type=int, default=0, help='0 - not share token; use each bin'
                                                                    '1 - share token')
    parser.add_argument("--seq_gen", type=str, default='NOadd',
                        help='addQ - add info token with timestamp and '
                             'addTS - share token'
                             'NOadd - no adding info token')
    parser.add_argument("--objective", type=str, default='G2DYDTSP',
                        help='G1DYDTSP - Generative multi-timw dynamic mono TimeStamp P'
                             'G2DYDTSP - G1 with position'
                             'GSDYDTSP - Generative simple dynamic mono TimeStamp P'
                             'DYMTSP - dynamic mono TimeStamp P'
                             'DYDTSP - dynamic dual TimeStamp P'
                             'TANTP - time-aware NTP'
                             'NTP - remove timestamp'
                             'TTE - time to event')
    parser.add_argument("--in_pretrain", type=int, default=1)
    parser.add_argument("--eval_seed", type=int, default=0)
    parser.add_argument("--eval_max_length", type=int, default=2048)
    parser.add_argument("--eval_overlap", type=int, default=512)

    parser.add_argument("--eval_task_dir", type=str, default=os.path.join(_DR, "PFM_downstream") + os.sep)
    parser.add_argument("--eval_data_dir", type=str, default=os.path.join(_DR, "PFM_downstream", "tensor_dt_saved") + os.sep)

    parser.add_argument("--pe_baseline", type=str, default=None, help='None - OURS (default). ETHOS - generation-comparison baseline.')
    args = parser.parse_args()
    processor = key_value_unit_processer(args.data)

    config = token_bin_range(args, processor.inclusion_dict_processed)
    tokenizer = MultiTypeTokenizer(config, args)

    def QA_dataset(args, tokenizer, processor, is_train):
        load_share_token = 0 if args.bin.startswith('bin') else args.share_tokens
        load_seq_gen = 'addQ' if args.seq_gen in ['addQ', 'addTS'] else 'NOadd'

        dataset_setting_dir = f'/max_len_{args.eval_max_length}_overlap_{args.eval_overlap}/' \
                              f'feature{args.data}_{args.bin}_share{load_share_token}_{load_seq_gen}{"_ETHOS" if args.pe_baseline == "ETHOS" else ""}/'

        dt_label_dir = args.eval_data_dir + dataset_setting_dir + f'dt_{"train" if is_train else "test"}/'
        ntp_dir = args.eval_data_dir + dataset_setting_dir + f'{"train" if is_train else "test"}/'

        os.makedirs(ntp_dir, exist_ok=True)

        csv_to_tensor_dt(f'{args.eval_task_dir}/{args.seq_gen}/{"train" if is_train else "test"}/',
                         tokenizer, processor, max_length=args.eval_max_length, overlap_size=args.eval_overlap, 
                         basic_dir=ntp_dir, dt_label_dir=dt_label_dir,
                         n_workers=args.sample_n_workers, addQ=load_seq_gen == 'addQ',
                         ethos=args.pe_baseline == 'ETHOS', raw=args.bin.startswith('raw'))


    val_dataset = QA_dataset(args, tokenizer, processor, is_train=False)


