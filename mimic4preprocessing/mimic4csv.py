import csv
import numpy as np
import os
import pandas as pd
from tqdm import tqdm
import math

from mimic4preprocessing.util import dataframe_from_csv
from mimic4preprocessing.resources.medcodes import icd10to9dict
from mimic4preprocessing.omr_labevent_fix import fix_omr
from mimic4preprocessing.my_itemid import my_itemid

nb_rows_dict = {'icu/ingredientevents': 14253480, 'icu/outputevents': 5359395, 'icu/datetimeevents': 9979761,
           'icu/chartevents': 432997491, 'icu/procedureevents': 808706, 'icu/inputevents': 10953713,
           'hosp/hcpcsevents': 186074, 'hosp/labevents': 158374764, 'hosp/microbiologyevents': 3988224,
           'hosp/poe': 52212109, 'hosp/prescriptions': 20292611, 'hosp/omr': 7753027, 'hosp/emar': 42808593,
            'hosp/omr_v1': 13249406,}

def read_patients_table(mimic4_path):
    pats = dataframe_from_csv(os.path.join(mimic4_path, 'hosp/patients.csv'))
    pats = pats.reset_index()
    pats = pats[['subject_id', 'gender', 'anchor_age', 'anchor_year', 'dod']] #subject_id	gender	anchor_age	anchor_year	anchor_year_group	dod

    # anchor_year - anchor_age 계산 → 출생연도
    birth_year = pats['anchor_year'] - pats['anchor_age']
    # 출생일을 "YYYY-01-01 00:00:00" 형식으로 생성
    pats['dob'] = pd.to_datetime(birth_year.astype(str) + "-01-01 00:00:00")

    pats.dod = pd.to_datetime(pats.dod)
    return pats


def read_admissions_table(mimic4_path):
    admits = dataframe_from_csv(os.path.join(mimic4_path, 'hosp/admissions.csv')).reset_index() # subject_id	hadm_id	admittime	dischtime	deathtime	admission_type	admit_provider_id	admission_location	discharge_location	insurance	language	marital_status	race	edregtime	edouttime	hospital_expire_flag
    admits = admits[['subject_id', 'hadm_id', 'admittime', 'dischtime', 'deathtime', 'admission_type', 'admission_location', 'discharge_location', 'language', 'marital_status', 'race', 'hospital_expire_flag', 'edregtime', 'edouttime']]
    admits.admittime = pd.to_datetime(admits.admittime)
    admits.dischtime = pd.to_datetime(admits.dischtime)
    admits.edregtime = pd.to_datetime(admits.edregtime)
    admits.edouttime = pd.to_datetime(admits.edouttime)
    admits.deathtime = pd.to_datetime(admits.deathtime)
    return admits


def read_icustays_table(mimic4_path):
    stays = dataframe_from_csv(os.path.join(mimic4_path, 'icu/icustays.csv')).reset_index() # subject_id	hadm_id	stay_id	first_careunit == last_careunit	intime	outtime	los
    stays.intime = pd.to_datetime(stays.intime)
    stays.outtime = pd.to_datetime(stays.outtime)
    return stays

def read_transfers_table(mimic4_path):
    transfers = dataframe_from_csv(os.path.join(mimic4_path, 'hosp/transfers.csv')).reset_index() # subject_id	hadm_id	stay_id	first_careunit == last_careunit	intime	outtime	los
    transfers.intime = pd.to_datetime(transfers.intime)
    transfers.outtime = pd.to_datetime(transfers.outtime)
    # hadm_id: float → int (NaN 안전)
    transfers['hadm_id'] = transfers['hadm_id'].astype('Int64')
    return transfers


def read_lab_table(mimic4_path, chunksize=5_000_000):
    csv_path = os.path.join(mimic4_path, 'hosp/labevents.csv')
    cache_path = os.path.join(mimic4_path, 'hosp/labevents-extract_.pkl')

    # 캐시 있으면 로드
    if os.path.exists(cache_path):
        print(f"[read_lab_table] Load cached: {cache_path}")
        return pd.read_pickle(cache_path)

    print("[read_lab_table] Processing labevents.csv in chunks...")

    chunk_results = []

    for chunk in pd.read_csv(
            csv_path,
            usecols=['subject_id', 'hadm_id', 'charttime'],
            chunksize=chunksize,
            dtype={'subject_id': int, 'hadm_id': float}  # hadm_id는 NaN 포함 가능하므로 일단 float
    ):
        # 날짜 변환
        chunk['charttime'] = pd.to_datetime(chunk['charttime'], errors='coerce')

        # charttime이 없는 데이터만 제거 (hadm_id가 없는 데이터는 살림)
        chunk = chunk.dropna(subset=['charttime'])

        # 핵심 로직: (subject_id, hadm_id) 쌍으로 그룹화하여 최대 시간 계산
        # dropna=False 옵션을 주면 hadm_id가 NaN인 경우도 별도의 그룹으로 잡힘
        # 즉, (subject_id=123, hadm_id=NaN) -> max_time 계산됨
        chunk_max = chunk.groupby(['subject_id', 'hadm_id'], dropna=False)['charttime'].max()

        chunk_results.append(chunk_max)

    print("[read_lab_table] Aggregating chunks...")

    # 모든 청크 결과를 합침
    all_chunks = pd.concat(chunk_results)

    # 청크 경계에 걸쳐있는 ID들이 있을 수 있으므로 다시 한번 groupby -> max 수행
    labevents = all_chunks.groupby(level=['subject_id', 'hadm_id'], dropna=False).max().reset_index()

    # 타입 정리
    # Int64는 NaN을 허용하는 정수 타입입니다.
    labevents['subject_id'] = labevents['subject_id'].astype('Int64')
    labevents['hadm_id'] = labevents['hadm_id'].astype('Int64')

    # 결과 확인용 출력 (옵션)
    print(f"Total rows: {len(labevents)}")
    print(f"Rows with hadm_id: {labevents['hadm_id'].notnull().sum()}")
    print(f"Rows without hadm_id: {labevents['hadm_id'].isnull().sum()}")

    # 캐시 저장
    labevents.to_pickle(cache_path)
    print(f"[read_lab_table] Saved cache: {cache_path}")

    return labevents


