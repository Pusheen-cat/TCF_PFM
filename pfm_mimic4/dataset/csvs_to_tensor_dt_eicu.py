import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple
# from prepocessing.mimic3.lab_unit_numeric_matching.itemid_reference_range import reference_range_dict
import pickle
import gc
import os
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


def parse_csv_to_input_data(csv_dir_path: str, target_csv: str, subject_id_str, unit_id_str, processor, processed_path):
    """
    CSV 파일을 input_data 형태로 변환 (pandas 벡터화 연산 사용)
    """
    '''['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'itemname', 'value', 'valueuom', 'linksto', 'order', 'time']'''
    csv_path = os.path.join(csv_dir_path, target_csv)
    df = pd.read_csv(csv_path)

    df['charttime'] = pd.to_datetime(df['charttime'], format='mixed').dt.floor('min')
    df['time'] = df['charttime']

    # time은 오름차순, order는 내림차순
    df = df.sort_values(by=['time', 'order'], ascending=[True, False]).reset_index(drop=True)

    df['time'] = df['time'].astype(str)

    df = processor.encode_parallel(df, linksto_strict=False)

    # 출력 경로 설정 (processed_path 하위)
    out_path = Path(processed_path) / subject_id_str[:3] / subject_id_str / f'{unit_id_str}.pkl'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(out_path)


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


def _list_csv_filenames(input_dir, addQ=True):
    """
    input_dir: root_path/A_raw_data_colloection/test
    반환: [(subject_id_str, unit_id_str, csv_dir_path), ...]
    """
    filenames = []
    target_csv = "events_addQ.csv" if addQ else "events.csv"

    with os.scandir(input_dir) as it1:
        for entry1 in it1:
            if not entry1.is_dir(): continue

            with os.scandir(entry1.path) as it2:
                for entry2 in it2:
                    if not entry2.is_dir(): continue

                    # *1과 *2를 결합하여 subject_id 생성
                    subject_id_str = entry1.name + entry2.name

                    with os.scandir(entry2.path) as it3:
                        for entry3 in it3:
                            if not entry3.is_dir(): continue

                            unit_id_str = entry3.name
                            csv_path = os.path.join(entry3.path, target_csv)

                            if os.path.exists(csv_path):
                                filenames.append((subject_id_str, unit_id_str, entry3.path))

    return filenames


