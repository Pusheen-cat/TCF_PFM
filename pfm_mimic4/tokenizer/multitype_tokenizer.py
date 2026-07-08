import argparse

import numpy as np
import torch
from transformers import AutoTokenizer
from typing import Dict, List, Tuple, Union, Any, Optional
import bisect
from datetime import datetime
import pandas as pd
import re
from typing import List, Union
from pfm_mimic4.tokenizer.tokenizing_setting import token_bin_range


class CategoricalTokenizer:
    """정해진 카테고리 토큰들을 위한 토크나이저"""

    def __init__(self, vocab_list):
        """
        vocab_list: 허용되는 토큰들의 리스트
        예: ['<v_sbp>', '<setting_1>', '<t_pipp>', '<unknown>']
        TODO! MIMIC4 ver에서 우리는 vocab_list가 dict 및 None 인 경우도 처리하도록 업데이트
        """
        self.vocab_list = vocab_list
        self.token_to_id = {}
        self.id_to_token = {}


        # 어휘 사전 구축
        if isinstance(self.vocab_list, list):
            for i, token in enumerate(vocab_list):
                self.token_to_id[token] = i
                self.id_to_token[i] = token
            self.vocab_size = len(self.id_to_token)
        elif isinstance(self.vocab_list, dict):
            for str_value, idx in self.vocab_list.items():
                if idx not in self.id_to_token:
                    self.id_to_token[idx] = str_value
            self.token_to_id = self.vocab_list
            self.vocab_size = len(self.id_to_token)
        elif self.vocab_list==None:
            self.token_to_id = None
            self.id_to_token = None
            self.vocab_size = 1
        else:
            raise NotImplementedError


        # <unknown> 토큰이 없으면 추가
        if (self.token_to_id is not None) and ('<unknown>' not in self.token_to_id):
            self.token_to_id['<unknown>'] = self.vocab_size
            self.id_to_token[self.vocab_size] = '<unknown>'
            self.vocab_size += 1

    def encode(self, tokens: List[str]) -> List[int]:
        """문자열 토큰들을 ID로 변환"""
        if self.token_to_id is None:
            return [0]*len(tokens)

        token_ids = []
        for token in tokens:
            token_ids.append(self.token_to_id.get(token, self.token_to_id['<unknown>']))

        return token_ids

    def decode(self, token_ids: List[int]) -> List[str]:
        """토큰 ID들을 문자열로 변환"""
        if self.id_to_token is None:
            return ['']*len(token_ids)

        tokens = []
        for token_id in token_ids:
            tokens.append(self.id_to_token[token_id])

        return tokens

    def get_vocab(self) -> Dict[str, int]:
        """어휘 사전 반환"""
        return self.token_to_id.copy()


class NumericBinTokenizer:
    def __init__(self, thresholds):
        """
        숫자를 bin으로 분류하는 토크나이저

        Args:
            thresholds (list): 증가하는 순서의 threshold 값들 (각 bin 사이의 경계값)
        """
        self.thresholds = sorted(thresholds)  # 안전을 위해 정렬
        self.num_bins = len(thresholds) + 1
        self.vocab_size = self.num_bins

    def encode(self, values):
        """
        숫자 값들의 리스트를 bin index들의 리스트로 변환

        Args:
            values (list): 변환할 숫자 값들의 리스트

        Returns:
            list: bin index들의 리스트
        """
        # result = []
        # for value in values:
        #     for i, threshold in enumerate(self.thresholds):
        #         if value < threshold:
        #             result.append(i)
        #             break
        #     else:
        #         result.append(len(self.thresholds))  # 마지막 bin
        # return result
        # TODO --- 기존 비효율적 코드
        # 입력값을 numpy 배열로 변환
        values = np.array(values)

        # searchsorted를 호출하여 각 값에 대한 bin index를 한 번에 계산
        # side='right'는 기존 코드의 '<' 비교와 동일한 결과를 줍니다.
        # [10, 20, 30] 이고 값이 20이면, 20 < 30 이므로 index 2를 반환
        indices = np.searchsorted(self.thresholds, values, side='right')

        # 원래 함수의 반환 타입과 맞추기 위해 list로 변환
        return indices.tolist()

    def decode(self, bin_indices):
        """
        bin index들의 리스트를 문자열 표현들의 리스트로 변환

        Args:
            bin_indices (list): bin index들의 리스트

        Returns:
            list: bin 범위를 나타내는 문자열들의 리스트
        """
        result = []
        for bin_index in bin_indices:
            if bin_index < 0 or bin_index >= self.num_bins:
                raise ValueError(f"bin_index는 0부터 {self.num_bins - 1} 사이여야 합니다.")

            if bin_index == 0:
                # 첫 번째 bin: ~threshold[0]
                result.append(f"<~{self.thresholds[0]}>")
            elif bin_index == len(self.thresholds):
                # 마지막 bin: threshold[-1]~
                result.append(f"<{self.thresholds[-1]}~>")
            else:
                # 중간 bin: threshold[i-1]~threshold[i]
                result.append(f"<{self.thresholds[bin_index - 1]}~{self.thresholds[bin_index]}>")

        return result

