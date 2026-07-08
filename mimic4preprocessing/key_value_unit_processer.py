import pickle
import pandas as pd
import numpy as np
from collections import defaultdict
from mimic4preprocessing.my_itemid import my_itemid
from mimic4preprocessing.scripts.inclusion_criteria.criteria1 import criteria1

from mimic4preprocessing.unit_value_cleaning.dicts_chartevents import float_value_convert as chartevents_float_value_convert
from mimic4preprocessing.unit_value_cleaning.dicts_chartevents import string_value_convert as chartevents_string_value_convert
from mimic4preprocessing.unit_value_cleaning.dicts_chartevents import chartevents_float_unit_convert as chartevents_float_unit_convert
from mimic4preprocessing.unit_value_cleaning.dicts_chartevents import chartevents_str_unit_convert as chartevents_str_unit_convert
from mimic4preprocessing.unit_value_cleaning.dicts_chartevents import float_inclusion_dict as chartevents_float_inclusion_dict
from mimic4preprocessing.unit_value_cleaning.dicts_chartevents import float_binary_inclusion_dict as chartevents_float_binary_inclusion_dict
from mimic4preprocessing.unit_value_cleaning.dicts_chartevents import convert_key_float as chartevents_convert_key_float

from mimic4preprocessing.unit_value_cleaning.dicts_labevents import float_value_convert as labevents_float_value_convert
from mimic4preprocessing.unit_value_cleaning.dicts_labevents import string_value_convert as labevents_string_value_convert
from mimic4preprocessing.unit_value_cleaning.dicts_labevents import labevents_float_unit_convert as labevents_float_unit_convert
from mimic4preprocessing.unit_value_cleaning.dicts_labevents import labevents_str_unit_convert as labevents_str_unit_convert
from mimic4preprocessing.unit_value_cleaning.dicts_labevents import float_inclusion_dict as labevents_float_inclusion_dict
from mimic4preprocessing.unit_value_cleaning.dicts_labevents import convert_key_float as labevents_convert_key_float

from mimic4preprocessing.unit_value_cleaning.dicts_omr import float_value_convert as omr_float_value_convert
from mimic4preprocessing.unit_value_cleaning.dicts_omr import string_value_convert as omr_string_value_convert
from mimic4preprocessing.unit_value_cleaning.dicts_omr import omr_float_unit_convert as omr_float_unit_convert
from mimic4preprocessing.unit_value_cleaning.dicts_omr import omr_str_unit_convert as omr_str_unit_convert
from mimic4preprocessing.unit_value_cleaning.dicts_omr import float_inclusion_dict as omr_float_inclusion_dict
from mimic4preprocessing.unit_value_cleaning.dicts_omr import convert_key_float as omr_convert_key_float

from mimic4preprocessing.unit_value_cleaning.dicts_outputevents import float_value_convert as outputevents_float_value_convert
from mimic4preprocessing.unit_value_cleaning.dicts_outputevents import string_value_convert as outputevents_string_value_convert
from mimic4preprocessing.unit_value_cleaning.dicts_outputevents import outputevents_float_unit_convert as outputevents_float_unit_convert
from mimic4preprocessing.unit_value_cleaning.dicts_outputevents import outputevents_str_unit_convert as outputevents_str_unit_convert
from mimic4preprocessing.unit_value_cleaning.dicts_outputevents import float_inclusion_dict as outputevents_float_inclusion_dict
from mimic4preprocessing.unit_value_cleaning.dicts_outputevents import convert_key_float as outputevents_convert_key_float

from mimic4preprocessing.unit_value_cleaning.interchange_csvs import labevents_to, omr_to, outputevents_to
interchange_csvs_dict = {'labevents':labevents_to, 'omr':omr_to, 'outputevents':outputevents_to}
convert_key_float_dict = {'chartevents':chartevents_convert_key_float,
                          'labevents':labevents_convert_key_float,
                          'omr':omr_convert_key_float,
                          'outputevents':outputevents_convert_key_float}
value_convert = {'chartevents': chartevents_float_value_convert|chartevents_string_value_convert,
                 'labevents': labevents_float_value_convert|labevents_string_value_convert,
                 'omr': omr_float_value_convert|omr_string_value_convert,
                 'outputevents':outputevents_float_value_convert|outputevents_string_value_convert}
unit_convert = {'chartevents': chartevents_float_unit_convert|chartevents_str_unit_convert,
                 'labevents': labevents_float_unit_convert|labevents_str_unit_convert,
                 'omr': omr_float_unit_convert|omr_str_unit_convert,
                 'outputevents':outputevents_float_unit_convert|outputevents_str_unit_convert}