def _add_dt_token_gen_label(df, csv_dir_path, subject_id_str, unit_id_str, ethos, tokenizer, max_length, overlap_size,
                            tokenize_split_path, raw):
    df['charttime'] = pd.to_datetime(df['charttime'], format='mixed', errors='coerce')
    df['subject_id'] = df['subject_id'].astype(int)
    df = df.drop_duplicates(subset=['subject_id', 'charttime', 'itemid', 'value']).reset_index(drop=True)
    df_data = df

    min_events = 20
    if len(df_data[df_data['itemid'].astype(int) < 1000000]) <= min_events:
        return None

    # 라벨 컬럼 정의 (기존 배열 유지하되 mortality만 실제 데이터 사용)
    common_cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'stay', 'adm_hr', 'icu_hr']
    each_label_cols = (['ihm'] + ['decompensation_death'] + ['decompensation_arrest'] + ['icu_in'] +
                       [f'readmission_{d}day' for d in [30, 90, 365]] + [f'ohm_{d}day' for d in [30, 90, 365]] +
                       ['adm_los', 'icu_los'] +
                       ['Acute and unspecified renal failure', 'Acute cerebrovascular disease',
                        'Acute myocardial infarction', 'Cardiac dysrhythmias', 'Chronic kidney disease',
                        'Chronic obstructive pulmonary disease and bronchiectasis',
                        'Complications of surgical procedures or medical care', 'Conduction disorders',
                        'Congestive heart failure; nonhypertensive', 'Coronary atherosclerosis and other heart disease',
                        'Diabetes mellitus with complications', 'Diabetes mellitus without complication',
                        'Disorders of lipid metabolism', 'Essential hypertension', 'Fluid and electrolyte disorders',
                        'Gastrointestinal hemorrhage', 'Hypertension with complications and secondary hypertension',
                        'Other liver diseases', 'Other lower respiratory disease', 'Other upper respiratory disease',
                        'Pleurisy; pneumothorax; pulmonary collapse',
                        'Pneumonia (except that caused by tuberculosis or sexually transmitted disease)',
                        'Respiratory failure; insufficiency; arrest (adult)', 'Septicemia (except in labor)', 'Shock'] +
                       ['vaso'] + ['oliguria', 'anuria'])

    # 단일 라벨 파일 로드 및 검증
    label_path = Path(csv_dir_path) / 'label_mortality.csv'
    if not label_path.exists():
        raise f"{label_path} - No exist"
        return None

    df_ihm_1 = pd.read_csv(label_path)
    # df_ihm_1의 icum col을 decompensation_death col로 이름 바꾸고 맨 뒤로 보내
    # icum → decompensation_death 로 이름 변경
    df_ihm_1 = df_ihm_1.rename(columns={'icum': 'decompensation_death'})
    # 해당 컬럼을 맨 뒤로 이동
    col = 'decompensation_death'
    df_ihm_1 = df_ihm_1[[c for c in df_ihm_1.columns if c != col] + [col]]

    # 데이터가 1줄도 없으면(헤더만 존재하면) None 반환하여 건너뜀
    if df_ihm_1.empty:
        return None

    df_ihm_1['charttime'] = pd.to_datetime(df_ihm_1['charttime'], format='mixed', errors='coerce')

    # 병합용 df 준비 (다른 컬럼들은 모두 -100 처리)
    df_label_merged = df_ihm_1.copy()
    for col in each_label_cols:
        if col not in df_label_merged.columns:
            df_label_merged[col] = -100

    df_label_merged[each_label_cols] = df_label_merged[each_label_cols].infer_objects(copy=False).fillna(-100)
    final_label_cols = common_cols + each_label_cols

    # 없는 common_cols 에러 방지 (필요 시 조정)
    for col in common_cols:
        if col not in df_label_merged.columns:
            df_label_merged[col] = -100

    df_label_merged = df_label_merged[final_label_cols]
    df_label_merged = df_label_merged.sort_values(by='charttime').reset_index(drop=True)

    # [STEP 2~4] 병합 및 정렬 (기존과 동일하므로 adm_str 변수명만 변경)
    df_label_merged = df_label_merged.rename(columns={'charttime': 'time'})
    cols_to_drop = [c for c in common_cols if c != 'charttime']
    df_label_merged = df_label_merged.drop(columns=cols_to_drop)
    df_label_merged['order'] = -1

    df_data = df_data.drop(columns=['time']).rename(columns={'charttime': 'time'})
    df_data = df_data[['time', 'itemid', 'value', 'order']]

    df_data['orig_idx'] = range(len(df_data))
    df_label_merged['orig_idx'] = range(len(df_data), len(df_data) + len(df_label_merged))

    target_cols = ['time', 'itemid', 'value', 'order', 'orig_idx'] + each_label_cols
    for col in each_label_cols: df_data[col] = -100
    df_label_merged['itemid'] = '2100000'
    df_label_merged['value'] = ''

    df_data = df_data[target_cols]
    df_label_merged = df_label_merged[target_cols]
    data_label_merged = pd.concat([df_data, df_label_merged], ignore_index=True)

    data_label_merged = data_label_merged.sort_values(
        by=['time', 'order', 'orig_idx'], ascending=[True, False, True]
    ).reset_index(drop=True)

    df_data_dt = data_label_merged[['time', 'itemid', 'value']]
    df_label_dt = data_label_merged[each_label_cols]

    dt_label_counter_dict = {}
    for col in each_label_cols:
        valid_values = df_label_dt[df_label_dt[col] != -100][col]
        dt_label_counter_dict[col] = {int(k): int(v) for k, v in valid_values.value_counts().items()}

    # 패딩용 기본값 설정
    padding_sample = np.array([0, 0, 0], dtype=int)
    padding_label = np.array([-100, ] * len(each_label_cols), dtype=int)

    df_data_dt['value'] = df_data_dt['value'].apply(lambda x: [x])
    df_data_dt['itemid'] = df_data_dt['itemid'].astype(str)
    one_sample = list(df_data_dt[['time', 'itemid', 'value']].itertuples(index=False, name=None))
    one_label = df_label_dt.to_numpy(dtype=int)

    encoded_sample, encoded_labels = encode_with_given_tokenizer(one_sample, one_label, tokenizer)

    if ethos:
        encoded_sample, encoded_labels = ethos_array_label(encoded_sample, encoded_labels,
                                                           [-100, ] * len(each_label_cols))

    split_samples, split_labels = split_sample_with_overlap(encoded_sample, encoded_labels, max_length, overlap_size,
                                                            subject_id_str, unit_id_str)

    for idx__, (split_sample, split_label) in enumerate(zip(split_samples, split_labels)):
        if not raw:
            padded_sample = np.full((max_length, 3), padding_sample, dtype=int)
            actual_len = len(split_sample)
            padded_sample[:actual_len] = split_sample[:actual_len].astype(int)
        else:
            padded_sample = np.full((max_length, 3), padding_sample, dtype=float)
            actual_len = len(split_sample)
            padded_sample[:actual_len] = split_sample[:actual_len].astype(float)

        padded_label = np.full((max_length, len(each_label_cols)), padding_label, dtype=np.int8)
        padded_label[:actual_len] = split_label[:actual_len].astype(np.int8)

        # unit_id_str 로 저장
        save_path = (tokenize_split_path / f"{subject_id_str[:3]}/{subject_id_str}/{unit_id_str}/{idx__}.pkl")
        os.makedirs(save_path.parent, exist_ok=True)
        with open(save_path, "wb") as f:
            pickle.dump(padded_sample, f)

        label_save_path = (
                    tokenize_split_path / f"{subject_id_str[:3]}/{subject_id_str}/{unit_id_str}/{idx__}_label.pkl")
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
    # 경로 계산
    folder_path = Path(folder_path)  # root_path/A_raw_data_colloection/test
    split_str = folder_path.name  # 'test' 또는 'train'
    root_path = folder_path.parent.parent  # root_path

    addQ_str = "addQ" if addQ else "NOadd"
    target_csv = "events_addQ.csv" if addQ else "events.csv"

    csv_files = _list_csv_filenames(folder_path, addQ=addQ)
    csv_files.sort()
    num_files = len(csv_files)
    print(f"처리할 파일 수: {num_files}")

    processed_path = root_path / "PFM_downstream" / f"processed_{processor.criteria_name}" / addQ_str / split_str

    # 1단계
    print('1 Processing', end='')
    if not os.path.exists(os.path.join(processed_path, "done.txt")):
        for idx, (subject_id_str, unit_id_str, csv_dir_path) in enumerate(csv_files):
            parse_csv_to_input_data(csv_dir_path, target_csv, subject_id_str, unit_id_str, processor, processed_path)

        with open(os.path.join(processed_path, "done.txt"), "w") as f:
            f.write("done")
        print(' End')
    print('1 Processing - DONE')

    dt_label_counter_dict_all = defaultdict(Counter)

    print('2 Processing', end='')
    tokenize_split_path = root_path / "PFM_downstream" / "tokenized_splited" / \
                          f"maxlen{max_length}_overlap{overlap_size}_processed_{processor.criteria_name}_share{0 if tokenizer.args.bin.startswith('bin') else tokenizer.args.share_tokens}_ethos{ethos}_{tokenizer.args.bin}" / \
                          addQ_str / split_str

    # 2단계
    for idx__, (subject_id_str, unit_id_str, csv_dir_path) in enumerate(csv_files):
        pkl_path = processed_path / subject_id_str[:3] / subject_id_str / f'{unit_id_str}.pkl'

        # 파일이 비어 건너뛰었거나 오류로 없는 경우 예외 처리
        if not pkl_path.exists(): continue

        with open(pkl_path, "rb") as f:
            df = pickle.load(f)

        print(idx__, "-", len(df))
        result = _add_dt_token_gen_label(df, csv_dir_path, subject_id_str, unit_id_str, ethos, tokenizer, max_length,
                                         overlap_size, tokenize_split_path, raw)

        if result is not None:
            for col, counts in result.items():
                dt_label_counter_dict_all[col].update(counts)

    # 앞서 추가 요청하신 카운터 딕셔너리 저장 로직
    if len(dt_label_counter_dict_all) > 0:
        counter_save_path = tokenize_split_path / "dt_label_counter_all.pkl"
        os.makedirs(counter_save_path.parent, exist_ok=True)
        with open(counter_save_path, "wb") as f:
            pickle.dump(dict(dt_label_counter_dict_all), f)
        print(f"\n✅ dt_label_counter_dict_all 저장 완료: {counter_save_path}")

    # 3단계 (Triplet 수집 및 배치)
    triplet_samples = _collect_subject_idx_triplets(tokenize_split_path)
    triplet_samples.sort(key=lambda x: (x[0], x[1], x[2]))
    num_samples = len(triplet_samples)
    batch_size = 1000
    num_batches = (num_samples + batch_size - 1) // batch_size
    print(f"Total samples: {num_samples}, Total batches: {num_batches}")

    for batch_idx in tqdm(range(num_batches), desc="Processing Batches"):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, num_samples)
        batch_triplets = triplet_samples[start_idx:end_idx]

        batch_samples, batch_labels = [], []

        for subject_id, unit_id_str, split_idx in batch_triplets:
            subject_id_str = str(subject_id)
            sub3 = subject_id_str[:3]

            sample_path = tokenize_split_path / sub3 / subject_id_str / unit_id_str / f"{split_idx}.pkl"
            label_path = tokenize_split_path / sub3 / subject_id_str / unit_id_str / f"{split_idx}_label.pkl"

            with open(sample_path, "rb") as f: batch_samples.append(pickle.load(f))
            with open(label_path, "rb") as f: batch_labels.append(pickle.load(f))

        stacked_samples = np.stack(batch_samples, axis=0)
        stacked_labels = np.stack(batch_labels, axis=0)

        sample_save_path = Path(basic_dir) / f"{batch_idx}.pkl"
        label_save_path = Path(dt_label_dir) / f"{batch_idx}.pkl"

        os.makedirs(sample_save_path.parent, exist_ok=True)
        os.makedirs(label_save_path.parent, exist_ok=True)

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
    triplets = []
    for sub3 in base_path.iterdir():
        if not sub3.is_dir() or not sub3.name.isdigit() or len(sub3.name) != 3: continue
        for subject_dir in sub3.iterdir():
            if not subject_dir.is_dir() or not subject_dir.name.isdigit(): continue
            subject_id = subject_dir.name

            # adm 기반이 아닌 일반 디렉토리(unit_id) 순회로 변경
            for unit_dir in subject_dir.iterdir():
                if not unit_dir.is_dir(): continue
                unit_id_str = unit_dir.name
                for pkl in unit_dir.iterdir():
                    if pkl.suffix != ".pkl": continue
                    idx__ = pkl.stem
                    if not idx__.isdigit(): continue
                    triplets.append((int(subject_id), unit_id_str, int(idx__)))
    return triplets