def read_chart_table(mimic4_path, chunksize=5_000_000):
    import os
    import pandas as pd

    csv_path = os.path.join(mimic4_path, 'icu/chartevents.csv')

    # 두 개의 캐시 경로 설정
    cache_path_hadm = os.path.join(mimic4_path, 'icu/chartevents-extract_.pkl')
    cache_path_stay = os.path.join(mimic4_path, 'icu/chartevents-extract_stay_.pkl')

    # 두 캐시 파일이 모두 존재하면 로드 후 반환
    if os.path.exists(cache_path_hadm) and os.path.exists(cache_path_stay):
        print(f"[read_chart_table] Load cached (HADM): {cache_path_hadm}")
        print(f"[read_chart_table] Load cached (STAY): {cache_path_stay}")
        df_hadm = pd.read_pickle(cache_path_hadm)
        df_stay = pd.read_pickle(cache_path_stay)
        return df_hadm, df_stay

    print("[read_chart_table] Processing chartevents.csv in chunks...")

    # 집계용 딕셔너리 초기화
    agg_hadm = {}  # hadm_id -> (subject_id, max_charttime)
    agg_stay = {}  # stay_id -> (subject_id, max_charttime)

    # usecols에 stay_id 추가
    for chunk in pd.read_csv(
            csv_path,
            usecols=['subject_id', 'hadm_id', 'stay_id', 'charttime'],
            chunksize=chunksize
    ):
        # datetime 변환
        chunk['charttime'] = pd.to_datetime(chunk['charttime'], errors='coerce')

        # -------------------------------------------------------
        # 1. HADM_ID 기준 집계
        # -------------------------------------------------------
        # hadm_id가 있는 행만 추출
        chunk_h = chunk.dropna(subset=['hadm_id', 'charttime'])

        if not chunk_h.empty:
            # 청크 내에서 hadm_id별로 가장 늦은 시간과 subject_id 추출 (속도 최적화)
            # sort_values -> drop_duplicates를 쓰면 groupby 루프보다 빠릅니다.
            latest_h = (chunk_h.sort_values('charttime', ascending=False)
                        .drop_duplicates(['hadm_id']))

            # Global Dictionary 업데이트
            for row in latest_h.itertuples(index=False):
                # row: subject_id, hadm_id, stay_id, charttime 순서 (usecols 순서가 아님에 주의, 이름으로 접근 권장)
                hid = row.hadm_id
                sid = row.subject_id
                ct = row.charttime

                if hid not in agg_hadm or ct > agg_hadm[hid][1]:
                    agg_hadm[hid] = (sid, ct)

        # -------------------------------------------------------
        # 2. STAY_ID 기준 집계 (새로 추가된 부분)
        # -------------------------------------------------------
        # stay_id가 있는 행만 추출
        chunk_s = chunk.dropna(subset=['stay_id', 'charttime'])

        if not chunk_s.empty:
            # 청크 내에서 stay_id별 최신값 추출
            latest_s = (chunk_s.sort_values('charttime', ascending=False)
                        .drop_duplicates(['stay_id']))

            for row in latest_s.itertuples(index=False):
                stid = row.stay_id
                sid = row.subject_id
                ct = row.charttime

                if stid not in agg_stay or ct > agg_stay[stid][1]:
                    agg_stay[stid] = (sid, ct)

    # -------------------------------------------------------
    # 결과 생성 및 저장: HADM
    # -------------------------------------------------------
    chartevents_hadm = (
        pd.DataFrame.from_dict(
            agg_hadm, orient='index', columns=['subject_id', 'charttime']
        )
        .reset_index(names='hadm_id')
    )
    chartevents_hadm['subject_id'] = chartevents_hadm['subject_id'].astype('Int64')
    chartevents_hadm['hadm_id'] = chartevents_hadm['hadm_id'].astype('Int64')

    chartevents_hadm.to_pickle(cache_path_hadm)
    print(f"[read_chart_table] Saved cache (HADM): {cache_path_hadm}")

    # -------------------------------------------------------
    # 결과 생성 및 저장: STAY (새로 추가된 부분)
    # -------------------------------------------------------
    chartevents_stay = (
        pd.DataFrame.from_dict(
            agg_stay, orient='index', columns=['subject_id', 'charttime']
        )
        .reset_index(names='stay_id')
    )
    chartevents_stay['subject_id'] = chartevents_stay['subject_id'].astype('Int64')
    chartevents_stay['stay_id'] = chartevents_stay['stay_id'].astype('Int64')

    chartevents_stay.to_pickle(cache_path_stay)
    print(f"[read_chart_table] Saved cache (STAY): {cache_path_stay}")

    # 두 개의 데이터프레임을 반환
    return chartevents_hadm, chartevents_stay


