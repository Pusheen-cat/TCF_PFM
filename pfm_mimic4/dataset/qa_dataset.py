# get_datasets.py
import os
import sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_DIR)
import pickle
import numpy as np
from torch.utils.data import Dataset
from mimic4preprocessing.key_value_unit_processer import key_value_unit_processer
from pfm_mimic4.dataset.csvs_to_tensor import csv_to_tensor
from pfm_mimic4.dataset.csvs_to_tensor_dt import csv_to_tensor_dt
from pfm_mimic4.dataset.csvs_to_tensor_dt_eicu import csv_to_tensor_dt as csv_to_tensor_dt_eicu
from pfm_mimic4.dataset.add_pos_group import add_position_group
from datetime import datetime
from pfm_mimic4.tokenizer.multitype_tokenizer import my_tokens
from pathlib import Path
import re

def extract_bin_count(bin_str):
    match = re.match(r'bin(\d+)', bin_str)
    if match:
        return int(match.group(1))
    else:
        raise ValueError(f"Invalid bin format: {bin_str}")

class QA_dataset(Dataset):
    def __init__(self, args, tokenizer, processor, is_train = False):
        """
        data: List of (text, target_text) pairs
        tokenizer: tokenizer with encode() method
        """
        """MIMIC 4"""
        self.meta_tokens = np.array(my_tokens('meta_idxs')) # 0 for mimic3
        self.question_token = my_tokens('question_idx') # 9 # 2 for mimic3
        self.downstream_token = 10 # 1 for mimic3
        self.bin_start_idx = my_tokens('feature_startidx') # 11 # 3 for mimic3

        self.objective = args.objective # 'G2DYDTSP' (OURS) or 'NTP' (ETHOS / downstream)
        self.in_pretrain = False
        self.pe_baseline = args.pe_baseline # None (OURS) or 'ETHOS'
        load_share_token = 0 if args.bin.startswith('bin') else args.share_tokens
        load_seq_gen = 'addQ' if args.seq_gen == 'addQ' else 'NOadd'
        bin_count = extract_bin_count(args.bin) # args.bin = 'bin10_exp1_th10', ,,
        self.bin_count = bin_count

        max_length = args.sample_max_length if args.in_pretrain else args.eval_max_length
        overlap = args.sample_overlap if args.in_pretrain else args.eval_overlap

        dataset_setting_dir = f'/max_len_{max_length}_overlap_{overlap}/' \
                              f'feature{args.data}_{args.bin}_share{load_share_token}_{load_seq_gen}{"_ETHOS" if args.pe_baseline == "ETHOS" else ""}/'

        done_name = dataset_setting_dir + f'{"train_done" if is_train else "test_done"}.txt'

        if args.in_pretrain:
            self.in_pretrain = True
            data_dir = args.data_dir
            self.tte_dir = None  # per-event TTE labels were MOTOR-only (removed)
            self.ntp_dir = data_dir+dataset_setting_dir+f'{"train" if is_train else "test"}/'
        else:
            self.in_pretrain = False
            data_dir = args.eval_data_dir
            self.dt_label_dir = data_dir + dataset_setting_dir + f'dt_{"train" if is_train else "test"}/'
            self.ntp_dir = data_dir + dataset_setting_dir + f'{"train" if is_train else "test"}/'

        if os.path.exists(data_dir+done_name):
            print(data_dir, done_name)
            rank = int(os.environ.get("RANK", 0))
            if rank == 0:
                print(f"## Dataset Load: {data_dir + done_name}")
            self.data = {}
            for filename in os.listdir(self.ntp_dir): #0.pkl, 1.pkl...
                # 숫자 부분 추출
                num = int(filename.split('.')[0])
                file_path = os.path.join(self.ntp_dir, filename)

                # pickle 파일 로드
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)

                # dict에 저장
                self.data[num] = data

            if not args.in_pretrain:
                self.dt_label = {}
                for filename in os.listdir(self.dt_label_dir):  # 0.pkl, 1.pkl...
                    # 숫자 부분 추출
                    num = int(filename.split('.')[0])
                    file_path = os.path.join(self.dt_label_dir, filename)

                    # pickle 파일 로드
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)

                    # dict에 저장
                    self.dt_label[num] = data

        else:
            print(f'No file {data_dir+done_name} ... creating')
            # 디렉토리 경로만 분리해서 생성
            os.makedirs(self.ntp_dir, exist_ok=True)
            if not args.in_pretrain:
                os.makedirs(self.dt_label_dir, exist_ok=True)


            if args.in_pretrain:
                csv_to_tensor(f'{args.qa_table_dir}/{load_seq_gen}/{"train" if is_train else "test"}/',
                              args.tte_threshold, tokenizer, processor, max_length = max_length, overlap_size = overlap, 
                              basic_dir = self.ntp_dir, tte_dir = self.tte_dir,
                              n_workers = args.sample_n_workers, addQ = load_seq_gen=='addQ',
                              ethos = self.pe_baseline == 'ETHOS', raw = args.bin.startswith('raw'))
            else:
                if getattr(args, 'dataset', None) == 'eICU':
                    csv_to_tensor_dt_eicu(f'{args.eval_task_dir}/{"train" if is_train else "test"}/',
                                 tokenizer, processor, max_length=max_length, overlap_size=overlap, 
                                 basic_dir=self.ntp_dir, dt_label_dir=self.dt_label_dir,
                                 n_workers=args.sample_n_workers, addQ=load_seq_gen == 'addQ',
                                 ethos = self.pe_baseline == 'ETHOS', raw = args.bin.startswith('raw'))
                else:
                    csv_to_tensor_dt(f'{args.eval_task_dir}/{load_seq_gen}/{"train" if is_train else "test"}/',
                                     tokenizer, processor, max_length=max_length, overlap_size=overlap, 
                                     basic_dir=self.ntp_dir, dt_label_dir=self.dt_label_dir,
                                     n_workers=args.sample_n_workers, addQ=load_seq_gen == 'addQ',
                                     ethos = self.pe_baseline == 'ETHOS', raw = args.bin.startswith('raw'))

            print(f'Created new dataset {self.ntp_dir}')
            with open(data_dir+done_name, 'w', encoding='utf-8') as f:
                f.write("done.\n")

            # Now load processed data
            self.data = {}
            for filename in os.listdir(self.ntp_dir):  # 0.pkl, 1.pkl...
                # 숫자 부분 추출
                num = int(filename.split('.')[0])
                file_path = os.path.join(self.ntp_dir, filename)

                # pickle 파일 로드
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)

                # dict에 저장
                self.data[num] = data

            if not args.in_pretrain:
                self.dt_label = {}
                for filename in os.listdir(self.dt_label_dir):  # 0.pkl, 1.pkl...
                    # 숫자 부분 추출
                    num = int(filename.split('.')[0])
                    file_path = os.path.join(self.dt_label_dir, filename)

                    # pickle 파일 로드
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)

                    # dict에 저장
                    self.dt_label[num] = data

        if args.share_tokens == 1 and bin_count is not None:
            init_idx = my_tokens('value_initial_idx')
            for key, value in self.data.items():
                mask = value[:, :, 1] >= my_tokens('2nd_feature_idx')
                value[mask, 2] = ((value[mask, 2] - init_idx) % bin_count) + init_idx
                self.data[key] = value



    def __len__(self):
        return sum(len(data) for data in self.data.values())

    def __getitem__(self, idx):
        k_num = idx//1000
        rest_num = idx%1000
        input_tns = self.data[k_num][rest_num] #length, 3

        if self.in_pretrain:
            if self.objective.endswith('TSP'):
                time_readable = datetime.fromtimestamp(input_tns[3,0])
                year_only_datetime = datetime(time_readable.year, 1, 1, 0, 0, 0)
                sec_int_from_year = int(year_only_datetime.timestamp())
                new_year_index = my_tokens('meta_extra10') #@ This should change if you change tokenizer offsets
                vector = np.array([int(sec_int_from_year), 0, new_year_index], dtype=int)

                input_tns = np.insert(input_tns, 3, vector, axis=0)

            if self.pe_baseline == 'ETHOS':
                age_year = (input_tns[3, 0] - input_tns[0, 0]) / 31557600
                decile_threshold = np.array([20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95])
                age_bin_index = np.digitize(age_year, decile_threshold) + my_tokens('meta_extra13_for_ETHOS')  # @ This should change if you change tokenizer offsets
                vector = np.array([input_tns[3, 0].item(), 0, age_bin_index], dtype=int)

                # 4번째(index=3) 위치에 vector 삽입
                input_tns = np.insert(input_tns, 3, vector, axis=0)

            else:
                '''
                Need to add age since timestamp is ignored: put age bin at position 3 (4th position)
                Use extra index 138-147
                '''
                age_year = (input_tns[3,0]-input_tns[0,0]) / 31557600
                decile_threshold = np.array([38.14, 47.98, 54.21, 59.38, 64.13, 68.83, 73.63, 78.25, 82.88])
                age_bin_index = np.digitize(age_year, decile_threshold)+my_tokens('meta_extra0') #@ This should change if you change tokenizer offsets
                vector = np.array([input_tns[3,0].item(), 0, age_bin_index], dtype=int)

                # 4번째(index=3) 위치에 vector 삽입
                input_tns = np.insert(input_tns, 3, vector, axis=0)

            # Next-token label: shift left by one; ignore (-100) the downstream-task
            # token and padding positions. G2DYDTSP = OURS; NTP = ETHOS baseline / eval.
            if self.objective in ['G2DYDTSP', 'NTP']:
                shifted_tensor = np.roll(input_tns, shift=-1, axis=0)
                condition = (shifted_tensor[:, 1] == self.downstream_token) | (shifted_tensor[:, 0] == 0) # Time ==0: padding - masking
                label = np.where(condition, -100, shifted_tensor[:, 2])
                label[-1] = -100
            else:
                raise NotImplementedError


        else:
            label = self.dt_label[k_num][rest_num]  # length, 3
            if self.objective.endswith('TSP'):
                time_readable = datetime.fromtimestamp(input_tns[3,0])
                year_only_datetime = datetime(time_readable.year, 1, 1, 0, 0, 0)
                sec_int_from_year = int(year_only_datetime.timestamp())
                new_year_index = my_tokens('meta_extra10') #@ This should change if you change tokenizer offsets
                vector = np.array([int(sec_int_from_year), 0, new_year_index], dtype=int)
                input_tns = np.insert(input_tns, 3, vector, axis=0)

                label = np.insert(label, 3, np.array(
                    [-100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100]), axis=0)

            if self.pe_baseline == 'ETHOS':
                age_year = (input_tns[3, 0] - input_tns[0, 0]) / 31557600
                decile_threshold = np.array([20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95])
                age_bin_index = np.digitize(age_year, decile_threshold) + my_tokens(
                    'meta_extra13_for_ETHOS')  # @ This should change if you change tokenizer offsets
                vector = np.array([input_tns[3, 0].item(), 2, age_bin_index], dtype=int)
                # 4번째(index=3) 위치에 vector 삽입
                input_tns = np.insert(input_tns, 3, vector, axis=0)

                label = np.insert(label, 3, np.array(
                    [-100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100]), axis=0)

            else:
                '''
                Need to add age since timestamp is ignored: put age bin at position 3 (4th position)
                Use extra index 138-147
                '''
                age_year = (input_tns[3, 0] - input_tns[0, 0]) / 31557600
                decile_threshold = np.array([38.14, 47.98, 54.21, 59.38, 64.13, 68.83, 73.63, 78.25, 82.88])
                age_bin_index = np.digitize(age_year, decile_threshold) + my_tokens(
                    'meta_extra0')  # @ This should change if you change tokenizer offsets
                vector = np.array([input_tns[3, 0].item(), 2, age_bin_index], dtype=int)
                # 4번째(index=3) 위치에 vector 삽입
                input_tns = np.insert(input_tns, 3, vector, axis=0)

                label = np.insert(label, 3, np.array(
                    [-100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100,
                     -100, -100, -100, -100, -100, -100, -100, -100, -100, -100]), axis=0)


        return add_position_group(np.expand_dims(input_tns, axis=0)).squeeze(axis=0), label


