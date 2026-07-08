import json
import os
import argparse
import numpy as np
import torch
import random

def save_args_to_json(args, file_path="config.json"):
    """
    Parses command-line arguments and saves them to a JSON file,
    ensuring all keys and values are converted to strings.

    Args:
        args: An argparse.Namespace object containing the parsed arguments.
        file_path (str): The path to the JSON file where the arguments will be saved.
                         Defaults to "config.json" in the current directory.
    """
    try:
        # Convert the argparse.Namespace object to a dictionary
        # This requires 'args' to be an object with a __dict__ attribute, like argparse.Namespace
        if isinstance(args, dict):
            args_dict = args
        else:
            args_dict = vars(args)

        # Create a new dictionary to store string-converted keys and values
        # This ensures all keys and values are strings, preventing JSON serialization errors
        string_converted_args = {}
        for k, v in args_dict.items():
            # Handle None explicitly to convert it to the string "None"
            # Otherwise, str(None) would just be "None" which is fine, but good to be explicit
            string_converted_args[str(k)] = str(v) if v is not None else "None"

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(string_converted_args, f, indent=4, ensure_ascii=False)
        print(f"인자들이 성공적으로 '{file_path}'에 JSON 형식으로 저장되었습니다.")
    except Exception as e:
        print(f"오류 발생: 인자를 JSON 파일에 저장하는 데 실패했습니다. {e}")


def load_args_from_json(file_path="config.json"):
    """
    Loads arguments from a JSON file and returns them as an argparse.Namespace object.
    Tries to intelligently cast values back to their original types (int, float, bool, or None),
    assuming they were stored as strings.

    Args:
        file_path (str): The path to the JSON file containing argument key-value pairs.

    Returns:
        argparse.Namespace: The loaded arguments.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            string_args = json.load(f)

        parsed_args = {}
        for k, v in string_args.items():
            # Convert string values back to original types if possible
            if v == "None":
                parsed_args[k] = None
            elif v == "True":
                parsed_args[k] = True
            elif v == "False":
                parsed_args[k] = False
            else:
                # Try to cast to int or float if possible
                try:
                    parsed_args[k] = int(v)
                except ValueError:
                    try:
                        parsed_args[k] = float(v)
                    except ValueError:
                        parsed_args[k] = v  # Keep as string

        return argparse.Namespace(**parsed_args)

    except Exception as e:
        print(f"오류 발생: JSON 파일에서 인자를 불러오는 데 실패했습니다. {e}")
        return argparse.Namespace()


def update_args_from_json(args, file_path="config.json"):
    """
    기존 argparse.Namespace 객체를 JSON 파일의 값으로 업데이트합니다.
    단, 'eval'로 시작하는 키는 덮어씌우지 않습니다.

    Args:
        args (argparse.Namespace): 기존 인자들
        file_path (str): JSON 파일 경로

    Returns:
        argparse.Namespace: 업데이트된 인자
    """
    loaded_args = load_args_from_json(file_path)

    for k, v in vars(loaded_args).items():
        if not k.startswith("eval"):
            setattr(args, k, v)  # 덮어쓰기

    return args

def set_seed(seed: int, rank: int):
    """각 프로세스(rank)에 맞춰 seed를 고정"""
    seed = seed + rank  # 각 rank마다 seed를 다르게
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    # 재현성 보장 설정
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def get_bin(bin_str):
    assert bin_str.startswith("bin10")
    if bin_str[5] == '0':
        return 100
    else:
        return 10