class NumericBinStringTokenizer:
    def __init__(self, thresholds, share_bin = True):
        """
        숫자를 bin으로 분류하는 토크나이저

        Args:
            thresholds (list): 증가하는 순서의 threshold 값들 (각 bin 사이의 경계값)
            *** NumericBinStringTokenizer 는 threshold가 10개임 (제일 앞 값 추가됨)
        """
        # None 제외 정렬 여부 확인
        thresholds_wo_none = [t for t in thresholds if t is not None]
        assert thresholds_wo_none == sorted(thresholds_wo_none), f"thresholds must be sorted (excluding None): {thresholds_wo_none}"
        self.thresholds = thresholds if share_bin else thresholds_wo_none # share안하면 효율적으로 압축

        self.value_to_index = {v: i for i, v in enumerate(self.thresholds) if v is not None}

        self.num_bins = len(thresholds) # +1 없음
        self.vocab_size = self.num_bins

    def encode(self, values): # float
        """
        숫자 값들의 리스트를 bin index들의 리스트로 변환

        Args:
            values (list): 변환할 숫자 값들의 리스트

        Returns:
            list: bin index들의 리스트
        """
        return [self.value_to_index[round(v)] for v in values]

    def decode(self, bin_indices):
        """
        bin index들의 리스트를 문자열 표현들의 리스트로 변환

        Args:
            bin_indices (list): bin index들의 리스트

        Returns:
            list: bin 범위를 나타내는 문자열들의 리스트
        """
        result = []
        raise NotImplementedError
        return result