def read_icd_diagnoses_table(mimic4_path):
    codes = dataframe_from_csv(os.path.join(mimic4_path, 'hosp/d_icd_diagnoses.csv'))
    codes = codes.reset_index()  # index -> normal column
    codes = codes[['icd_code', 'icd_version', 'long_title']]
    diagnoses = dataframe_from_csv(os.path.join(mimic4_path, 'hosp/diagnoses_icd.csv'))
    diagnoses = diagnoses.reset_index()  # index -> normal column
    diagnoses = diagnoses.merge(codes, how='inner', left_on=['icd_code', 'icd_version'], right_on=['icd_code', 'icd_version'])
    diagnoses[['subject_id', 'hadm_id', 'seq_num']] = diagnoses[['subject_id', 'hadm_id', 'seq_num']].astype(int)
    return diagnoses


def read_events_table_by_row(mimic4_path, table):
    #nb_rows_dict = {'chartevents': 330712484, 'labevents': 27854056, 'outputevents': 4349219}
    # hosp/omr 예외 처리
    if table.lower() == 'hosp/omr':
        path = os.path.join(mimic4_path, 'hosp/omr.csv')
        df_omr = pd.read_csv(path)

        df_omr = fix_omr(df_omr)

        total_rows = len(df_omr)

        print('total_len omr: ', total_rows)

        df_omr.to_csv(
            mimic4_path+'/hosp/omr_v1.csv',
            index=False,
            chunksize=1_000_000  # 100만 row씩 write
        )

        for i, row in df_omr.iterrows():
            row = row.to_dict()

            if 'icustay_id' not in row:
                row['icustay_id'] = ''

            yield row, i, total_rows

    reader = csv.DictReader(open(os.path.join(mimic4_path, table.lower() + '.csv'), 'r'))
    for i, row in enumerate(reader):
        if 'icustay_id' not in row:
            row['icustay_id'] = ''
        # --------------------------------------------------
        # labevents 전용 value / valuenum 처리
        # --------------------------------------------------
        if table.lower() == 'hosp/labevents':
            value = row.get('value')
            valuenum = row.get('valuenum')

            # valuenum이 숫자로 변환 가능한지
            try:
                valuenum_num = float(valuenum)
                valuenum_valid = True
            except (TypeError, ValueError):
                valuenum_valid = False

            # value가 숫자로 변환 가능한지
            try:
                float(value)
                value_is_numeric = True
            except (TypeError, ValueError):
                value_is_numeric = False

            # 조건: valuenum은 숫자 가능 + value는 숫자 불가
            if valuenum_valid and not value_is_numeric:
                row['value'] = str(valuenum_num)
        yield row, i, nb_rows_dict[table.lower()]


def count_icd_codes(diagnoses, output_path=None):
    codes = diagnoses[['ICD9_CODE', 'icd_version', 'long_title']].drop_duplicates().set_index('ICD9_CODE')
    codes['count'] = diagnoses.groupby('ICD9_CODE')['hadm_id'].count()
    codes['count'] = codes['count'].fillna(0).astype(int)
    codes = codes[codes['count'] > 0]
    if output_path:
        codes.to_csv(output_path, index_label='ICD9_CODE')
    return codes.sort_values('count', ascending=False).reset_index()


def count_icd_codes_v2(diagnoses, output_path=None):
    # 고유 코드 + 제목 테이블 생성
    codes = (
        diagnoses[['icd_code', 'icd_version', 'long_title']]
        .drop_duplicates()
        .set_index(['icd_code', 'icd_version'])
    )

    # (icd_code, icd_version) 조합별 count
    codes['COUNT'] = (
        diagnoses.groupby(['icd_code', 'icd_version'])['hadm_id'].count()
    )

    # NA → 0, int 변환
    codes['COUNT'] = codes['COUNT'].fillna(0).astype(int)

    # count > 0만 필터
    codes = codes[codes['COUNT'] > 0]

    # 저장
    if output_path:
        codes.to_csv(output_path, index_label=['icd_code', 'icd_version'])

    diagnoses = idcd10toidc9(diagnoses)
    new_output_path = os.path.join(os.path.dirname(output_path),'diagnoses_counts_icd9s.csv')
    count_icd_codes(diagnoses, new_output_path)

    return diagnoses

