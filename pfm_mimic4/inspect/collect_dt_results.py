import os
import json
import pandas as pd
import glob


def get_last_best_val_loss(log_path: str):
    """
    log 파일에서 '50/50' 이 정확히 1개 존재하는지 확인한 후,
    해당 line까지(포함)에서 마지막 'New best validation loss:' 값을 float으로 반환.
    없으면 None 반환.
    """
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # '50/50' 라인 찾기
    fifty_lines = [i for i, line in enumerate(lines) if "50/50" in line]

    if len(fifty_lines) != 1:
        fifty_lines = [i for i, line in enumerate(lines) if "40/50" in line]
    if len(fifty_lines) != 1:
        raise ValueError(f"'50/50' must appear exactly once, but found {len(fifty_lines)} times.")

    cutoff = fifty_lines[0]+2  # N+2번째 줄 index

    last_val_loss = None
    for line in lines[:cutoff + 1]:  # 0 ~ N까지
        if "New best validation loss:" in line:
            try:
                val = float(line.strip().split("New best validation loss:")[-1])
                last_val_loss = val
            except ValueError:
                continue

    return last_val_loss

def flatten_mixed_dict(d, sep="_"):
    flat = {}
    for k, v in d.items():
        if isinstance(v, dict):  # nested dict인 경우 flatten
            for inner_k, inner_v in v.items():
                flat[f"{k}{sep}{inner_k}"] = inner_v
        else:  # 그냥 값인 경우 그대로 둠
            flat[k] = v
    return flat

def get_best_epoch_result(path_folder):
    """
    :param path_folder: ~/~/downstream_task_6_5e-05/ #
    :return: dict of best epoch
    """
    # epochN_result.json 파일들 찾기
    json_files = glob.glob(os.path.join(path_folder, "epoch*_result.json"))
    if not json_files:
        return None  # 파일 없으면 None 반환

    best_result = None
    best_valid_loss = float("inf")

    for file_path in json_files:
        with open(file_path, "r") as f:
            data = json.load(f)

        # validation loss 비교
        valid_loss = data.get("valid_loss", float("inf"))
        if valid_loss < best_valid_loss:
            best_valid_loss = valid_loss
            best_result = data

    return best_result

def list_dtlr_str(parent_folder, range = True):
    names= [
        name for name in os.listdir(parent_folder)
        if os.path.isdir(os.path.join(parent_folder, name)) and name.startswith("downstream_task")
    ]
    lrs = set([tt.split("_")[-1] for tt in names])
    out = []
    for lr in lrs:
        count = 0
        for data in ['criteria1']:
            if not os.path.isfile(os.path.join(parent_folder, f"downstream_task_{data}{'_range0' if range else ''}_{lr}", "epoch4_result.json")):
                print(f"Partial exsistance of DT with Data {data} LR {lr} in {parent_folder}")
            else:
                count+=1
        if count ==1:
            out.append(lr)



    return out