class MultiTypeTokenizer:
    """다양한 타입의 데이터를 처리하는 통합 토크나이저 (timestamp 포함)"""

    def __init__(self, config: Dict[str, Dict], args):
        """
        config 예시:
        {
            'question': {
                'type': 'categorical',
                'vocab_list': ['<v_sbp>', '<v_hr>', '<t_drug>', '<t_doc>']
                #TODO mimimc4 ADD 'vocab_list': {'<v_sbp>':4, '<v_hr>':1, '<t_drug>':4, '<t_doc>':2}
            },
            'meta': {
                'type': 'categorical',
                'vocab_list': ['<birth>', '<F>', '<M>', '<WHITE>', '<ASIAN>']
            },
            't_drug': {
                'type': 'text', #TODO Currently no 'text' format
                'tokenizer_name': 'bert-base-uncased'
            },
            'v_sbp': {
                'type': 'numeric',
                'range_config': {
                    'fine': {'min': 80, 'max': 160, 'step': 0.1},
                    'coarse': {'min': 0, 'max': 500, 'step': 1.0}
                }
            }
        }
        ori# 형태 - digit tokenization의 경우
            'v_sbp': {
                    'type': 'numeric',
                    'decimal': 2
                }
        bin# 형태 - binning tokenization의 경우
            'v_sbp': {
                    'type': 'numeric',
                    'bins': [1,2,3,4,5,6,7,8,8] # 숫자는 오른쪽 bin에 포함
                }
        bin# 형태 - binning tokenization / TODO but with None init
            'v_sbp': {
                    'type': 'numeric_bin_string',
                    'bins': [None, 1,None,3,None,5,None,7,None,8] # 숫자는 오른쪽 bin에 포함
                }
        """
        self.args = args

        self.config = config
        self.tokenizers = {}
        self.type_to_idx = {}  # data type을 index로 매핑
        self.idx_to_type = {}  # index를 data type으로 매핑
        self.type_to_token_offset = {}  # 각 타입의 토큰 오프셋
        self.total_vocab_size = 0

        # Padding constants
        self.PAD_TOKEN_ID = 0
        self.PAD_TIME = 0
        self.PAD_TYPE = 0

        self._initialize_tokenizers()
        self._create_type_mapping()
        self._calculate_token_offsets()

        self.return_float = False  # raw/STRATS float tokenizer removed

    def _initialize_tokenizers(self):
        """각 타입별 토크나이저 초기화"""
        for data_type, type_config in self.config.items(): # data_type: itemid
            if type_config['type'] == 'text': #현재 text는 없음
                tokenizer = AutoTokenizer.from_pretrained(type_config['tokenizer_name'])
                self.tokenizers[data_type] = tokenizer

            elif type_config['type'] == 'categorical':
                tokenizer = CategoricalTokenizer(type_config['vocab_list'])
                self.tokenizers[data_type] = tokenizer

            elif type_config['type'] == 'numeric_bin':
                tokenizer = NumericBinTokenizer(type_config['bins'])
                self.tokenizers[data_type] = tokenizer

            elif type_config['type'] == 'numeric_bin_string': # TODO ADDED in MIMIC4 (String -> int 변환된 애들 처리 위해서)
                tokenizer = NumericBinStringTokenizer(type_config['bins'])
                self.tokenizers[data_type] = tokenizer

            else:
                raise ValueError(f"Unsupported tokenizer type: {type_config['type']}")

    def _create_type_mapping(self):
        """데이터 타입을 인덱스로 매핑"""
        for idx, data_type in enumerate(self.config.keys()): # data_type: meta / downstream_task / v_sbp...
            self.type_to_idx[data_type] = idx
            self.idx_to_type[idx] = data_type

    def _calculate_token_offsets(self):
        """각 타입별 토큰 ID 오프셋 계산"""
        offset = 1 # 0 for pad token
        for idx, data_type in enumerate(self.config.keys()): # data_type: meta / downstream_task / v_sbp...
            tokenizer = self.tokenizers[data_type]
            self.type_to_token_offset[data_type] = offset

            if hasattr(tokenizer, 'vocab_size'):
                vocab_size = tokenizer.vocab_size
            else:
                vocab_size = len(tokenizer.get_vocab())

            self.total_vocab_size = offset+vocab_size

            if (not self.args.share_tokens) | (int(data_type)>=1_000_000):
                offset += vocab_size


    def _timestamp_to_seconds(self, timestamp_str: str) -> int:
        """타임스탬프를 초 단위로 변환"""
        try:
            # pandas를 사용하여 타임스탬프 파싱
            dt = pd.to_datetime(timestamp_str)
            # Unix epoch (1970-01-01)로부터의 초 계산
            return int(dt.timestamp())
        except:
            # 파싱 실패 시 0으로 설정
            return 0

    def _apply_padding_and_truncation(self, encoded_rows: List[List[int]],
                                      encoded_labels:List[np.array],
                                      max_length: Optional[int] = None,
                                      pad_left: bool = False) -> np.array:
        """패딩과 truncation 적용"""
        if max_length is None:
            return np.array(encoded_rows, dtype=float if self.return_float else int), np.array(encoded_labels) if encoded_labels is not None else None

        # Truncation 적용
        if len(encoded_rows) > max_length:
            if pad_left:  # 왼쪽 패딩이면 오른쪽부터 자르기 (최신 데이터 유지)
                encoded_rows = encoded_rows[-max_length:]
            else:  # 오른쪽 패딩이면 왼쪽부터 자르기 (초기 데이터 유지)
                encoded_rows = encoded_rows[:max_length]

        # Padding 적용
        if len(encoded_rows) < max_length:
            pad_length = max_length - len(encoded_rows)
            pad_row = [self.PAD_TIME, self.PAD_TYPE, self.PAD_TOKEN_ID, np.ones_like(encoded_rows[0][3])*-100]

            if pad_left:
                # 왼쪽에 패딩 추가
                padded_rows = [pad_row] * pad_length + encoded_rows
            else:
                # 오른쪽에 패딩 추가
                padded_rows = encoded_rows + [pad_row] * pad_length

            encoded_rows = padded_rows

        if encoded_labels is not None:
            # Truncation 적용
            if len(encoded_labels) > max_length:
                if pad_left:  # 왼쪽 패딩이면 오른쪽부터 자르기 (최신 데이터 유지)
                    encoded_labels = encoded_labels[-max_length:]
                else:  # 오른쪽 패딩이면 왼쪽부터 자르기 (초기 데이터 유지)
                    encoded_labels = encoded_labels[:max_length]

            # Padding 적용
            if len(encoded_labels) < max_length:
                pad_length = max_length - len(encoded_labels)
                pad_row = np.ones_like(encoded_labels) * -100

                if pad_left:
                    # 왼쪽에 패딩 추가
                    padded_rows = [pad_row] * pad_length + encoded_labels
                else:
                    # 오른쪽에 패딩 추가
                    padded_rows = encoded_labels + [pad_row] * pad_length

                encoded_labels = padded_rows


        return np.array(encoded_rows, dtype=float if self.return_float else int), np.array(encoded_labels, dtype=int)

    def encode(self, input_data: List[Tuple[str, str, List]],
               label = None,
               max_length: Optional[int] = None,
               pad_left: bool = False) -> np.array:
        """
        전체 입력 데이터 인코딩 (패딩 및 truncation 포함)
        input_data: [('2191-03-15 14:12:00.000000000', 'v_sbp', [170.0]), ...]
        max_length: 최대 시퀀스 길이 (None이면 패딩/truncation 안함)
        pad_left: True이면 왼쪽 패딩, False이면 오른쪽 패딩

        Returns:
            np.array.Tensor: shape (max_length, 4) where each row is [timestamp_sec, tokenizer_idx, token_idx, label numpy]
                         패딩된 부분은 [0, 0, -100, nparray[-100s]
        """
        encoded_rows = []
        encoded_labels = None
        if label is not None:
            encoded_labels = []
            no_label = np.ones_like(label[0]) * -100

        for idx, (timestamp_str, data_type, data) in enumerate(input_data):
            # 타임스탬프를 초로 변환
            timestamp_sec = self._timestamp_to_seconds(timestamp_str)

            # 데이터 타입의 인덱스 가져오기
            if data_type not in self.type_to_idx:
                raise ValueError(f"Unknown data type: {data_type}")
            tokenizer_idx = self.type_to_idx[data_type]

            # 해당 타입의 토크나이저로 인코딩
            tokenizer = self.tokenizers[data_type]
            type_config = self.config[data_type]
            offset = self.type_to_token_offset[data_type]

            if type_config['type'] == 'text':
                # 텍스트는 리스트의 첫 번째 요소만 사용
                text = data[0] if isinstance(data, list) else data
                token_ids = tokenizer.encode(text, add_special_tokens=False)
            elif type_config['type'] == 'numeric':
                # 숫자 데이터 인코딩
                token_ids = tokenizer.encode(data)
            elif type_config['type'] == 'categorical':
                # 카테고리 데이터 인코딩
                token_ids = tokenizer.encode(data)
            elif type_config['type'] == 'numeric_bin':
                # 숫자 데이터 인코딩
                token_ids = tokenizer.encode(data)
            elif type_config['type'] == 'numeric_bin_string':
                # 숫자 데이터 인코딩
                token_ids = tokenizer.encode(data)

            else:
                raise ValueError(f"Unsupported type: {type_config['type']}")

            # 각 토큰에 대해 행 생성 (오프셋 적용)
            gen_token_len = len(token_ids)

            for idx_, token_idx in enumerate(token_ids):
                global_token_idx = token_idx + offset

                if label is not None:
                    if idx_ <gen_token_len-1:
                        one_label = no_label
                    else:
                        one_label = label[idx]
                    encoded_labels.append(one_label)

                encoded_rows.append([timestamp_sec, tokenizer_idx, global_token_idx])


        # 패딩과 truncation 적용
        return self._apply_padding_and_truncation(encoded_rows, encoded_labels, max_length, pad_left)

    def decode(self, encoded_tensor: torch.Tensor) -> List[Tuple[str, str, List]]:
        """
        인코딩된 텐서를 원래 형태로 디코딩 (패딩 토큰 제외)

        Args:
            encoded_tensor: shape (N, 3) tensor [timestamp_sec, tokenizer_idx, global_token_idx]

        Returns:
            List[Tuple[str, str, List]]: [(timestamp_str, data_type, decoded_data), ...]
        """
        if encoded_tensor.dim() != 2 or encoded_tensor.size(1) != 3:
            raise ValueError("Input tensor must have shape (N, 3)")

        # 패딩 토큰 필터링
        mask = encoded_tensor[:, 0] != self.PAD_TIME
        filtered_tensor = encoded_tensor[mask]

        if filtered_tensor.size(0) == 0:
            return []

        # 타임스탬프와 데이터 타입별로 그룹화
        grouped_data = {}

        for row in filtered_tensor:
            timestamp_sec, tokenizer_idx, global_token_idx = row.tolist()

            # 타임스탬프를 문자열로 변환
            timestamp_str = pd.to_datetime(timestamp_sec, unit='s').strftime('%Y-%m-%d %H:%M:%S.%f')

            # 토크나이저 인덱스를 데이터 타입으로 변환
            if tokenizer_idx not in self.idx_to_type:
                raise ValueError(f"Unknown tokenizer index: {tokenizer_idx}")
            data_type = self.idx_to_type[tokenizer_idx]

            # 글로벌 토큰 인덱스를 로컬 토큰 인덱스로 변환
            offset = self.type_to_token_offset[data_type]
            local_token_idx = global_token_idx - offset

            # 그룹 키 생성
            group_key = (timestamp_str, data_type)

            if group_key not in grouped_data:
                grouped_data[group_key] = []
            grouped_data[group_key].append(local_token_idx)

        # 각 그룹을 디코딩
        decoded_items = []

        for (timestamp_str, data_type), token_ids in grouped_data.items():
            tokenizer = self.tokenizers[data_type]
            type_config = self.config[data_type]

            if type_config['type'] == 'text':
                # 텍스트 디코딩
                decoded_text = tokenizer.decode(token_ids, skip_special_tokens=True)
                decoded_data = [decoded_text]
            elif type_config['type'] == 'numeric':
                # 숫자 데이터 디코딩
                decoded_data = tokenizer.decode(token_ids)
            elif type_config['type'] == 'categorical':
                # 카테고리 데이터 디코딩
                decoded_data = tokenizer.decode(token_ids)
            elif type_config['type'] == 'numeric_bin':
                # 카테고리 데이터 디코딩
                decoded_data = tokenizer.decode(token_ids)

            else:
                raise ValueError(f"Unsupported type: {type_config['type']}")

            decoded_items.append((timestamp_str, data_type, decoded_data))

        # 타임스탬프 순서로 정렬
        decoded_items.sort(key=lambda x: x[0])

        return decoded_items

    def get_type_info(self) -> Dict[str, Any]:
        """타입별 정보 반환"""
        info = {}
        tokenizer_ranges = {}
        for data_type in self.config.keys():
            tokenizer = self.tokenizers[data_type]
            if hasattr(tokenizer, 'vocab_size'):
                vocab_size = tokenizer.vocab_size
            else:
                vocab_size = len(tokenizer.get_vocab())

            info[data_type] = {
                'vocab_size': vocab_size,
                'tokenizer_idx': self.type_to_idx[data_type],
                'token_offset': self.type_to_token_offset[data_type],
                'type': self.config[data_type]['type']
            }

            tokenizer_ranges[self.type_to_idx[data_type]] = [self.type_to_token_offset[data_type], self.type_to_token_offset[data_type]+vocab_size]

        info['total_vocab_size'] = self.total_vocab_size
        info['tokenizer_ranges'] = tokenizer_ranges
        return info

    def get_padding_info(self) -> Dict[str, int]:
        """패딩 관련 정보 반환"""
        return {
            'pad_token_id': self.PAD_TOKEN_ID,
            'pad_time': self.PAD_TIME,
            'pad_type': self.PAD_TYPE
        }


