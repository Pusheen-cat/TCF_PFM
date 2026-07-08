#!/usr/bin/env python3
"""
Pretraining launcher for the proposed method (TCF) on MIMIC-IV.

Shared-token variant: share_tokens=1 with seq_gen="addQ", objective="G2DYDTSP",
bin="bin10_exp1_th10". Sweeps the learning rate over [5e-4, 1e-4, 5e-5, 1e-5].
Launches pfm_mimic4/main.py under torchrun (DDP) once per configuration, waiting
for free GPUs between runs.

Usage:
    python pfm_mimic4/scripts/OURS.py --gpus 0,1,2,3 --num-gpus 4
"""

import os
import sys
import subprocess
import time
import argparse
import json
from datetime import datetime
from itertools import product
import GPUtil
from pathlib import Path


class TrainingManager:
    def __init__(self,
                 available_gpus=[0, 1, 2, 3],
                 num_gpus_per_exp=4,
                 base_args=None):
        self.available_gpus = available_gpus
        self.num_gpus_per_exp = num_gpus_per_exp
        self.base_args = base_args or {}
        self.experiment_results = []

        self.start_idx = 0

    def check_gpu_availability(self, gpu_ids):
        """Check if GPUs are available (low utilization)"""
        try:
            gpus = GPUtil.getGPUs()
            for gpu_id in gpu_ids:
                if gpu_id < len(gpus):
                    gpu = gpus[gpu_id]
                    if gpu.load > 0.1:  # 10% threshold
                        return False # 10% 이상 사용중인게 있으면 False를 보냄
            return True
        except:
            # Fallback to nvidia-smi if GPUtil fails
            for gpu_id in gpu_ids:
                cmd = f"nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits -i {gpu_id}"
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    usage = int(result.stdout.strip())
                    if usage > 10:
                        return False
                except:
                    continue
            return True

    def wait_for_gpus(self, needed_gpus):
        """Wait for available GPUs"""
        print(f"Waiting for {needed_gpus} available GPUs...")

        while True:
            available_combinations = []

            # Try all combinations of available GPUs
            from itertools import combinations
            for gpu_combo in combinations(self.available_gpus, needed_gpus):
                if self.check_gpu_availability(gpu_combo):
                    available_combinations.append(gpu_combo)

            if available_combinations:
                return available_combinations[0]  # Return first available combination

            print("Not enough GPUs available. Waiting 60 seconds...")
            time.sleep(60)

    def build_command(self, experiment_args):
        """Build the training command"""
        # Merge base args with experiment args
        all_args = {**self.base_args, **experiment_args}

        # Convert to command line arguments
        arg_str = ""
        for key, value in all_args.items():
            if isinstance(value, bool):
                if value:
                    arg_str += f"--{key} "
            else:
                arg_str += f"--{key} {value} "

        return arg_str.strip()

    def run_experiment(self, exp_name, gpu_list, experiment_args):
        """Run a single experiment"""
        print("=" * 60)
        print(f"Starting experiment: {exp_name}")
        print(f"Using GPUs: {gpu_list}")
        print(f"Arguments: {experiment_args}")
        print("=" * 60)

        # Build command
        arg_str = self.build_command(experiment_args)
        gpu_str = ",".join(map(str, gpu_list))

        cmd = f"""
                PYTHONPATH={Path(__file__).resolve().parents[2]} \
                CUDA_VISIBLE_DEVICES={gpu_str} \
                NCCL_P2P_DISABLE=1 NCCL_IB_DISABLE=1 \
                torchrun \
                    --nproc_per_node={self.num_gpus_per_exp} \
                    --master_port=29700 \
                    pfm_mimic4/main.py {arg_str}
                """

        # Run command
        start_time = time.time()
        try:
            process = subprocess.Popen(cmd, shell=True)
            process.wait()

            end_time = time.time()
            duration = end_time - start_time

            if process.returncode == 0:
                print(f"✅ Experiment {exp_name} completed successfully")
                print(f"Duration: {duration:.2f} seconds")
                status = "success"
            else:
                print(f"❌ Experiment {exp_name} failed with exit code {process.returncode}")
                status = "failed"

        except Exception as e:
            print(f"❌ Experiment {exp_name} failed with exception: {e}")
            status = "error"
            duration = time.time() - start_time

        # Record result
        result = {
            "experiment_name": exp_name,
            "status": status,
            "duration": duration,
            "gpu_list": gpu_list,
            "args": experiment_args
        }
        self.experiment_results.append(result)

        # Brief pause for GPU memory cleanup
        time.sleep(10)

        return status == "success"

    def run_parameter_sweep(self, param_grid_list):
        """Run parameter sweep experiments"""
        print("Starting parameter sweep...")

        experiment_count = 0
        successful_count = 0

        for param_grid in param_grid_list:
            # Generate all combinations
            param_names = list(param_grid.keys())
            param_values = list(param_grid.values())

            for combination in product(*param_values):
                experiment_count += 1

                # Create experiment args
                experiment_args = dict(zip(param_names, combination))

                # Create experiment name
                exp_name = "_".join([f"{k}_{v}" for k, v in experiment_args.items()])
                exp_name = f"sweep_{experiment_count}_{exp_name}"

                if self.start_idx >= experiment_count:
                    print(f'pass idx {experiment_count-1} | {exp_name}')
                    continue

                # Wait for available GPUs
                gpu_list = self.wait_for_gpus(self.num_gpus_per_exp)

                # Run experiment
                if self.run_experiment(exp_name, gpu_list, experiment_args):
                    successful_count += 1

        print("=" * 60)
        print("Parameter sweep completed!")
        print(f"Total experiments: {experiment_count}")
        print(f"Successful experiments: {successful_count}")
        print(f"Failed experiments: {experiment_count - successful_count}")
        print("=" * 60)

        return self.experiment_results

    def save_results(self, filename="experiment_results.json"):
        """Save experiment results to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.experiment_results, f, indent=2)

        print(f"Results saved to: {filename}")
        return filename


def main():
    parser = argparse.ArgumentParser(description="Training Script Manager")
    parser.add_argument("--gpus", type=str, default="4,5",
                        help="Comma-separated GPU IDs")
    parser.add_argument("--num-gpus", type=int, default=2,
                        help="Number of GPUs per experiment")
    parser.add_argument("--config", type=str, default=None,
                        help="JSON config file with parameter grid")

    args = parser.parse_args()

    # Parse GPU list
    gpu_list = [int(x.strip()) for x in args.gpus.split(",")]

    # ------------------------------------------------------------------ #
    # EDIT: directory holding the pre-tokenized pretraining tensors built
    # by pfm_mimic4/dataset/csvs_to_tensor.py (see README, "Pretraining").
    DATA_DIR = "/path/to/PFM_pretraining/tensor_saved/"
    # EDIT: directory where checkpoints and results are written.
    CHECKPOINT_DIR = "/path/to/result_pretrained/"
    # ------------------------------------------------------------------ #

    # Base arguments: fixed hyper-parameters of the method (shared by all runs).
    base_args = {
        "objective": 'G2DYDTSP',
        "batch_size": 38,

        "sample_max_length": 2048,
        "sample_overlap": 512,
        "sample_n_workers": 1,

        # Fixed regularization (paper setting).
        "model_dropout": 0.1,
        "mask_feature_p": 0.1,
        "mask_token_p": 0.1,

        "data": 'criteria1',

        "multiple_rope_factor": 1,
        "model_timestamp_rope_dim": 40,
        "use_temperature_adj": 1,

        "pred_max_dist_hr": 24,

        "data_dir": DATA_DIR,
        "checkpoint_dir": CHECKPOINT_DIR,
        "result_dir": CHECKPOINT_DIR,
    }

    # Sweep: the shared-token variant (share_tokens=1 -> addQ) over the paper's learning rates.
    param_grid = [
        {
            "objective": ["G2DYDTSP"],
            "bin": ["bin10_exp1_th10"],
            "share_tokens": [1],
            "seq_gen": ["addQ"],
            "lr": [5e-4, 1e-4, 5e-5, 1e-5],
        },
    ]
    start_idx = 0  # resume the sweep from this experiment index

    # Load config if provided
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
            base_args.update(config.get("base_args", {}))
            param_grid.update(config.get("param_grid", []))

    # Create training manager
    manager = TrainingManager(
        available_gpus=gpu_list,
        num_gpus_per_exp=args.num_gpus,
        base_args=base_args
    )
    manager.start_idx = start_idx

    # Run parameter sweep
    results = manager.run_parameter_sweep(param_grid)

    # Save results
    manager.save_results()

    print("\n" + "=" * 60)
    print("EXPERIMENT SUMMARY")
    print("=" * 60)
    for result in results:
        status_symbol = "✅" if result["status"] == "success" else "❌"
        print(f"{status_symbol} {result['experiment_name']}: {result['status']} ({result['duration']:.1f}s)")


if __name__ == "__main__":
    main()