clipping = {'chartevents': chartevents_float_inclusion_dict|chartevents_float_binary_inclusion_dict,
            'labevents': labevents_float_inclusion_dict,
            'omr': omr_float_inclusion_dict,
            'outputevents':outputevents_float_inclusion_dict}

from mimic4preprocessing.my_itemid import my_itemid


linkstos = ['chartevents', 'labevents', 'omr', 'outputevents', 'hosp_admin', 'icu_admin', 'prefix',  ]
main_linkstos = ['chartevents', 'labevents', 'omr', 'outputevents']
criteria_dict = {'criteria1':criteria1}

class key_value_unit_processer:
    def __init__(self, criteria_name, data_path = 'mimic4preprocessing/unit_value_cleaning/data/'): #data_path: ~~unit_value_cleaning/data/
        self.main_linkstos = main_linkstos
        self.my_itemid = my_itemid
        self.interchange_csvs_dict = interchange_csvs_dict
        self.convert_key_float_dict = convert_key_float_dict
        self.criteria_name = criteria_name
        criteria = criteria_dict[criteria_name]
        """key: main_linkstos + 'others' """
        self.inclusion_dict, self.inclusion_dict_processed = self._inclusion_dict(criteria, data_path)

        self.value_convert = value_convert
        self.unit_convert = unit_convert
        self.clipping = clipping
        self._prepare_encoder()

        # [ADDITION] 병렬 처리를 위한 Lookup Table 캐싱
        self._cache_flattened_rules = {}

        for k, v in self.inclusion_dict.items():
            print('Incusion features', k, len(v))

    def _inclusion_dict(self, criteria, data_path):
        inclusion_dict = {} # Input 기준
        inclusion_dict_processed = {} # Output 기준. tokenizer에 넣을 config 만들 용도

        for main_linksto in self.main_linkstos:
            assert main_linksto in criteria.keys(), "No such linksto: " + main_linksto
            min_num = criteria[main_linksto]['count_threshold']
            criterion_inclusion_set = criteria[main_linksto]['inclusion_key']
            criterion_exclusion_set = criteria[main_linksto]['exclusion_key']
            criterion_inclusion_set = {int(k.split('||', 1)[0]) for k in criterion_inclusion_set}
            criterion_exclusion_set = {int(k.split('||', 1)[0]) for k in criterion_exclusion_set}

            with open(data_path+f'/unit_value_dicts/{main_linksto}_unit_value_dict_update.pkl', "rb") as f:
                chartevents_unit_value_dict = pickle.load(f) # It has 'float', ('binary',) 'string' as key
            merged = {k: v for d in chartevents_unit_value_dict.values() for k, v in d.items()}
            print("########")
            #print(merged)

            inclusion_list = []
            for key_, value_ in merged.items():
                counter = next(iter(value_.values()))
                if sum(counter.values())>=min_num:
                    inclusion_list.append(int(key_.split('||', 1)[0]))
            inclusion_set = (set(inclusion_list) | criterion_inclusion_set)-criterion_exclusion_set
            """여기까지 해서 output 기준 inclusion itemid 만듬"""
            inclusion_set_processed = inclusion_set.copy()
            inclusion_dict_processed[main_linksto] = list(inclusion_set_processed)
            """interchange_csvs --> convert_key_float 을 사용해서 역방향 itemid 탐색"""
            if main_linksto in self.interchange_csvs_dict.keys():
                interchange_dict = defaultdict(list)
                for k, v in self.interchange_csvs_dict[main_linksto].items():
                    v_key = int(v['key'].split('||', 1)[0])
                    k_key = int(k.split('||', 1)[0])
                    interchange_dict[v_key].append(k_key)
                # 필요하면 일반 dict로 변환
                interchange_dict = dict(interchange_dict)
                for itemid in inclusion_set.copy():
                    if itemid in interchange_dict:
                        inclusion_set.update(interchange_dict[itemid])
                        #print(f'[interchange_csvs] Add {interchange_dict.get(itemid)}')
            if main_linksto in self.convert_key_float_dict.keys():
                convert_dict = defaultdict(list)
                for k, v in self.convert_key_float_dict[main_linksto].items():
                    v_key = int(v['key'].split('||', 1)[0])
                    k_key = int(k.split('||', 1)[0])
                    convert_dict[v_key].append(k_key)
                # 필요하면 일반 dict로 변환
                convert_dict = dict(convert_dict)
                for itemid in inclusion_set.copy():
                    if itemid in convert_dict:
                        inclusion_set.update(convert_dict[itemid])
                        #print(f'[convert_key_float] Add {convert_dict.get(itemid)}')

            inclusion_dict[main_linksto] = list(inclusion_set)

        itemid_list = [
            v['itemid']
            for v in self.my_itemid.values()
            if isinstance(v, dict) and 'itemid' in v
        ]
        inclusion_dict['others'] = itemid_list

        return inclusion_dict, inclusion_dict_processed

    def _prepare_encoder(self):
        """먼저 value_convert에서 inclusion_dict에 있는 애들만 남김 + inclusion_dict에도 value_convert에 있는 애들만 남김"""
        for main_linksto in self.main_linkstos:
            self.value_convert[main_linksto] = {
                int(k.split('||', 1)[0]): v
                for k, v in self.value_convert[main_linksto].items()
            }

            int_key_intersectin = set(self.inclusion_dict[main_linksto]) & set(self.value_convert[main_linksto].keys())
            self.inclusion_dict[main_linksto] = list(int_key_intersectin)

            self.value_convert[main_linksto] = {
                k: v
                for k, v in self.value_convert[main_linksto].items()
                if k in int_key_intersectin
            }

            self.unit_convert[main_linksto] = {
                int(k.split('||', 1)[0]): v
                for k, v in self.unit_convert[main_linksto].items()
            }
            self.clipping[main_linksto] = {
                int(k.split('||', 1)[0]): v
                for k, v in self.clipping[main_linksto].items()
            }
            self.convert_key_float_dict[main_linksto] = { # 밖 / 안 key 모두 int로 변경
                int(k.split('||', 1)[0]): {
                    **v,
                    'key': int(v['key'].split('||', 1)[0])
                }
                for k, v in self.convert_key_float_dict[main_linksto].items()
            }
            if main_linksto in self.interchange_csvs_dict:
                self.interchange_csvs_dict[main_linksto] = {  # 밖 / 안 key 모두 int로 변경
                    int(k.split('||', 1)[0]): {
                        **v,
                        'key': int(v['key'].split('||', 1)[0])
                    }
                    for k, v in self.interchange_csvs_dict[main_linksto].items()
                }
            print(f'{main_linksto} unit_convert', len(self.unit_convert[main_linksto]), end = '')
            self.unit_convert[main_linksto] = {
                k: v
                for k, v in self.unit_convert[main_linksto].items()
                if k in int_key_intersectin
            }
            print('->', len(self.unit_convert[main_linksto]))
            print(f'{main_linksto} clipping', len(self.clipping[main_linksto]), end = '')
            self.clipping[main_linksto] = {
                k: v
                for k, v in self.clipping[main_linksto].items()
                if k in int_key_intersectin
            }
            print('->', len(self.clipping[main_linksto]))
            print(f'{main_linksto} convert_key_float', len(self.convert_key_float_dict[main_linksto]), end='')
            self.convert_key_float_dict[main_linksto] = {
                k: v
                for k, v in self.convert_key_float_dict[main_linksto].items()
                if k in int_key_intersectin
            }
            print('->', len(self.convert_key_float_dict[main_linksto]))

    def encode(self, itemid, value, valueuom, linksto):
        itemid = int(itemid)
        value = str(value)
        valueuom = str(valueuom)

        if itemid >= 1000000:
            if (itemid == my_itemid['Question']['itemid']) and (int(value) not in self.inclusion_dict[linksto]):
                return None, None, None, None
            else:
                return str(itemid), value, valueuom, linksto

        assert linksto in main_linkstos
        if itemid not in self.inclusion_dict[linksto]:
            return None, None, None, None

        """ 1. Value drop """
        if value in self.value_convert[linksto][itemid]['drop']:
            return None, None, None, None
        """ 2. Unit drop """
        if valueuom in self.unit_convert[linksto].get(itemid, {}).get('drop', []):
            return None, None, None, None

        """ 1. Value convert """
        value = self.value_convert[linksto][itemid]['convert'].get(value, value)
        value = float(value)
        if np.isnan(value):
            return None, None, None, None

        """ 2. Unit convert  """
        tmp = self.unit_convert[linksto].get(itemid, {}).get('convert', {}).get(valueuom)
        if tmp is not None:
            if isinstance(tmp, list):
                valueuom = tmp[0]
                value = tmp[1](value)
            else:
                valueuom = tmp

        """ 3. Clipping """
        if itemid in self.clipping[linksto].keys():
            if (value < self.clipping[linksto][itemid]['inclusion'][0]) or (value > self.clipping[linksto][itemid]['inclusion'][1]):
                return None, None, None, None

        """ 4. ID/Value conversion with a) convert_key_float / b) interchage_csvs """
        # a) convert_key_float
        if itemid in self.convert_key_float_dict[linksto]:
            value = self.convert_key_float_dict[linksto][itemid]['convert'](value)
            valueuom = self.convert_key_float_dict[linksto][itemid]['unit']
            itemid = self.convert_key_float_dict[linksto][itemid]['key']

        # a) interchage_csvs
        if linksto in self.interchange_csvs_dict:
            if itemid in self.interchange_csvs_dict[linksto]:
                value = self.interchange_csvs_dict[linksto][itemid]['convert'](value)
                valueuom = self.interchange_csvs_dict[linksto][itemid]['unit']
                itemid = self.interchange_csvs_dict[linksto][itemid]['key']

        raise "QA 에서 question (itemid 2000000) 과 answer (그 다음 row) 가 세트로 있어야 하지만 이는 row 하나씩 받아서 그 메커니즘은 밖에서 해줘야함"
        return str(itemid), value, valueuom, linksto

    # --------------------------------------------------------------------------
    # Helper: 규칙을 벡터 연산용으로 변환 (String 변환 로직 반영)
    # --------------------------------------------------------------------------
    def _get_flattened_rules(self, linksto):
        if linksto in self._cache_flattened_rules:
            return self._cache_flattened_rules[linksto]

        # 1. Value Drop Set
        # encode 함수에서 value = str(value)를 먼저 수행하므로,
        # 규칙에 있는 값들도 모두 string으로 변환해서 저장해야 매칭됨.
        value_drop_set = set()

        # 2. Value Convert Map
        value_convert_map = {}

        for itemid, rules in self.value_convert[linksto].items():
            if 'drop' in rules:
                for v in rules['drop']:
                    value_drop_set.add((itemid, str(v)))  # str 변환 필수
            if 'convert' in rules:
                for old_v, new_v in rules['convert'].items():
                    # value=str(value) 로직에 맞춤
                    value_convert_map[(itemid, str(old_v))] = new_v

        # 3. Unit Drop Set
        unit_drop_set = set()
        for itemid, rules in self.unit_convert[linksto].items():
            if 'drop' in rules:
                for u in rules['drop']:
                    unit_drop_set.add((itemid, str(u)))  # str 변환

        # 4. Clipping DataFrame (숫자 범위이므로 str 변환 불필요)
        clip_data = []
        for itemid, rules in self.clipping[linksto].items():
            if 'inclusion' in rules:
                clip_data.append({
                    'itemid': itemid,
                    'min_val': rules['inclusion'][0],
                    'max_val': rules['inclusion'][1]
                })
        df_clip = pd.DataFrame(clip_data) if clip_data else pd.DataFrame(columns=['itemid', 'min_val', 'max_val'])

        self._cache_flattened_rules[linksto] = {
            'value_drop_set': value_drop_set,
            'value_convert_map': value_convert_map,
            'unit_drop_set': unit_drop_set,
            'df_clip': df_clip
        }
        return self._cache_flattened_rules[linksto]

    # --------------------------------------------------------------------------
    # Main Function: Parallel Execution
    # --------------------------------------------------------------------------
    def encode_parallel(self, df, linksto_strict=True):
        """
        Input: df (pd.DataFrame)
        Output: df (Cleaning 후, Q-A 종속성 반영 및 원본 Index 유지)
        """
        df = df.copy()

        # 0. 초기 강제 문자열 변환 및 전처리
        df['itemid'] = df['itemid'].astype(str)
        df['value'] = df['value'].astype(str)
        df['valueuom'] = df['valueuom'].astype(str)
        df['_itemid_int'] = pd.to_numeric(df['itemid'], errors='coerce').fillna(-1).astype(int)

        # ----------------------------------------------------------------------
        # 1. Split Data (Index 유지)
        # ----------------------------------------------------------------------
        mask_high = df['_itemid_int'] >= 1_000_000

        df_pass = df[mask_high].copy()  # Question 후보군
        df_proc = df[~mask_high].copy()  # Answer 후보군

        # ======================================================================
        # 2. Process Low IDs (Answer) FIRST
        # ======================================================================
        processed_chunks = []

        if not df_proc.empty:
            for linksto_val, group in df_proc.groupby('linksto'):

                # [수정] linksto_strict 옵션에 따라 검사할 linksto 목록 결정
                if linksto_strict:
                    if linksto_val not in self.main_linkstos:
                        continue
                    target_linkstos = [linksto_val]
                else:
                    # 잘못 기재된 linksto를 무시하고 가능한 모든 linksto에 대해 검사
                    target_linkstos = self.main_linkstos

                # [추가] 아직 처리되지 않은 남은 데이터들을 추적하기 위한 복사본
                remaining_group = group.copy()

                for real_lt in target_linkstos:
                    # [추가] 남은 데이터가 없으면 불필요한 루프 조기 종료
                    if remaining_group.empty:
                        break

                    rules = self._get_flattened_rules(real_lt)

                    # (A) Inclusion Filtering (remaining_group에서 필터링)
                    valid_ids = set(self.inclusion_dict[real_lt])

                    # 현재 real_lt에 속하는 데이터의 마스크 생성
                    match_mask = remaining_group['_itemid_int'].isin(valid_ids)
                    sub_group = remaining_group[match_mask].copy()

                    # [핵심] 이번 루프에서 매칭된 데이터는 남은 그룹에서 제외시켜 중복 방지
                    remaining_group = remaining_group[~match_mask]

                    if sub_group.empty: continue

                    # (B) Value Drop
                    keys = list(zip(sub_group['_itemid_int'], sub_group['value']))
                    mask_drop = [k in rules['value_drop_set'] for k in keys]
                    sub_group = sub_group[~np.array(mask_drop)]
                    if sub_group.empty: continue

                    # (C) Unit Drop (linksto_strict가 True일 때만 실행)
                    if linksto_strict:
                        keys_uom = list(zip(sub_group['_itemid_int'], sub_group['valueuom']))
                        mask_unit_drop = [k in rules['unit_drop_set'] for k in keys_uom]
                        sub_group = sub_group[~np.array(mask_unit_drop)]
                        if sub_group.empty: continue

                    # (D) Value Convert & Type Casting & Explicit NaN Drop
                    new_values = [
                        rules['value_convert_map'].get((i, v), v)
                        for i, v in zip(sub_group['_itemid_int'], sub_group['value'])
                    ]
                    sub_group['value'] = new_values
                    sub_group['value'] = pd.to_numeric(sub_group['value'], errors='coerce')
                    sub_group = sub_group.dropna(subset=['value'])
                    if sub_group.empty: continue

                    # (E) Unit Convert (linksto_strict가 True일 때만 실행)
                    if linksto_strict:
                        unit_convert_dict = self.unit_convert[real_lt]
                        target_ids = set(sub_group['_itemid_int']) & set(unit_convert_dict.keys())
                        for uid in target_ids:
                            u_rules = unit_convert_dict[uid].get('convert', {})
                            if not u_rules: continue
                            mask_uid = sub_group['_itemid_int'] == uid
                            existing_units = sub_group.loc[mask_uid, 'valueuom'].unique()
                            for unit_str in existing_units:
                                if unit_str in u_rules:
                                    rule = u_rules[unit_str]
                                    mask_unit = mask_uid & (sub_group['valueuom'] == unit_str)
                                    if isinstance(rule, list):
                                        new_u, func = rule[0], rule[1]
                                        sub_group.loc[mask_unit, 'value'] = sub_group.loc[mask_unit, 'value'].apply(
                                            func)
                                        sub_group.loc[mask_unit, 'valueuom'] = new_u
                                    else:
                                        sub_group.loc[mask_unit, 'valueuom'] = rule

                    # (F) Clipping
                    df_clip = rules['df_clip']
                    if not df_clip.empty:
                        sub_group = sub_group.reset_index()
                        group_merged = sub_group.merge(df_clip, left_on='_itemid_int', right_on='itemid', how='left',
                                                       suffixes=('', '_clip'))
                        cond_min = group_merged['min_val'].notna() & (group_merged['value'] < group_merged['min_val'])
                        cond_max = group_merged['max_val'].notna() & (group_merged['value'] > group_merged['max_val'])
                        valid_clip_mask = ~(cond_min | cond_max)
                        sub_group = group_merged[valid_clip_mask].copy()
                        sub_group = sub_group.set_index('index')
                        sub_group.index.name = None
                        sub_group = sub_group.drop(columns=['min_val', 'max_val', 'itemid_clip'], errors='ignore')

                    # (G) ID Chaining
                    # 1. convert_key_float
                    if real_lt in self.convert_key_float_dict:
                        ckf_dict = self.convert_key_float_dict[real_lt]
                        target_ids = set(sub_group['_itemid_int']) & set(ckf_dict.keys())
                        for tid in target_ids:
                            info = ckf_dict[tid]
                            mask = sub_group['_itemid_int'] == tid
                            sub_group.loc[mask, 'value'] = sub_group.loc[mask, 'value'].apply(info['convert'])
                            sub_group.loc[mask, 'valueuom'] = info['unit']
                            new_key = int(info['key'])
                            sub_group.loc[mask, 'itemid'] = str(new_key)
                            sub_group.loc[mask, '_itemid_int'] = new_key

                    # 2. interchange_csvs
                    if real_lt in self.interchange_csvs_dict:
                        ic_dict = self.interchange_csvs_dict[real_lt]
                        target_ids = set(sub_group['_itemid_int']) & set(ic_dict.keys())
                        for tid in target_ids:
                            info = ic_dict[tid]
                            mask = sub_group['_itemid_int'] == tid
                            sub_group.loc[mask, 'value'] = sub_group.loc[mask, 'value'].apply(info['convert'])
                            sub_group.loc[mask, 'valueuom'] = info['unit']
                            new_key = int(info['key'])
                            sub_group.loc[mask, 'itemid'] = str(new_key)
                            sub_group.loc[mask, '_itemid_int'] = new_key

                    processed_chunks.append(sub_group)

        # 생존한 Answer 데이터프레임
        if processed_chunks:
            df_proc_cleaned = pd.concat(processed_chunks).sort_index()
        else:
            df_proc_cleaned = pd.DataFrame(columns=df.columns)

        # ======================================================================
        # 3. Process High IDs (Question Logic with Strict Dependency)
        # ======================================================================
        question_id = self.my_itemid.get('Question', {}).get('itemid')

        if (question_id is not None) and (not df_pass.empty):
            # (1) 기본 Inclusion Filtering (Input 기준 유효성 검사)
            pass_chunks = []

            if linksto_strict:
                # [기존 로직] linksto가 엄격하게 지켜질 때
                for lt, subg in df_pass.groupby('linksto'):
                    is_question = subg['_itemid_int'] == question_id

                    if (not is_question.any()) or (lt not in self.inclusion_dict):
                        pass_chunks.append(subg)
                        continue

                    q_values = pd.to_numeric(subg.loc[is_question, 'value'], errors='coerce').fillna(-1).astype(int)
                    valid_set = set(self.inclusion_dict[lt])
                    is_valid_value = q_values.isin(valid_set)

                    mask_drop = pd.Series(False, index=subg.index)
                    mask_drop.loc[is_question] = ~is_valid_value
                    pass_chunks.append(subg[~mask_drop])
            else:
                # [수정된 로직] linksto가 무작위일 때 (groupby를 신뢰하지 않음)
                # 전체 df_pass를 대상으로 모든 가능한 inclusion_dict의 합집합(union)으로 검사
                is_question = df_pass['_itemid_int'] == question_id

                if is_question.any():
                    q_values = pd.to_numeric(df_pass.loc[is_question, 'value'], errors='coerce').fillna(-1).astype(
                        int)

                    # 모든 가능한 valid_ids의 합집합 생성
                    all_valid_ids = set()
                    for valid_ids in self.inclusion_dict.values():
                        all_valid_ids.update(valid_ids)

                    is_valid_value = q_values.isin(all_valid_ids)

                    mask_drop = pd.Series(False, index=df_pass.index)
                    mask_drop.loc[is_question] = ~is_valid_value
                    pass_chunks.append(df_pass[~mask_drop])
                else:
                    pass_chunks.append(df_pass)

            if pass_chunks:
                df_pass = pd.concat(pass_chunks).sort_index()
            else:
                df_pass = pd.DataFrame(columns=df.columns)

            # (2) Question-Answer Dependency & Update Logic
            if not df_pass.empty:
                is_question = df_pass['_itemid_int'] == question_id

                if is_question.any():
                    q_indices = df_pass.index[is_question]
                    expected_a_indices = q_indices + 1

                    # [Check DF 생성]
                    check_df = pd.DataFrame({
                        'q_idx': q_indices,
                        'a_idx': expected_a_indices,
                        'q_val': df_pass.loc[q_indices, 'value'].values  # 현재 값 (Old ID)
                    })

                    # -------------------------------------------------------------
                    # [FIX] suffixes에 의존하지 않고 명시적으로 rename 후 merge
                    # -------------------------------------------------------------

                    # 1. 생존한 Answer 정보 (Final ID 확인용)
                    final_answer_ids = df_proc_cleaned[['itemid']].rename(columns={'itemid': 'itemid_a_final'})

                    merged_check = check_df.merge(
                        final_answer_ids,
                        left_on='a_idx',
                        right_index=True,
                        how='left'
                    )

                    # 2. 원본 Answer ID (매칭 검증용)
                    orig_answer_ids = df[['itemid']].rename(columns={'itemid': 'itemid_a_orig'})

                    merged_check = merged_check.merge(
                        orig_answer_ids,
                        left_on='a_idx',
                        right_index=True,
                        how='left'
                    )

                    # [조건 A] Answer가 살아있는가? (itemid_a_final 컬럼 존재 및 NaN 아님)
                    cond_alive = merged_check['itemid_a_final'].notna()

                    # [조건 B] Question 값이 Answer의 "원본" ID와 일치하는가?
                    cond_match = merged_check['q_val'] == merged_check['itemid_a_orig'].astype(str)

                    valid_mask = cond_alive & cond_match

                    # [업데이트] 살아남을 Question의 value를 "최종 Answer ID"로 갱신
                    if valid_mask.any():
                        valid_updates = merged_check[valid_mask]
                        # q_idx를 인덱스로, itemid_a_final(새 ID)을 값으로 매핑
                        update_map = valid_updates.set_index('q_idx')['itemid_a_final']

                        # df_pass 값 업데이트
                        df_pass.loc[update_map.index, 'value'] = update_map

                    # [필터링] 유효하지 않은 Question 제거
                    valid_q_indices = merged_check.loc[valid_mask, 'q_idx'].values
                    final_mask = (~is_question) | (df_pass.index.isin(valid_q_indices))
                    df_pass = df_pass[final_mask]

        # ----------------------------------------------------------------------
        # Final Merge
        # ----------------------------------------------------------------------
        df_cleaned = pd.concat([df_proc_cleaned, df_pass])

        if '_itemid_int' in df_cleaned.columns:
            df_cleaned = df_cleaned.drop(columns=['_itemid_int'])

        # [추가] itemid 컬럼이 float(예: 123.0)으로 풀리는 것을 방지하고 int로 강제 변환
        # 문자열로 된 숫자나 float 형태를 모두 안전하게 숫자로 바꾼 뒤 int로 캐스팅합니다.
        df_cleaned['itemid'] = pd.to_numeric(df_cleaned['itemid'], errors='coerce').fillna(-1).astype(int)

        return df_cleaned.sort_index()