def process_folders(p: str, output_csv_name: str = "dt_result_table.csv"):
    """
    주어진 경로 'p' 내의 폴더들을 처리하여 'args.json' 파일에서 데이터를 추출합니다.

    인자:
        p (str): 여러 폴더를 포함하는 입력 경로.
        output_csv_name (str): 출력 CSV 파일의 이름.
    """
    all_dfs = []

    # 원하는 열 순서 정의
    desired_column_order = ["test_loss", "valid_loss", "train_loss", "pre_val_loss",
                            "dt_feature", "bin", "FT", "lr", "eval_finetune_lr", "share_tokens", "seq_gen", "objective",
                            "pe_baseline", "use_rope",
                            "multiple_rope_factor", "model_timestamp_rope_dim", "use_temperature_adj"
                            ]

    for folder_name in os.listdir(p):
        folder_path = os.path.join(p, folder_name)

        if p.startswith('duplicate'):
            continue

        # 디렉토리인지 확인
        if os.path.isdir(folder_path):
            checkpoint_path = os.path.join(folder_path, "check_points")
            epoch50_model_path = os.path.join(checkpoint_path, "checkpoint_epoch_40.pt")
            args_json_path = os.path.join(folder_path, "args.json")

            # best_model.pt가 존재하고 args.json이 존재하는지 확인
            if os.path.exists(epoch50_model_path) and os.path.exists(args_json_path):
                ### Downstream tasks

                ##################### - log : validation loss
                pre_train_validation = get_last_best_val_loss(folder_path + '/results/training_log.log')
                ##################### - END

                downstream_lrs = list_dtlr_str(folder_path)
                for dt_lr in downstream_lrs:
                    for dt_feature in ['criteria1']:
                        for ft_method in ['probe']: #'full'
                            if ft_method == 'full':
                                dt_result_dict = get_best_epoch_result(folder_path+f"/downstream_task_{dt_feature}_{dt_lr}/")
                            else:
                                dt_result_dict = get_best_epoch_result(folder_path + f"/downstream_task_{dt_feature}_range0_{dt_lr}/")
                            if dt_result_dict is None:
                                continue

                            dt_result_dict['FT'] = ft_method
                            dt_result_dict["5"].pop("confusion_matrix", None)
                            dt_result_dict["6"].pop("confusion_matrix", None)

                            dt_result_dict["IHM"] = dt_result_dict.pop("0")
                            dt_result_dict["DEC-death"] = dt_result_dict.pop("1")
                            dt_result_dict["DEC-arrest"] = dt_result_dict.pop("2")

                            dt_result_dict["DEC-icu"] = dt_result_dict.pop("3")
                            dt_result_dict["Prog"] = dt_result_dict.pop("4")
                            dt_result_dict["LOS_adm"] = dt_result_dict.pop("5")
                            dt_result_dict["LOS_icu"] = dt_result_dict.pop("6")

                            dt_result_dict["Phe"] = dt_result_dict.pop("7")
                            dt_result_dict["Vaso"] = dt_result_dict.pop("8")
                            dt_result_dict["HUO"] = dt_result_dict.pop("9")


                            non_nested = flatten_mixed_dict(dt_result_dict)

                            non_nested["pre_val_loss"] = pre_train_validation


                            try:
                                with open(args_json_path, 'r') as f:
                                    data = json.load(f)
                                data['eval_finetune_lr'] = float(dt_lr)

                                data['dt_feature'] = dt_feature
                                data['exp'] = dt_feature

                                data = non_nested|data

                                # 딕셔너리를 단일 행 DataFrame으로 변환
                                df = pd.DataFrame([data])
                                all_dfs.append(df)
                            except Exception as e:
                                print(f"Error reading or processing {args_json_path}: {e}")

    if not all_dfs:
        print("해당하는 best_model.pt를 가진 유효한 args.json 파일이 없습니다.")
        return

    # 모든 DataFrame 연결
    # 누락된 값은 "<N/A>"로 채웁니다.
    final_df = pd.concat(all_dfs, ignore_index=True).fillna("<N/A>")

    # DataFrame의 현재 열 가져오기
    current_columns = final_df.columns.tolist()

    # 재정렬된 열을 위한 새 목록 생성
    reordered_columns = []

    # 원하는 열이 현재 열에 존재하면 앞으로 추가
    for col in desired_column_order:
        if col in current_columns:
            reordered_columns.append(col)
            current_columns.remove(col)  # 중복 방지를 위해 제거

    # 나머지 열 추가
    reordered_columns.extend(current_columns)

    # 새 열 순서로 DataFrame 재인덱싱
    final_df = final_df[reordered_columns]

    # DataFrame을 CSV 파일로 저장
    final_df.to_csv(output_csv_name, index=False)
    print(f"처리된 데이터가 {output_csv_name}에 저장되었습니다.")

process_folders("/path/to/PFM_data/result_pretrained/max_len2048_overlap512_h512_h8_l6_ff2048", "dt_mimic4_result_table_lrs.csv")