def idcd10toidc9(diagnoses):
    df = diagnoses.copy()
    # ICD-10 row만 따로 가져오기
    mask10 = df['icd_version'] == 10
    df10 = df[mask10]
    # 매핑 수행
    df10['mapped_code'] = df10['icd_code'].map(icd10to9dict)
    # 매핑 성공한 row만 유지
    df10 = df10.dropna(subset=['mapped_code'])
    # 코드와 버전 업데이트
    df10['icd_code'] = df10['mapped_code']
    df10['icd_version'] = 9
    df10 = df10.drop(columns=['mapped_code'])
    # ICD-9 원래 row + 변환된 ICD-10 row 합치기
    df9 = df[~mask10]
    # concat
    result = pd.concat([df9, df10], ignore_index=True)
    result = result.rename(columns={'icd_code': 'ICD9_CODE'})
    return result

def remove_icustays_with_transfers(stays): # subject_id	hadm_id	stay_id	first_careunit == last_careunit	intime	outtime	los
    stays = stays[(stays.first_careunit == stays.last_careunit)]
    return stays[['subject_id', 'hadm_id', 'stay_id', 'last_careunit', 'intime', 'outtime', 'los']]


def merge_on_subject(table1, table2):
    return table1.merge(table2, how='inner', left_on=['subject_id'], right_on=['subject_id'])


def merge_on_subject_admission(table1, table2): #stays, admits
    return table1.merge(table2, how='inner', left_on=['subject_id', 'hadm_id'], right_on=['subject_id', 'hadm_id'])

def outer_merge_on_subject_admission(table1, table2): #stays, admits
    return table1.merge(table2, how='outer', on=['subject_id','hadm_id'])


def add_age_to_icustays(stays):
    stays['age'] = stays.apply(lambda e: (e['intime'].to_pydatetime() - e['dob'].to_pydatetime()).total_seconds() / 3600.0 / 24.0 / 365.0, axis=1)
    stays.loc[stays.age < 0, 'age'] = 90
    return stays

def add_age_to_admin(stays):
    stays['dob'] = pd.to_datetime(
        (stays['anchor_year'] - stays['anchor_age']).astype(str) + '-01-01 00:00:00'
    )
    stays['age'] = stays.apply(lambda e: (e['admittime'].to_pydatetime() - e['dob'].to_pydatetime()).total_seconds() / 3600.0 / 24.0 / 365.0, axis=1)
    stays.loc[stays.age < 0, 'age'] = 90
    return stays

def add_inhospital_mortality_to_icustays(stays):
    mortality = stays.DOD.notnull() & ((stays.ADMITTIME <= stays.DOD) & (stays.DISCHTIME >= stays.DOD))
    mortality = mortality | (stays.DEATHTIME.notnull() & ((stays.ADMITTIME <= stays.DEATHTIME) & (stays.DISCHTIME >= stays.DEATHTIME)))
    stays['MORTALITY'] = mortality.astype(int)
    stays['MORTALITY_INHOSPITAL'] = stays['MORTALITY']
    return stays

def add_inhospital_mortality_to_icustays_v2(stays):
    mortality = (stays.deathtime.notnull() & ((stays.admittime <= stays.deathtime) & (stays.dischtime >= stays.deathtime)))
    stays['mortality'] = mortality.astype(int)
    stays['mortality_inhospital'] = stays['mortality']
    return stays

def add_inunit_mortality_to_icustays(stays):
    mortality = stays.dod.notnull() & ((stays.intime <= stays.dod) & (stays.outtime >= stays.dod))
    mortality = mortality | (stays.deathtime.notnull() & ((stays.intime <= stays.deathtime) & (stays.outtime >= stays.deathtime)))
    stays['mortality_inunit'] = mortality.astype(int)
    return stays

def add_inunit_mortality_to_icustays_v2(stays):
    mortality = (stays.deathtime.notnull() & ((stays.intime <= stays.deathtime) & (stays.outtime >= stays.deathtime)))
    stays['mortality_inunit'] = mortality.astype(int)
    return stays


def filter_admissions_on_nb_icustays(stays, min_nb_stays=1, max_nb_stays=1):
    to_keep = stays.groupby('HADM_ID').count()[['ICUSTAY_ID']].reset_index()
    to_keep = to_keep[(to_keep.ICUSTAY_ID >= min_nb_stays) & (to_keep.ICUSTAY_ID <= max_nb_stays)][['HADM_ID']]
    stays = stays.merge(to_keep, how='inner', left_on='HADM_ID', right_on='HADM_ID')
    return stays


def filter_icustays_on_age(stays, min_age=18, max_age=np.inf):
    stays = stays[(stays.age >= min_age) & (stays.age <= max_age)]
    return stays


def filter_diagnoses_on_stays(diagnoses, stays):
    return diagnoses.merge(stays[['subject_id', 'hadm_id']].drop_duplicates(), how='inner',
                           left_on=['subject_id', 'hadm_id'], right_on=['subject_id', 'hadm_id'])