# -------------------------------------------------------------------------
# [FIX 1] _parse_single_file
#   - file_info 언패킹: (subject_id_str, unit_id_str, csv_dir_path) 3-tuple 사용
#   - parse_csv_to_input_data에 target_csv, processed_path 추가 전달
# -------------------------------------------------------------------------
def _parse_single_file(file_info):
    """
    Pool에서 호출하기 위해 단일 인자(tuple)를 받는 래퍼 함수입니다.
    """
    (subject_id_str, unit_id_str, csv_dir_path), target_csv, processor, processed_path = file_info

    try:
        parse_csv_to_input_data(csv_dir_path, target_csv, subject_id_str, unit_id_str, processor, processed_path)
    except Exception as e:
        print(f"Error processing {subject_id_str}, {unit_id_str}: {e}")
        return None  # 에러 발생 시 None 반환


# -------------------------------------------------------------------------
# Worker 2: Tokenization & Labeling (Phase 2)
# -------------------------------------------------------------------------
def _tokenization_worker(args):
    """
    개별 파일에 대해 Tokenization, TTE Labeling, Splitting을 수행하고,
    완료 시 자신의 PID를 파일명으로 하는 로그에 기록하는 워커
    """
    (subject_id_str, unit_id_str, processed_path, csv_dir_path, ethos,
     tokenizer, max_length, overlap_size, tokenize_split_path, logs_dir, raw) = args
    pkl_path = (processed_path / subject_id_str[:3] / subject_id_str / f'{unit_id_str}.pkl')
    pid = current_process().pid

    try:
        with open(pkl_path, "rb") as f:
            df = pickle.load(f)
        result_counter = _add_dt_token_gen_label(
            df, csv_dir_path, subject_id_str, unit_id_str, ethos,
            tokenizer, max_length, overlap_size, tokenize_split_path, raw
        )
        del df
        gc.collect()

        log_file_path = os.path.join(logs_dir, f"done_{pid}.txt")
        with open(log_file_path, "a") as f:
            f.write(f"{subject_id_str}_{unit_id_str}\n")

        return (subject_id_str, unit_id_str, result_counter, True)

    except Exception as e:
        print(f"Error in tokenization {subject_id_str}, {unit_id_str}: {e}")

        # 실패한 파일도 별도 로그에 기록
        fail_log_path = os.path.join(logs_dir, f"failed_{pid}.txt")
        with open(fail_log_path, "a") as f:
            f.write(f"{subject_id_str}_{unit_id_str}\n")

        return (subject_id_str, unit_id_str, None, False)

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

    # -------------------------------------------------------------------------
    # [FIX 2] 비병렬 버전과 동일한 경로 계산 및 addQ 처리
    # -------------------------------------------------------------------------
    folder_path = Path(folder_path)
    split_str = folder_path.name          # 'test' 또는 'train'
    root_path = folder_path.parent.parent  # root_path

    addQ_str = "addQ" if addQ else "NOadd"
    target_csv = "events_addQ.csv" if addQ else "events.csv"

    # [FIX 3] addQ 인자를 _list_csv_filenames에 전달
    csv_files = _list_csv_filenames(folder_path, addQ=addQ)
    csv_files.sort()
    num_files = len(csv_files)
    num_cores = 40  # args.sample_n_workers 등 외부 변수와 연동 권장

    # [FIX 4] 비병렬 버전과 동일한 processed_path 구조
    processed_path = root_path / "PFM_downstream" / f"processed_{processor.criteria_name}" / addQ_str / split_str

    # --------------------------------------------------------------------------
    # [Phase 1: CSV Parsing]
    # --------------------------------------------------------------------------
    print('1 Processing with Parallelism...')
    if not os.path.exists(os.path.join(processed_path, "done.txt")):
        # [FIX 5] target_csv 및 processed_path를 각 태스크에 포함
        tasks_1 = [(csv_file, target_csv, processor, processed_path) for csv_file in csv_files]
        with Pool(processes=num_cores) as pool:
            list(tqdm(pool.imap_unordered(_parse_single_file, tasks_1), total=num_files, desc="Phase 1: Parsing"))

        with open(os.path.join(processed_path, "done.txt"), "w") as f:
            f.write("done")
    else:
        print('Phase 1 Loaded (already done)')

    # --------------------------------------------------------------------------
    # [Phase 2: Tokenization & TTE Labeling]
    # --------------------------------------------------------------------------
    # [FIX 6] 비병렬 버전과 동일한 tokenize_split_path 구조
    tokenize_split_path = root_path / "PFM_downstream" / "tokenized_splited" / \
                          f"maxlen{max_length}_overlap{overlap_size}_processed_{processor.criteria_name}_share{0 if tokenizer.args.bin.startswith('bin') else tokenizer.args.share_tokens}_ethos{ethos}_{tokenizer.args.bin}" / \
                          addQ_str / split_str

    logs_dir = tokenize_split_path / "process_logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Resume Logic: 이미 처리된 파일 확인
    done_files = set()
    log_files = glob.glob(os.path.join(logs_dir, "done_*.txt"))
    for log_file in log_files:
        with open(log_file, "r") as f:
            for line in f:
                done_files.add(line.strip())

    # [FIX 7] 3-tuple에서 subject_id_str, unit_id_str로 올바르게 참조
    files_to_process = [f for f in csv_files if f"{f[0]}_{f[1]}" not in done_files]
    print(f"Phase 2: 이미 처리된 파일: {len(done_files)}, 남은 파일: {len(files_to_process)}")

    # 각 라벨 컬럼마다 카운터를 합치기 위한 전역 Dict
    dt_label_counter_dict_all = defaultdict(Counter)

    if len(files_to_process) > 0:
        # [FIX 8] 3-tuple 언패킹 수정: csv_dir_path 포함
        tasks_2 = [(subject_id_str, unit_id_str, processed_path, csv_dir_path, ethos,
                    tokenizer, max_length, overlap_size, tokenize_split_path, logs_dir, raw)
                   for subject_id_str, unit_id_str, csv_dir_path in files_to_process]

        print('2 Processing with Parallelism...')
        with Pool(processes=num_cores) as pool:
            for result in tqdm(pool.imap_unordered(_tokenization_worker, tasks_2), total=len(tasks_2),
                               desc="Phase 2: Tokenizing"):
                sub_str, unit_id_str, counter_result, success = result

                if success and counter_result is not None:
                    for col, counts in counter_result.items():
                        dt_label_counter_dict_all[col].update(counts)
    else:
        print('Phase 2 Tokenization & TTE labeling already done')

    # =========================================================================
    # dt_label_counter_dict_all 저장
    # =========================================================================
    if len(dt_label_counter_dict_all) > 0:
        counter_save_path = tokenize_split_path / "dt_label_counter_all.pkl"
        os.makedirs(counter_save_path.parent, exist_ok=True)
        with open(counter_save_path, "wb") as f:
            pickle.dump(dict(dt_label_counter_dict_all), f)
        print(f"✅ dt_label_counter_dict_all 저장 완료: {counter_save_path}")

    # [검증] 빠진 파일이 있는지 확인
    done_files = set()
    for log_file in glob.glob(os.path.join(logs_dir, "done_*.txt")):
        with open(log_file, "r") as f:
            for line in f: done_files.add(line.strip())

    failed_files = set()
    for log_file in glob.glob(os.path.join(logs_dir, "failed_*.txt")):
        with open(log_file, "r") as f:
            for line in f: failed_files.add(line.strip())

    # done도 아니고 failed도 아닌 파일만 진짜 문제
    unprocessed = [f for f in csv_files
                   if f"{f[0]}_{f[1]}" not in done_files
                   and f"{f[0]}_{f[1]}" not in failed_files]

    if len(failed_files) > 0:
        print(f"⚠️  오류로 건너뛴 파일: {len(failed_files)}개 (무시하고 계속)")

    if len(unprocessed) > 0:
        raise Exception(f"오류: 처리도 실패도 아닌 파일이 {len(unprocessed)}개 남았습니다.")

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

    tasks_3 = []
    for batch_idx in range(num_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, num_samples)
        batch_triplets = triplet_samples[start_idx:end_idx]
        tasks_3.append((batch_idx, batch_triplets, tokenize_split_path, basic_dir, dt_label_dir))

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
        # [FIX 9] NotImplementedError 제거 — 병렬 버전 정상 호출
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

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample_max_length", type=int, default=2048)
    parser.add_argument("--sample_overlap", type=int, default=512)
    parser.add_argument("--sample_n_workers", type=int, default=16)
    parser.add_argument("--data_dir", type=str, default="/path/to/PFM_data/PFM_pretraining/tensor_saved/")
    parser.add_argument("--qa_table_dir", type=str, default="/path/to/PFM_data/PFM_pretraining/")
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

    parser.add_argument("--eval_task_dir", type=str, default="/path/to/PFM_data/PFM_downstream/")
    parser.add_argument("--eval_data_dir", type=str, default="/path/to/PFM_data/PFM_downstream/tensor_dt_saved/")

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