# def my_tokens(name): # MIMIC3 ver
#     my_token_dict = {
#         'meta_extra0':18, # its actually 17
#         'meta_extra10':28, # its actually 27
#         'meta_<in_time>':14,
#         'value_initial_idx': 178,
#         'meta_extra0_for_ETHOS': 17,
#         'meta_extra13_for_ETHOS': 30,
#
#         'meta_<adm_time>': 13,
#         'meta_<out_time>': 15,
#         'meta_<dis_time>': 16,
#         'meta_extra20':37, #
#         'meta_extra21':38,
#
#         '<DTask>': 48,
#         '<birth>': 1,
#     }
#     return my_token_dict[name]

def my_tokens(name): # MIMIC4 ver
    my_token_dict = {
        'meta_extra0':50,
        'meta_extra10':60,

        'value_initial_idx': 296,
        'meta_extra0_for_ETHOS': 50,
        'meta_extra13_for_ETHOS': 63,

        'meta_<adm_time>': 3,
        'meta_<in_time>':5,
        'meta_<out_time>': 6,
        'meta_<dis_time>': 4,
        # 'meta_extra20':37, #
        # 'meta_extra21':38,

        '<DTask>': 295,
        '<birth>': 33,

        ## generation ##
        '2nd_feature_idx': 12, # 4- mimic3
        'question_idx': 9, # 2- m3
        'birth_idx': 4,  # 0-m3
        'birth_token': 33, # 1-m3
        'meta_idxs':[0,1,2,3,4,5,6,7,8],

        'feature_startidx': 11, #3
        'feature_endidx': 205

    }
    return my_token_dict[name]