def get_datasets(args, tokenizer, processor):
    val_dataset = QA_dataset(args, tokenizer, processor, is_train=False)
    train_dataset = QA_dataset(args, tokenizer, processor, is_train = True)

    return train_dataset, val_dataset


if __name__ == "__main__":
    from pfm_mimic4.tokenizer.multitype_tokenizer import MultiTypeTokenizer
    from pfm_mimic4.tokenizer.tokenizing_setting import token_bin_range
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
    parser.add_argument("--bin", type=str, default='bin10_exp0_th10',
                        help='value binning; thresholds live in mimic4preprocessing/unit_value_cleaning/data/ (generated by mimic4preprocessing/unit_value_cleaning/binning/make_bin.py). bin{N}_exp{E}_th{T} = N percentile bins, density-weight exponent E (exp0 = no weighting), weight-clip threshold T. Used: bin10_exp1_th10 [OURS], bin10_exp0_th10 [ETHOS generation baseline]. Also generated: bin10_exp{0.5,1.5,2}_th10.')
    parser.add_argument("--share_tokens", type=int, default=0, help='0 - not share token; use each bin'
                                                                    '1 - share token')
    parser.add_argument("--seq_gen", type=str, default='NOadd',
                        help='addQ - add info token with timestamp and '
                             'addTS - share token'
                             'NOadd - no adding info token')
    parser.add_argument("--objective", type=str, default='G2DYDTSP',
                        help='G2DYDTSP - OURS. NTP - ETHOS baseline / downstream eval.')
    parser.add_argument("--in_pretrain", type=int, default=1)
    parser.add_argument("--eval_max_length", type=int, default=2048)
    parser.add_argument("--eval_overlap", type=int, default=512)

    parser.add_argument("--eval_task_dir", type=str, default="/path/to/PFM_data/PFM_downstream/")
    parser.add_argument("--eval_data_dir", type=str, default="/path/to/PFM_data/PFM_downstream/tensor_dt_saved/")

    parser.add_argument("--pe_baseline", type=str, default=None, help='None - OURS (default). ETHOS - generation-comparison baseline.')

    parser.add_argument("--dataset", type=str, default='M4', help='M4, eICU')


    args = parser.parse_args()
    processor = key_value_unit_processer(args.data)

    config = token_bin_range(args, processor.inclusion_dict_processed)

    tokenizer = MultiTypeTokenizer(config, args)
    train_dataset, val_dataset = get_datasets(args, tokenizer, processor)
    print("Train dataset size:", len(train_dataset))
    print("Val dataset size:", len(val_dataset))
    print("Example batch:", train_dataset[0])