""" qa_dataset에서 사용될 수 있도록 {'50971': {'type': 'numeric_bin', 'bins': [3.2, 3.5, 3.8, 4.1, 4.34, 4.7, 5.0, 5.3, 5.7]},...} 이런식으로 만듬 """
from mimic4preprocessing.my_itemid import my_itemid
from pathlib import Path

def _rearrange_config_dict(obj):
    """
    obj가 dict이면:
        key는 str (숫자 의미)
        1) 1_000_000 이상 key 먼저 (오름차순)
        2) 그 다음 1_000_000 미만 key (오름차순)

    obj가 list이면:
        1) 중복 제거
        2) 동일 기준으로 정렬

    반환:
        dict -> dict (key는 str 유지)
        list -> list
    """
    def sort_key(x):
        return (0 if int(x) >= 1_000_000 else 1, int(x))

    # 🔹 dict 처리
    if isinstance(obj, dict):
        sorted_items = sorted(
            obj.items(),
            key=lambda kv: sort_key(kv[0])
        )
        return dict(sorted_items)

    # 🔹 list 처리
    elif isinstance(obj, list):
        unique_lst = list(set(obj))
        return sorted(unique_lst, key=sort_key)

    else:
        raise TypeError("Input must be dict or list")
def _create_dataset_config(pkl_name, inclusion_dict): # pkl_name : 'bin10_weightTrue_exp0_th10'
    config_dict = {}
    tags = []
    base_dir = Path(__file__).resolve().parent
    pkl_path = base_dir / "unit_value_cleaning" / "data"
    for linksto, itemid_list in inclusion_dict.items():
        with open(pkl_path/ f"{linksto}_{pkl_name}.pkl", "rb") as f:
            data = pickle.load(f)
            # print(data.keys())
            # print(data[227969].keys())
            # print(data[227969])
            # raise AttributeError
        for itemid in itemid_list:
            config_dict[str(itemid)] = {'type': f'numeric_bin{"" if data[itemid]['tag'] == "float" else "_string"}', 'bins': data[itemid]['thresholds']}
            tags.append(str(itemid))

    for key_, value_ in my_itemid.items():
        if isinstance(value_, dict):
            config_dict[str(value_['itemid'])] = {'type': 'categorical', 'vocab_list': value_['values']}

    """Question (itemid 2000000) 의 value는 inclusion_dict에 있는 itemid들이 되어야 함"""
    assert set(tags) == set([str(x) for x in set().union(*inclusion_dict.values())])
    config_dict[str(my_itemid['Question']['itemid'])]['vocab_list'] = _rearrange_config_dict(tags)

    #### Key 순서 arrange ####
    config_dict = _rearrange_config_dict(config_dict)

    return config_dict