# 사용 예시 및 테스트
def main(args):
    # 설정
    config = {
        'meta': {
            'type': 'categorical',
            'vocab_list': ['<birth>', '<F>', '<M>', '<WHITE>', '<ASIAN>']
        },
        'question': {
            'type': 'categorical',
            'vocab_list': ['<v_sbp>', '<v_hr>', '<t_drug>', '<t_doc>']
        },
        # 't_drug': {
        #     'type': 'text',
        #     'tokenizer_name': 'bert-base-uncased'
        # },
        'v_sbp': {
            'type': 'numeric',
            'range_config': {
                'fine': {'min': 80, 'max': 160, 'step': 0.1},
                'coarse': {'min': 0, 'max': 500, 'step': 1.0}
            }
        },
        'v_hr': {
            'type': 'numeric',
            'range_config': {
                'fine': {'min': 50, 'max': 120, 'step': 0.1},
                'coarse': {'min': 0, 'max': 300, 'step': 1.0}
            }
        },
    }
    config.update(token_bin_range(args))  # 'decimal' for ori#, 'bins' for bin#

    # 토크나이저 초기화
    tokenizer = MultiTypeTokenizer(config, args)

    # 샘플 데이터
    input_data = [
        ('2191-03-12 10:12:00.000000000', 'meta', ['<birth>']),
        ('2191-03-12 10:12:00.000000000', 'meta', ['<M>']),
        ('2191-03-12 10:12:00.000000000', 'meta', ['<WHITE>']),
        ('2191-03-15 14:12:00.000000000', 'question', ['<v_sbp>']),
        ('2191-03-15 14:12:00.000000000', 'v_sbp', [170.0]),
        ('2191-03-15 14:20:00.000000000', 'question', ['<v_sbp>']),
        ('2191-03-15 14:20:00.000000000', 'v_sbp', [150.0]),
        ('2191-03-15 14:30:00.000000000', 'question', ['<v_sbp>']),
        ('2191-03-15 14:30:00.000000000', 'v_sbp', [140.0]),
        # ('2191-03-16 01:30:00.000000000', 'question', ['<t_drug>']),
        # ('2191-03-16 01:30:00.000000000', 't_drug', ['losartan: angiotensin receptor blocker']),
        ('2191-03-16 05:00:00.000000000', 'question', ['<v_hr>']),
        ('2191-03-16 05:00:00.000000000', 'v_hr', [85.5]),
    ]

    print("=== 기본 인코딩 (패딩 없음) ===")
    encoded_tensor = tokenizer.encode(input_data)
    print("Encoded tensor len:", len(encoded_tensor))
    print("Encoded tensor:")
    print(encoded_tensor)

    max_length = 15
    print(f"\n=== 패딩 적용 (max_length={max_length}, pad_left=False) ===")
    encoded_padded = tokenizer.encode(input_data, max_length=max_length, pad_left=False)
    print("Padded tensor shape:", encoded_padded.shape)
    print("Padded tensor:")
    print(encoded_padded)

    print(f"\n=== 패딩 적용 (max_length={max_length}, pad_left=True) ===")
    encoded_padded_left = tokenizer.encode(input_data, max_length=max_length, pad_left=True)
    print("Left-padded tensor shape:", encoded_padded_left.shape)
    print("Left-padded tensor:")
    print(encoded_padded_left)

    max_length = 3
    print(f"\n=== Truncation 테스트 (max_length={max_length}, pad_left=False) ===")
    encoded_truncated = tokenizer.encode(input_data, max_length=max_length, pad_left=False)
    print("Truncated tensor shape:", encoded_truncated.shape)
    print("Truncated tensor:")
    print(encoded_truncated)

    print(f"\n=== Truncation 테스트 (max_length={max_length}, pad_left=True) ===")
    encoded_truncated_left = tokenizer.encode(input_data, max_length=max_length, pad_left=True)
    print("Left-truncated tensor shape:", encoded_truncated_left.shape)
    print("Left-truncated tensor:")
    print(encoded_truncated_left)

    # 디코딩 테스트
    print("\n=== 디코딩 테스트 (패딩된 데이터) ===")
    decoded_data = tokenizer.decode(encoded_padded)
    print("Decoded data:")
    for item in decoded_data:
        print(item)

    # 패딩 정보
    print("\n=== 패딩 정보 ===")
    padding_info = tokenizer.get_padding_info()
    print("Padding info:", padding_info)

    # 타입별 정보 출력
    print("\n=== 타입별 정보 ===")
    type_info = tokenizer.get_type_info()
    for data_type, info in type_info.items():
        if data_type != 'total_vocab_size' and data_type !='tokenizer_ranges':
            print(
                f"{data_type}: idx={info['tokenizer_idx']}, vocab_size={info['vocab_size']}, offset={info['token_offset']}, type={info['type']}")

    print(f"Total vocabulary size: {type_info['total_vocab_size']}")
    print(f"Total tokenizer_ranges: {type_info['tokenizer_ranges']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", type=str, default='bin10_exp1_th10',
                        help='value binning; thresholds live in mimic4preprocessing/unit_value_cleaning/data/ (generated by mimic4preprocessing/unit_value_cleaning/binning/make_bin.py). bin{N}_exp{E}_th{T} = N percentile bins, density-weight exponent E (exp0 = no weighting), weight-clip threshold T. Used: bin10_exp1_th10 [OURS], bin10_exp0_th10 [ETHOS generation baseline]. Also generated: bin10_exp{0.5,1.5,2}_th10.')
    parser.add_argument("--share_tokens", type=int, default=1, help='0 - not share token; use each bin'
                                                                    '1 - share token')
    parser.add_argument("--binning_threshold", type=str,
                        default="/path/to/PFM_data/thresholds/")

    args = parser.parse_args()
    main(args)