def break_up_stays_by_subject(stays, output_path, subjects=None):
    subjects = stays.subject_id.unique() if subjects is None else subjects
    nb_subjects = subjects.shape[0]
    for subject_id in tqdm(subjects, total=nb_subjects, desc='Breaking up stays by subjects'):
        dn = os.path.join(output_path, str(subject_id))
        try:
            os.makedirs(dn)
        except:
            pass

        stays[stays.subject_id == subject_id].sort_values(by=['admittime', 'intime']).to_csv(os.path.join(dn, 'stays.csv'), index=False)


def break_up_diagnoses_by_subject(diagnoses, output_path, subjects=None):
    subjects = diagnoses.subject_id.unique() if subjects is None else subjects
    nb_subjects = subjects.shape[0]
    for subject_id in tqdm(subjects, total=nb_subjects, desc='Breaking up diagnoses by subjects'):
        dn = os.path.join(output_path, str(subject_id))
        try:
            os.makedirs(dn)
        except:
            pass

        diagnoses[diagnoses.subject_id == subject_id].sort_values(by=['ICUSTAY_ID', 'SEQ_NUM'])\
                                                     .to_csv(os.path.join(dn, 'diagnoses.csv'), index=False)

def break_up_diagnoses_by_subject_v2(diagnoses, output_path, subjects=None):
    subjects = diagnoses.subject_id.unique() if subjects is None else subjects
    nb_subjects = subjects.shape[0]
    for subject_id in tqdm(subjects, total=nb_subjects, desc='Breaking up diagnoses by subjects'):
        dn = os.path.join(output_path, str(subject_id))
        try:
            os.makedirs(dn)
        except:
            pass

        diagnoses[diagnoses.subject_id == subject_id].sort_values(by=['hadm_id', 'seq_num'])\
                                                     .to_csv(os.path.join(dn, 'diagnoses.csv'), index=False)

class ItemIDLabelMapper:
    def __init__(self, table, mimic4_path, itemid_col='itemid', label_col='label'):
        self.itemid_col = itemid_col
        self.label_col = label_col
        self.table = table

        if table != 'hosp/labevents':
            df = pd.read_csv(mimic4_path + "/icu/d_items.csv")

        else:
            df = pd.read_csv("./mimic4preprocessing/resources/itemid_to_variable_map.csv")
            df_lab = pd.read_csv(mimic4_path + "/hosp/d_labitems.csv")
            #df = pd.read_csv("./resources/itemid_to_variable_map.csv")
            df.columns = df.columns.str.lower()
            df_lab.columns = df_lab.columns.str.lower()

            # df에 없는 itemid만 df_lab에서 추출
            missing_lab = df_lab.loc[
                ~df_lab['itemid'].isin(df['itemid']),
                ['itemid', 'label']
            ].copy()
            # level2에 label 대문자로 채우기
            missing_lab['level2'] = missing_lab['label'].str.upper()
            # df의 컬럼 구조에 맞추기 (없는 컬럼은 NaN)
            missing_lab = missing_lab.drop(columns=['label'])
            missing_lab = missing_lab.reindex(columns=df.columns)
            # df에 row 추가
            df = pd.concat([df, missing_lab], ignore_index=True)


            label_col = 'level2'
            spare_col = 'mimic label'

            # label 보완: level2가 NaN이면 mimic label 사용
            df[label_col] = df[label_col].fillna(df[spare_col])



        # 타입 통일 (문자/숫자 섞임 방지)
        df = df[[itemid_col, label_col]].dropna(subset=[itemid_col, label_col])
        df[itemid_col] = df[itemid_col].astype(int)



        # dict 생성 (itemid → label)
        # itemid 중복 시 첫 번째 label 사용
        self._map = (
            df.drop_duplicates(subset=[itemid_col])
              .set_index(itemid_col)[label_col]
              .to_dict()
        )
        if table == 'hosp/omr' or table == 'hosp/omr_v1':
            self.itemname = self.get_simple
        else:
            self.itemname = self.get

    def get(self, row, default=''):
        itemid = row['itemid']
        try:
            return self._map.get(int(itemid), default)
        except (ValueError, TypeError):
            print(f'!!!Missing!!! table:{self.table}, itemid:{itemid}')
            #raise 'ERRR'
            return default

    def get_simple(self, row):
        return row['result_name']

    def __contains__(self, itemid):
        try:
            return int(itemid) in self._map
        except (ValueError, TypeError):
            return False

    def __len__(self):
        return len(self._map)

def safe_int(val):
    if val in (None, ''):
        return ''
    try:
        # float 형태 ('22595853.0' 포함) 처리
        f = float(val)
        if math.isnan(f):
            return ''
        return int(f)
    except (ValueError, TypeError):
        return ''