if __name__ == '__main__':
    datapath = 'mimic4preprocessing/unit_value_cleaning/data/'

    processer = key_value_unit_processer('criteria1', datapath)

    print(processer.inclusion_dict_processed) # total 250
    print(len(processer.inclusion_dict_processed['chartevents'])) #134
    print(len(processer.inclusion_dict_processed['labevents'])) # 107
    print(len(processer.inclusion_dict_processed['omr'])) # 5
    print(len(processer.inclusion_dict_processed['outputevents'])) # 4

    print(processer.inclusion_dict) # total 277+11(metas)
    print(len(processer.inclusion_dict['chartevents'])) #148
    print(len(processer.inclusion_dict['labevents'])) # 120
    print(len(processer.inclusion_dict['omr'])) # 5
    print(len(processer.inclusion_dict['outputevents'])) # 4

    print(set(processer.inclusion_dict['chartevents'])-set(processer.inclusion_dict_processed['chartevents'])) # 14
    #{225312, 220227, 226531, 226534, 227464, 226536, 226537, 226540, 226512, 223761, 226707, 226329, 225309, 225310}
    print(set(processer.inclusion_dict_processed['chartevents']) - set(processer.inclusion_dict['chartevents'])) #0

    print(set(processer.inclusion_dict['labevents']) - set(processer.inclusion_dict_processed['labevents']))
    print(set(processer.inclusion_dict_processed['labevents']) - set(processer.inclusion_dict['labevents']))

    print(set(processer.inclusion_dict['omr']) - set(processer.inclusion_dict_processed['omr'])) # {226707}
    print(set(processer.inclusion_dict_processed['omr']) - set(processer.inclusion_dict['omr'])) # {226730}

    print(set(processer.inclusion_dict['outputevents']) - set(processer.inclusion_dict_processed['outputevents']))
    print(set(processer.inclusion_dict_processed['outputevents']) - set(processer.inclusion_dict['outputevents']))

    _create_dataset_config('bin10_weightTrue_exp0_th10', processer.inclusion_dict_processed)



    sorted_dict = {k: sorted(v) for k, v in processer.inclusion_dict.items()}
    print(sorted_dict)  # total 250

    print(processer.inclusion_dict['omr'])

    path = "../mimic4preprocessing/resources/itemid_to_variable_map.csv"

    effective_itemid = set(processer.inclusion_dict['chartevents'])|set(processer.inclusion_dict['labevents'])|set(processer.inclusion_dict['omr'])|set(processer.inclusion_dict['outputevents']) # 4
    effective_itemid_195 = set(processer.inclusion_dict_processed['chartevents'])|set(processer.inclusion_dict_processed['labevents'])|set(processer.inclusion_dict_processed['omr'])|set(processer.inclusion_dict_processed['outputevents']) # 4


    df = pd.read_csv(path)

    # 2. 필터링할 effective_itemid 리스트 정의 (예시 데이터)
    # 실제 사용하시는 리스트로 대체하세요.
    effective_itemid = list(effective_itemid)
    effective_itemid_195 = list(effective_itemid_195)

    # 3. ITEMID 열의 값이 리스트 안에 있는 행만 추출
    # 만약 csv의 ITEMID가 문자열로 읽혔을 경우를 대비해 astype(int) 처리를 하거나
    # 리스트 요소 형식을 맞추는 것이 좋습니다.
    filtered_df = df[df['ITEMID'].isin(effective_itemid)]
    filtered_df_195 = df[df['ITEMID'].isin(effective_itemid_195)]

    # 4. 같은 위치에 새로운 파일명으로 저장
    output_path = '../mimic4preprocessing/resources/effective_itemids_273.csv'
    filtered_df.to_csv(output_path, index=False)

    output_path = '../mimic4preprocessing/resources/effective_itemids_195.csv'
    filtered_df_195.to_csv(output_path, index=False)


    print(f"필터링 완료! 저장된 행 개수: {len(filtered_df)}")