def read_events_table_and_break_up_by_subject(mimic4_path, table, output_path,
                                              items_to_keep=None, subjects_to_keep=None, reset = False):
    # print("CWD (current working directory):", os.getcwd())
    # raise AttributeError
    obs_header = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'itemname', 'value', 'valueuom', 'linksto', 'order']
    if items_to_keep is not None:
        items_to_keep = set([str(s) for s in items_to_keep])
    if subjects_to_keep is not None:
        subjects_to_keep = set([str(s) for s in subjects_to_keep])

    if table == 'hosp/omr':
        linksto = 'omr'
    elif table == 'hosp/omr_v1':
        linksto = 'omr'
    elif table == 'icu/chartevents':
        linksto = 'chartevents'
    elif table == 'hosp/labevents':
        linksto = 'labevents'
    elif table == 'icu/outputevents':
        linksto = 'outputevents'
    else:
        raise NotImplementedError


    class DataStats(object):
        def __init__(self):
            self.curr_subject_id = ''
            self.curr_obs = []

    data_stats = DataStats()
    mapper = ItemIDLabelMapper(table, mimic4_path)

    def write_current_observations(reset):
        dn = os.path.join(output_path, str(data_stats.curr_subject_id))
        try:
            os.makedirs(dn)
        except:
            pass
        fn = os.path.join(dn, 'events.csv')
        if not os.path.exists(fn) or not os.path.isfile(fn) or reset:
            f = open(fn, 'w')
            f.write(','.join(obs_header) + '\n')
            f.close()
        w = csv.DictWriter(open(fn, 'a'), fieldnames=obs_header, quoting=csv.QUOTE_MINIMAL)
        w.writerows(data_stats.curr_obs)
        data_stats.curr_obs = []

    #nb_rows_dict = {'chartevents': 330712484, 'labevents': 27854056, 'outputevents': 4349219}
    nb_rows = nb_rows_dict[table.lower()]

    if table == 'hosp/omr': nb_rows = 13249406

    for row, row_no, _ in tqdm(read_events_table_by_row(mimic4_path, table), total=nb_rows,
                                                        desc='Processing {} table'.format(table)):

        if (subjects_to_keep is not None) and (row['subject_id'] not in subjects_to_keep):
            continue
        if (items_to_keep is not None) and (row['itemid'] not in items_to_keep):
            continue

        try:
            int_itemid = int(row['itemid'])
        except:
            print(row)
        row_out = {'subject_id': row['subject_id'],
                   'hadm_id': safe_int(row.get('hadm_id')),
                   'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                   'charttime': row['charttime'],
                   'itemid': row['itemid'],
                   'itemname': mapper.itemname(row),
                   'value': row['value'],
                   'valueuom': row['valueuom'],
                   'linksto': linksto if int(row['itemid'])<1000000 else 'hosp_admin',
                   'order': int(row['order']) if row.get('order') not in (None, '') else 0,}
        if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
            write_current_observations(reset)
        data_stats.curr_obs.append(row_out)
        data_stats.curr_subject_id = row['subject_id']

    if data_stats.curr_subject_id != '':
        write_current_observations(reset)

def read_adm_stay_table_and_break_up_by_subject(df, output_path, type, items_to_keep=None, subjects_to_keep=None,):
    obs_header = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'itemname', 'value', 'valueuom', 'linksto', 'order']
    if items_to_keep is not None:
        items_to_keep = set([str(s) for s in items_to_keep])
    if subjects_to_keep is not None:
        subjects_to_keep = set([str(s) for s in subjects_to_keep])

    if type == 'stay':
        linksto = 'icu_admin'
    elif type == 'admit':
        linksto = 'hosp_admin'
    elif type == 'for_dob':
        linksto = 'prefix'
    elif type == 'for_dod':
        linksto = 'hosp_admin'

    class DataStats(object):
        def __init__(self):
            self.curr_subject_id = ''
            self.curr_obs = []

    data_stats = DataStats()

    def write_current_observations(reset=False):
        dn = os.path.join(output_path, str(data_stats.curr_subject_id))
        try:
            os.makedirs(dn)
        except:
            pass
        fn = os.path.join(dn, 'events.csv')
        if not os.path.exists(fn) or not os.path.isfile(fn) or reset:
            f = open(fn, 'w')
            f.write(','.join(obs_header) + '\n')
            f.close()
        w = csv.DictWriter(open(fn, 'a'), fieldnames=obs_header, quoting=csv.QUOTE_MINIMAL)
        w.writerows(data_stats.curr_obs)
        data_stats.curr_obs = []

    # print(df)
    # print(len(df))
    # raise AttributeError

    for _, row in tqdm(df.iterrows(), total=len(df), desc='Processing Stay table'):
        if (subjects_to_keep is not None) and (str(row['subject_id']) not in subjects_to_keep):
            continue
        if type == 'stay': # -> ICU In/Out & #ICU class#
            # ICU IN
            tag = 'icu-in'
            key__ = 'Move'
            row_out = {'subject_id': row['subject_id'],
                       'hadm_id': row['hadm_id'],
                       'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                       'charttime': row['intime'],
                       'itemid': my_itemid[key__]['itemid'],
                       'itemname': key__,
                       'value': tag,
                       'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                       'linksto': linksto,
                       'order': 2, }
            if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                write_current_observations()
            data_stats.curr_obs.append(row_out)
            data_stats.curr_subject_id = row['subject_id']
            # ICU OUT
            tag = 'icu-out'
            key__ = 'Move'
            """ 다음은 icu-out time이 안적혀서 manual하게 적어준 값 """
            if pd.to_datetime(row['outtime'], errors='coerce') is pd.NaT:
                id_outtime = {12590282:'2185-04-12 17:11:19', 18717462:'2189-03-31 13:24:07', 14330929:'2188-06-23 14:45:00',
                              11661851:'2173-01-20 00:00:00', 17434223:'2146-09-28 12:35:23', 16348177:'2151-10-23 17:01:00',
                              10882284:'2125-05-18 17:00:13', 11783844:'2157-10-29 13:35:00', 15882332:'2178-04-18 18:29:00',
                              15777534:'2126-03-11 01:12:03', 19526758:'2153-07-09 11:20:00', 16799689:'2166-04-10 01:18:00',
                              10492274:'2165-03-25 16:20:00', 16117624:'2180-08-24 08:02:00'}
                row['outtime'] = id_outtime[int(row['subject_id'])]
            row_out = {'subject_id': row['subject_id'],
                       'hadm_id': row['hadm_id'],
                       'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                       'charttime': row['outtime'],
                       'itemid': my_itemid[key__]['itemid'],
                       'itemname': key__,
                       'value': tag,
                       'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                       'linksto': linksto,
                       'order': -3, }
            if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                write_current_observations()
            data_stats.curr_obs.append(row_out)
            data_stats.curr_subject_id = row['subject_id']
            # ICU class
            tag = 'last_careunit'
            key__ = 'ICU class'
            row_out = {'subject_id': row['subject_id'],
                       'hadm_id': row['hadm_id'],
                       'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                       'charttime': row['intime'],
                       'itemid': my_itemid[key__]['itemid'],
                       'itemname': key__,
                       'value': row[tag],
                       'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                       'linksto': linksto,
                       'order': 1, }
            if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                write_current_observations()
            data_stats.curr_obs.append(row_out)
            data_stats.curr_subject_id = row['subject_id']

        elif type == 'admit': #Admission -> @5 ER_ADM - @4 ADM/ER_DISCH - @3 #Admission location# - 0 - @-1 #'Death-event'/'Censored-event'# - @-3 DISCH - @-4 #Discharge location#

            if pd.notna(pd.to_datetime(row['edregtime'], errors='coerce')): # IF from ED
                # ED Admin
                tag = 'ed_admission'
                key__ = 'Move'
                row_out = {'subject_id': row['subject_id'],
                           'hadm_id': row['hadm_id'],
                           'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                           'charttime': row['edregtime'],
                           'itemid': my_itemid[key__]['itemid'],
                           'itemname': key__,
                           'value': tag,
                           'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                           'linksto': linksto,
                           'order': 5, }
                if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                    write_current_observations()
                data_stats.curr_obs.append(row_out)
                data_stats.curr_subject_id = row['subject_id']
                # ED Disch
                tag = 'ed_discharge'
                key__ = 'Move'
                row_out = {'subject_id': row['subject_id'],
                           'hadm_id': row['hadm_id'],
                           'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                           'charttime': row['edouttime'],
                           'itemid': my_itemid[key__]['itemid'],
                           'itemname': key__,
                           'value': tag,
                           'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                           'linksto': linksto,
                           'order': 4, }
                if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                    write_current_observations()
                data_stats.curr_obs.append(row_out)
                data_stats.curr_subject_id = row['subject_id']

            # Admission
            tag = 'admission'
            key__ = 'Move'
            row_out = {'subject_id': row['subject_id'],
                       'hadm_id': row['hadm_id'],
                       'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                       'charttime': row['admittime'],
                       'itemid': my_itemid[key__]['itemid'],
                       'itemname': key__,
                       'value': tag,
                       'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                       'linksto': linksto,
                       'order': 4, }
            if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                write_current_observations()
            data_stats.curr_obs.append(row_out)
            data_stats.curr_subject_id = row['subject_id']
            # Admission-location
            tag = 'admission_location'
            key__ = 'Admission location'
            name_tag = row[tag] if not (pd.isna(row[tag]) or str(row[tag]).strip() == '') else 'None-admit_loc'
            row_out = {'subject_id': row['subject_id'],
                       'hadm_id': row['hadm_id'],
                       'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                       'charttime': row['admittime'],
                       'itemid': my_itemid[key__]['itemid'],
                       'itemname': key__,
                       'value': name_tag,
                       'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                       'linksto': linksto,
                       'order': 3, }
            if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                write_current_observations()
            data_stats.curr_obs.append(row_out)
            data_stats.curr_subject_id = row['subject_id']
            # Discharge
            tag = 'discharge'
            key__ = 'Move'
            row_out = {'subject_id': row['subject_id'],
                       'hadm_id': row['hadm_id'],
                       'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                       'charttime': row['dischtime'],
                       'itemid': my_itemid[key__]['itemid'],
                       'itemname': key__,
                       'value': tag,
                       'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                       'linksto': linksto,
                       'order': -4, }
            if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                write_current_observations()
            data_stats.curr_obs.append(row_out)
            data_stats.curr_subject_id = row['subject_id']
            # Discharge-location
            tag = 'discharge_location'
            key__ = 'Discharge location'
            name_tag = row[tag] if not (pd.isna(row[tag]) or str(row[tag]).strip() == '') else 'None-disch_loc'
            row_out = {'subject_id': row['subject_id'],
                       'hadm_id': row['hadm_id'],
                       'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                       'charttime': row['dischtime'],
                       'itemid': my_itemid[key__]['itemid'],
                       'itemname': key__,
                       'value': name_tag,
                       'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                       'linksto': linksto,
                       'order': -5, }
            if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                write_current_observations()
            data_stats.curr_obs.append(row_out)
            data_stats.curr_subject_id = row['subject_id']
            # 'Death-event' - IHM
            if int(row['hospital_expire_flag']) == 1:
                tag = 'Death-event'
                key__ = "Ending"
                row_out = {'subject_id': row['subject_id'],
                           'hadm_id': row['hadm_id'],
                           'stay_id': int(row['stay_id']) if row.get('stay_id') not in (None, '') else '',
                           'charttime': row['deathtime'],
                           'itemid': my_itemid[key__]['itemid'],
                           'itemname': key__,
                           'value': tag,
                           'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                           'linksto': linksto,
                           'order': -2, }
                if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                    write_current_observations()
                data_stats.curr_obs.append(row_out)
                data_stats.curr_subject_id = row['subject_id']

        elif type == 'for_dob':
            ###### ADD Birth Prefix ######
            # Birth - Subject별로 하나 들어가야 하므로 처음에 위치하여 data_stats.curr_obs 가 비어 있는 경우만 추가됨
            if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                write_current_observations()

            if len(data_stats.curr_obs) == 0:

                tag = 'Birth'
                row_out = {'subject_id': row['subject_id'],
                           'hadm_id': '',
                           'stay_id': '',
                           'charttime': row['dob'],
                           'itemid': my_itemid[tag]['itemid'],
                           'itemname': tag,
                           'value': '',
                           'valueuom': my_itemid[tag]['unit'] if my_itemid[tag]['unit'] is not None else '',
                           'linksto': linksto,
                           'order': 100, }
                data_stats.curr_obs.append(row_out)

                tag = f'{"Male" if row['gender'] == "M" else "Female"}'
                key__ = 'Gender'
                row_out = {'subject_id': row['subject_id'],
                           'hadm_id': '',
                           'stay_id': '',
                           'charttime': row['dob'],
                           'itemid': my_itemid[key__]['itemid'],
                           'itemname': key__,
                           'value': tag,
                           'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                           'linksto': linksto,
                           'order': 99, }
                data_stats.curr_obs.append(row_out)

                tag = f'{row['race']}'
                key__ = 'Ethnicity'
                row_out = {'subject_id': row['subject_id'],
                           'hadm_id': '',
                           'stay_id': '',
                           'charttime': row['dob'],
                           'itemid': my_itemid[key__]['itemid'],
                           'itemname': key__,
                           'value': tag,
                           'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                           'linksto': linksto,
                           'order': 98, }
                data_stats.curr_obs.append(row_out)

            data_stats.curr_subject_id = row['subject_id']

        elif type == 'for_dod':
            ###### ADD Out of Hospital Death & Censored ######
            '''hospital_expire_flag 가 1이 아닌 애들 대상으로 진행'''
            if int(row['hospital_expire_flag']) != 1:
                tag = 'Censored-event' if pd.isna(row['dod']) else 'Death-event'
                key__ = 'Ending'
                row_out = {'subject_id': row['subject_id'],
                           'hadm_id': '',
                           'stay_id': '',
                           'charttime': row['dod'] if tag == 'Death-event' else row['dischtime'] + pd.DateOffset(years=1), #위에서 하루 다음날로 미뤄짐
                           'itemid': my_itemid[key__]['itemid'],
                           'itemname': key__,
                           'value': tag,
                           'valueuom': my_itemid[key__]['unit'] if my_itemid[key__]['unit'] is not None else '',
                           'linksto': linksto,
                           'order': -2, }
                if data_stats.curr_subject_id != '' and data_stats.curr_subject_id != row['subject_id']:
                    write_current_observations()
                data_stats.curr_obs.append(row_out)
                data_stats.curr_subject_id = row['subject_id']


    if data_stats.curr_subject_id != '':
        write_current_observations()

if __name__ == '__main__':
    table = 'hosp/labevents'
    mimic4_path = 'mimic4preprocessing.scripts.extract_subjects /path/to/mimiciv/3.1'
    mapper = ItemIDLabelMapper(table, mimic4_path)
    print(mapper._map[52065])