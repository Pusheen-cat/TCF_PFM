# transformer_trainer_ddp.py
import os
import torch
import torch.nn as nn
import torch.optim as optim
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler, Subset
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.amp import GradScaler, autocast  # Mixed precision imports
from tqdm import tqdm
import torch.nn.functional as F
import logging
from modules.dt_loss import dt_ce_loss
from modules.our_loss import time_prediction_loss
import json
import torch.nn.utils as utils

def initialize_ddp():
    """DDP를 프로그램 시작시 한 번만 초기화"""
    if not dist.is_initialized():
        try:
            # 환경 변수 확인
            rank = int(os.environ['RANK'])
            world_size = int(os.environ['WORLD_SIZE'])
            local_rank = int(os.environ['LOCAL_RANK'])

            print(f"[Rank {rank}] Initializing DDP - world_size: {world_size}, local_rank: {local_rank}")

            # CUDA 디바이스 설정
            torch.cuda.set_device(local_rank)
            device = torch.device(f"cuda:{local_rank}")

            # NCCL 백엔드로 초기화
            dist.init_process_group(
                backend='nccl',
                init_method='env://',  # 환경 변수 사용
                world_size=world_size,
                rank=rank,
                device_id=device  # ✅ 명시적으로 device 지정
            )

            print(f"[Rank {rank}] DDP initialization successful")

            # 모든 프로세스 동기화
            dist.barrier()

            return True

        except Exception as e:
            print(f"[Rank {os.environ.get('RANK', 'unknown')}] DDP initialization failed: {e}")
            return False
    else:
        print(f"[Rank {os.environ.get('RANK', 'unknown')}] DDP already initialized")
        return True

class TransformerTrainerDDP:
    def __init__(self, model, train_dataset, val_dataset, tokenizer, args):
        self.args = args
        self.world_size = int(os.environ["WORLD_SIZE"])
        self.rank = int(os.environ["RANK"])
        args.local_rank = int(os.environ["LOCAL_RANK"])
        self.device = torch.device(f"cuda:{args.local_rank}")
        self.batch_size = args.batch_size if args.in_pretrain else args.eval_finetune_batch_size
        self.checkpoint_dir = args.checkpoint_dir if args.in_pretrain else f'{args.eval_saved_path}/{args.eval_load_pretrained}/downstream_task_{f"{args.eval_dataset}_" if (args.eval_dataset != 'M4')&(not args.eval_zero_shot) else ""}{args.data}{f"_range{self.args.eval_ft_range}" if self.args.eval_ft_range <3 else ""}_{args.eval_finetune_lr}/check_points/'

        # Logger 설정 (rank 0에서만)
        self.logger = None
        if self.rank == 0:
            self.setup_logger()

        # DDP 초기화
        #torch.distributed.init_process_group(backend="nccl")


        # 모델, DDP 래핑
        self.model = model.to(self.device)
        if args.in_pretrain or args.eval_ft_range ==3:
            self.model = DDP(self.model, device_ids=[args.local_rank])
        else:
            self.model = DDP(self.model, device_ids=[args.local_rank], find_unused_parameters=True)

        # Mixed precision scaler 초기화
        self.scaler = GradScaler()

        # 데이터로더 (DDP용 Sampler)
        if args.in_pretrain:
            self.train_sampler = DistributedSampler(train_dataset, num_replicas=self.world_size, rank=self.rank)
            self.val_sampler = DistributedSampler(val_dataset, num_replicas=self.world_size, rank=self.rank, shuffle=False)
            self.train_loader = DataLoader(
                train_dataset,
                batch_size=self.batch_size,
                sampler=self.train_sampler,
                num_workers=args.num_workers,
                pin_memory=True
            )
            self.val_loader = DataLoader(
                val_dataset,
                batch_size=self.batch_size,
                sampler=self.val_sampler,
                num_workers=args.num_workers,
                pin_memory=True
            )
        else:
            train_size = int(len(train_dataset) * 0.85)
            # 인덱스를 정의합니다.
            train_indices = range(train_size)  # 0부터 799까지 (80%)
            valid_indices = range(train_size, len(train_dataset))  # 800부터 999까지 (나머지 20%)
            # Subset을 사용하여 데이터셋을 분리합니다.
            train_subset = Subset(train_dataset, train_indices)
            valid_subset = Subset(train_dataset, valid_indices)

            self.train_sampler = DistributedSampler(train_subset, num_replicas=self.world_size, rank=self.rank)
            self.val_sampler = DistributedSampler(valid_subset, num_replicas=self.world_size, rank=self.rank,
                                                  shuffle=False)
            self.test_sampler = DistributedSampler(val_dataset, num_replicas=self.world_size, rank=self.rank,
                                                  shuffle=False)
            self.train_loader = DataLoader(
                train_subset,
                batch_size=self.batch_size,
                sampler=self.train_sampler,
                num_workers=args.num_workers,
                pin_memory=True
            )
            self.val_loader = DataLoader(
                valid_subset,
                batch_size=self.batch_size,
                sampler=self.val_sampler,
                num_workers=args.num_workers,
                pin_memory=True
            )
            self.test_loader = DataLoader(
                val_dataset,
                batch_size=self.batch_size,
                sampler=self.test_sampler,
                num_workers=args.num_workers,
                pin_memory=True
            )

        if args.in_pretrain:
            self.optimizer = optim.Adam(self.model.parameters(), lr=args.lr)
            # Learning Rate Scheduler 추가 (최종 LR이 초기 LR의 0.01배가 되도록)
            self.scheduler = CosineAnnealingLR(
                self.optimizer,
                T_max=args.num_epochs,
                eta_min=args.lr * 0.01
            )

            # Warmup 설정
            self.warmup_steps = getattr(args, 'warmup_steps', 10)
            self.warmup_start_lr = args.lr * 0.01
            self.target_lr = args.lr
            self.current_step = 0

            # Best model tracking & Early stopping
            self.best_val_loss = float('inf')
            self.early_stop_counter = 0
            self.early_stop_patience = getattr(args, 'early_stop_patience', 10)

            # Loss function 설정
            #   G2DYDTSP (OURS): joint next-token + next-event-time loss.
            #   NTP (ETHOS baseline): plain next-token cross-entropy.
            if args.objective == 'G2DYDTSP':
                self.loss_function = time_prediction_loss(False)
            else:
                self.loss_function = self.compute_loss
        else:
            # params_to_update = []
            # for name, param in self.model.named_parameters():
            #     if "output_projection" in name:
            #         params_to_update.append(param)
            #
            # self.optimizer = optim.Adam(params_to_update, lr=args.eval_finetune_lr)

            if self.args.eval_ft_range == 0:
                params_to_update = [p for n, p in self.model.named_parameters() if "output_projection" in n]
                self.optimizer = optim.Adam(params_to_update, lr=args.eval_finetune_lr)

                for name, param in self.model.named_parameters():
                    if "output_projection" not in name:
                        param.requires_grad = False

            elif self.args.eval_ft_range == 3:
                self.optimizer = optim.Adam(self.model.parameters(), lr=args.eval_finetune_lr)

            self.scheduler = CosineAnnealingLR(
                self.optimizer,
                T_max=args.eval_finetune_epoch,
                eta_min=args.eval_finetune_lr * args.eval_ft_lr_decay
            )

            # Warmup 설정
            self.warmup_steps = getattr(args, 'eval_warmup_steps', 50)
            self.warmup_start_lr = args.eval_finetune_lr * args.eval_ft_lr_decay
            self.target_lr = args.eval_finetune_lr
            self.current_step = 0
            self.loss_function = dt_ce_loss(eval_dataset = self.args.eval_dataset).to(self.device)

            # Best model tracking & Early stopping
            self.best_val_loss = float('inf')
            self.early_stop_counter = 0
            self.early_stop_patience = getattr(args, 'early_stop_patience', 10)

            #global step for ConFIG
            # self.global_step = 0
            # self.operator = PseudoMomentumOperator(7)  # initialize operator, the only difference here is we need to specify the number of gradient vectors.


        if self.rank == 0:
            self.logger.info(f"Training setup completed")
            self.logger.info(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
            self.logger.info(f"Mixed precision training: ENABLED")
            self.logger.info(f"Initial learning rate: {args.lr}")
            self.logger.info(f"Final learning rate (eta_min): {args.lr * 0.01}")
            self.logger.info(f"Warmup steps: {self.warmup_steps}")
            self.logger.info(f"Warmup start LR: {self.warmup_start_lr}")
            self.logger.info(f"Batch size: {self.batch_size}")
            self.logger.info(f"Number of epochs: {args.num_epochs}")

    def setup_logger(self):
        """Logger 설정 - checkpoint 폴더와 같은 위치에 log 파일 저장"""
        os.makedirs(self.args.result_dir, exist_ok=True)
        log_file = os.path.join(self.args.result_dir, f"training_log.log")

        self.logger = logging.getLogger('TransformerTrainer')
        self.logger.setLevel(logging.INFO)

        # 기존 핸들러 제거 (중복 방지)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 파일 핸들러 추가
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 포매터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 핸들러 추가
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info(f"Logger initialized. Log file: {log_file}")

    def update_learning_rate(self):
        """Warmup learning rate 업데이트"""
        if self.current_step <= self.warmup_steps:
            lr = self.warmup_start_lr + (self.target_lr - self.warmup_start_lr) * (
                    self.current_step / self.warmup_steps)
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = lr
            return lr
        else:
            return self.optimizer.param_groups[0]['lr']

    def compute_loss(self, outputs, temperature, targets):
        temperature_expanded = temperature.unsqueeze(-1)
        scaled_logits = outputs / temperature_expanded
        scaled_logits = scaled_logits.view(-1, outputs.size(-1))
        targets = targets.view(-1)
        loss = F.cross_entropy(scaled_logits, targets, ignore_index=-100)
        return loss

    def train_one_epoch(self, epoch):
        self.model.train()
        self.train_sampler.set_epoch(epoch)

        total_loss = 0
        total_temp = 0
        num_batches = 0

        pbar = tqdm(self.train_loader, desc=f"[Rank {self.rank}] Epoch {epoch + 1} - Training", disable=self.rank != 0)

        for batch in pbar:
            inputs, targets = batch
            inputs = inputs.to(self.device)
            try:
                targets = targets.to(self.device)
            except:
                targets = [tt.to(self.device) for tt in targets]

            self.optimizer.zero_grad()

            # Mixed precision forward pass
            with autocast("cuda"):
                outputs, temperature = self.model(inputs, targets)
                if self.args.use_temperature_adj and epoch <= 6:
                    temperature = temperature * 0 + 1
                loss = self.loss_function(outputs, temperature, targets)

            # Mixed precision backward pass
            self.scaler.scale(loss).backward()
            utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.scaler.step(self.optimizer)
            self.scaler.update()

            # Learning rate 업데이트 (warmup 포함)
            current_lr = self.update_learning_rate()
            self.current_step += 1

            total_loss += loss.item()
            if self.args.use_temperature_adj:
                total_temp += torch.mean(temperature).item()
            else:
                total_temp +=1
            num_batches += 1

            # 실시간 평균 loss 업데이트
            current_avg_loss = total_loss / num_batches
            current_avg_temp = total_temp / num_batches
            if self.rank == 0:
                postfix_dict = {
                    'avg loss': f'{current_avg_loss:.2f}',
                    'avg temp': f'{current_avg_temp:.2f}',
                    'lr': f'{current_lr:.6f}',
                    'scale': f'{self.scaler.get_scale():.0f}'  # Mixed precision scale 표시
                }
                if self.model.module.use_time_label:
                    postfix_dict['time'] = f'{self.loss_function.time_loss:.2f}'
                    postfix_dict['tokn'] = f'{self.loss_function.token_loss:.2f}'
                # Warmup 단계인 경우 표시
                if self.current_step <= self.warmup_steps:
                    postfix_dict['warmup'] = f'{self.current_step}/{self.warmup_steps}'
                pbar.set_postfix(postfix_dict)

        avg_loss = total_loss / len(self.train_loader)
        avg_temp = total_temp / len(self.train_loader)
        return avg_loss, avg_temp

    def evaluate(self):
        self.model.eval()
        total_loss = 0
        total_temp = 0
        num_batches = 0

        pbar = tqdm(self.val_loader, desc=f"[Rank {self.rank}] Evaluating", disable=self.rank != 0)

        with torch.no_grad():
            for batch in pbar:
                inputs, targets = batch
                inputs = inputs.to(self.device)
                try:
                    targets = targets.to(self.device)
                except:
                    targets = [tt.to(self.device) for tt in targets]

                # Mixed precision forward pass for evaluation
                with autocast("cuda"):
                    outputs, temperature = self.model(inputs, targets)
                    loss = self.loss_function(outputs, temperature, targets)

                total_loss += loss.item()
                if self.args.use_temperature_adj:
                    total_temp += torch.mean(temperature).item()
                else:
                    total_temp += 1
                num_batches += 1

                # 실시간 평균 loss 업데이트
                current_avg_loss = total_loss / num_batches
                current_avg_temp = total_temp / num_batches
                if self.rank == 0:
                    pbar.set_postfix({'loss': f'{current_avg_loss:.2f}', 'temp': f'{current_avg_temp:.2f}'})

        avg_loss = total_loss / len(self.val_loader)
        avg_temp = total_temp / len(self.val_loader)
        return avg_loss, avg_temp

    def save_checkpoint(self, epoch, is_best=False, is_dt = False):
        save_interval = 5 if is_dt else 10
        if self.rank == 0:
            os.makedirs(f'{self.checkpoint_dir}', exist_ok=True)
            # Mixed precision scaler 상태도 저장
            state = {
                "epoch": epoch + 1,
                "model_state": self.model.module.state_dict(),
                "optimizer_state": self.optimizer.state_dict(),
                "scheduler_state": self.scheduler.state_dict(),
                "scaler_state": self.scaler.state_dict(),  # Mixed precision scaler 상태 저장
                "current_step": self.current_step,
                "args": vars(self.args),
                "best_val_loss": self.best_val_loss
            }

            if (epoch + 1) % save_interval == 0:
                save_path = os.path.join(self.checkpoint_dir, f"checkpoint_epoch_{epoch + 1}.pt")
                torch.save(state, save_path)
                print(f"[Rank 0] Saved checkpoint: {save_path}")
                self.logger.info(f"Saved checkpoint: {save_path}")

            # Best 모델 저장
            if is_best:
                best_path = os.path.join(self.checkpoint_dir, "best_model.pt")
                torch.save(state, best_path)
                print(f"[Rank 0] Saved best model: {best_path}")
                self.logger.info(f"Saved best model: {best_path}")

    def load_checkpoint(self, checkpoint_path, only_model=False, strict=False):
        """체크포인트 로드 함수 (Mixed precision 상태 포함)"""
        if self.rank == 0:
            self.logger.info(f"Loading checkpoint from {checkpoint_path}")

        checkpoint = torch.load(checkpoint_path, map_location=self.device)

        # 현재 모델의 state_dict 키 목록
        current_keys = set(self.model.module.state_dict().keys())

        # 체크포인트에서 불러온 키 목록
        loaded_keys = {
            k: v for k, v in checkpoint['model_state'].items()
            if not k.startswith('output_projection')
        }

        # 체크포인트에서 로드하려는 키들과 현재 모델의 키들이 일치하는지 확인
        missing_keys = current_keys - set(loaded_keys.keys())
        unexpected_keys = set(loaded_keys.keys()) - current_keys

        # output_projection 관련 누락만 있는지 확인
        allowed_missing_prefix = 'output_projection'
        real_missing = [k for k in missing_keys if not k.startswith(allowed_missing_prefix)]

        if real_missing:
            raise RuntimeError(f"Unexpected missing keys (excluding '{allowed_missing_prefix}'): {real_missing}")

        # unexpected_keys 중 temperature_projection으로 시작하지 않는 것이 있는지 확인
        unexpected_allowed_prefix = 'temperature_projection'
        real_unexpected = [k for k in unexpected_keys if not k.startswith(unexpected_allowed_prefix)]

        if real_unexpected:
            if self.args.objective == 'G2DYDTSP':
                # OURS carries time_addressing_module weights absent from the NTP head.
                for tt in real_unexpected:
                    if tt.startswith('time_addressing_module'):
                        pass
                    else:
                        raise RuntimeError(f"Unexpected keys in checkpoint not in model: {real_unexpected}")
            else:
                raise RuntimeError(f"Unexpected keys in checkpoint not in model: {real_unexpected}")

        loaded_keys = {k: v for k, v in loaded_keys.items() if "causal_mask" not in k} #not load causal_mask

        # 문제가 없다면 로드
        self.model.module.load_state_dict(loaded_keys, strict=False)

        if strict:
            print("STRICT MODEL LOAD")
            self.model.module.load_state_dict(checkpoint['model_state'], strict=True)

        if only_model:
            start_epoch = checkpoint.get('epoch', 0)
            return start_epoch
        # 옵티마이저 상태 로드
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])

        # 스케줄러 상태 로드
        if 'scheduler_state' in checkpoint:
            self.scheduler.load_state_dict(checkpoint['scheduler_state'])

        # Mixed precision scaler 상태 로드
        if 'scaler_state' in checkpoint:
            self.scaler.load_state_dict(checkpoint['scaler_state'])

        # 기타 상태 로드
        self.current_step = checkpoint.get('current_step', 0)
        self.best_val_loss = checkpoint.get('best_val_loss', float('inf'))

        start_epoch = checkpoint.get('epoch', 0)

        if self.rank == 0:
            self.logger.info(f"Resumed from epoch {start_epoch}")
            self.logger.info(f"Current step: {self.current_step}")
            self.logger.info(f"Best validation loss: {self.best_val_loss}")

        return start_epoch

    def train(self, resume_checkpoint=None):
        if self.rank == 0:
            self.logger.info("Starting training with mixed precision...")

        # ✅ Resume: 체크포인트에서 epoch, optimizer, scheduler 등 복원
        start_epoch = 0
        if resume_checkpoint is not None:
            start_epoch = self.load_checkpoint(resume_checkpoint)
            if self.rank == 0:
                self.logger.info(f"Resuming training from epoch {start_epoch}")

        for epoch in range(start_epoch, self.args.num_epochs):
            train_loss, train_temp = self.train_one_epoch(epoch)
            val_loss, val_temp = self.evaluate()

            # Learning rate scheduler step (warmup 완료 후에만)
            if self.current_step > self.warmup_steps:
                self.scheduler.step()

            current_lr = self.optimizer.param_groups[0]['lr']

            # Best model 체크 및 early stopping (rank 0에서만)
            is_best = False
            should_early_stop = False

            if self.rank == 0:
                warmup_status = f" (Warmup: {min(self.current_step, self.warmup_steps)}/{self.warmup_steps})" if self.current_step <= self.warmup_steps else ""
                log_message = (
                    f"Epoch {epoch + 1}/{self.args.num_epochs} | "
                    f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | "
                    f"Train temp: {train_temp:.4f} | Val temp: {val_temp:.4f} | "
                    f"LR: {current_lr:.6f} | Scale: {self.scaler.get_scale():.0f}{warmup_status}"
                )
                print(f"[Rank 0] {log_message}")
                self.logger.info(log_message)

                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self.early_stop_counter = 0
                    is_best = True
                    best_message = f"New best validation loss: {val_loss:.4f}"
                    print(f"[Rank 0] {best_message}")
                    self.logger.info(best_message)
                else:
                    self.early_stop_counter += 1
                    early_stop_message = f"Early stop counter: {self.early_stop_counter}/{self.early_stop_patience}"
                    print(f"[Rank 0] {early_stop_message}")
                    self.logger.info(early_stop_message)

                # 체크포인트 저장 (best 여부 전달)
                self.save_checkpoint(epoch, is_best)

                # Early stopping 체크
                should_early_stop = self.early_stop_counter >= self.early_stop_patience
                if should_early_stop:
                    early_stop_final_message = f"Early stopping triggered after {epoch + 1} epochs"
                    print(f"[Rank 0] {early_stop_final_message}")
                    self.logger.info(early_stop_final_message)

            # 모든 rank에서 early stopping 결정을 동기화
            early_stop_tensor = torch.tensor(1 if should_early_stop else 0, dtype=torch.int, device=self.device)
            dist.broadcast(early_stop_tensor, src=0)

            # 모든 rank에서 early stopping 체크
            if early_stop_tensor.item() == 1:
                if self.rank != 0:
                    print(f"[Rank {self.rank}] Early stopping triggered")
                break

        if self.rank == 0:
            self.logger.info("Training completed!")

        #dist.destroy_process_group()

    def downstream_tasks(self):

        if self.rank == 0:
            self.logger.info("Loading model from checkpoint")

        if not self.args.eval_zero_shot: # default
            self.load_checkpoint(f'{self.args.eval_saved_path}/{self.args.eval_load_pretrained}/check_points/best_model.pt', only_model=True)  # load model
        else:
            epoch = self.load_checkpoint(f'{self.checkpoint_dir}/best_model.pt', only_model=True, strict=True)
            self.loss_function.in_train(False)
            test_loss, test_temp = self.evaluate_dt(epoch, 0, 0,  0, 0, dataset = self.args.eval_dataset, zero_shot = True)
            return True



        if self.rank == 0:
            self.logger.info("Starting DT training with mixed precision...")

        for epoch in range(self.args.eval_finetune_epoch):
            self.loss_function.in_train(True)
            train_loss, train_temp = self.train_one_epoch(epoch)
            self.loss_function.in_train(True)
            val_loss, val_temp = self.evaluate()
            self.loss_function.in_train(False)
            test_loss, test_temp = self.evaluate_dt(epoch, train_loss, train_temp, val_loss, val_temp, dataset = self.args.eval_dataset)

            # NaN 체크
            # if any(torch.isnan(torch.tensor(x)) for x in [train_loss, train_temp, test_loss, test_temp]):
            #     print(
            #         f"NaN detected in epoch {epoch}: train_loss={train_loss}, train_temp={train_temp}, test_loss={test_loss}, test_temp={test_temp}")
            #     raise ValueError("NaN detected in training metrics")

            # Learning rate scheduler step (warmup 완료 후에만)
            if self.current_step > self.warmup_steps:
                self.scheduler.step()

            current_lr = self.optimizer.param_groups[0]['lr']

            # Best model 체크 및 early stopping (rank 0에서만)
            is_best = False
            should_early_stop = False

            if self.rank == 0:
                warmup_status = f" (Warmup: {min(self.current_step, self.warmup_steps)}/{self.warmup_steps})" if self.current_step <= self.warmup_steps else ""
                log_message = (
                    f"Epoch {epoch + 1}/{self.args.num_epochs} | "
                    f"Train Loss: {train_loss:.4f} | Test Loss: {test_loss:.4f} | "
                    f"Train temp: {train_temp:.4f} | Test temp: {test_temp:.4f} | "
                    f"LR: {current_lr:.6f} | Scale: {self.scaler.get_scale():.0f}{warmup_status}"
                )
                print(f"[Rank 0] {log_message}")
                self.logger.info(log_message)

                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self.early_stop_counter = 0
                    is_best = True
                    best_message = f"New best validation loss: {val_loss:.4f}"
                    print(f"[Rank 0] {best_message}")
                    self.logger.info(best_message)
                else:
                    self.early_stop_counter += 1
                    early_stop_message = f"Early stop counter: {self.early_stop_counter}/{self.early_stop_patience}"
                    print(f"[Rank 0] {early_stop_message}")
                    self.logger.info(early_stop_message)

                # 체크포인트 저장 (best 여부 전달)
                self.save_checkpoint(epoch, is_best, is_dt=True)

            # 모든 rank에서 early stopping 결정을 동기화
            early_stop_tensor = torch.tensor(1 if should_early_stop else 0, dtype=torch.int, device=self.device)
            dist.broadcast(early_stop_tensor, src=0)

            # 모든 rank에서 early stopping 체크
            if early_stop_tensor.item() == 1:
                if self.rank != 0:
                    print(f"[Rank {self.rank}] Early stopping triggered")
                break

        if self.rank == 0:
            self.logger.info("Training completed!")

        # dist.destroy_process_group()

    def evaluate_dt(self, epoch, train_loss, train_temp, val_loss, val_temp, dataset = 'M4', zero_shot = False):
        self.model.eval()
        total_loss = 0
        total_temp = 0
        num_batches = 0
        self.loss_function.eval = True

        pbar = tqdm(self.test_loader, desc=f"[Rank {self.rank}] Evaluating", disable=self.rank != 0)

        with torch.no_grad():
            for batch in pbar:
                inputs, targets = batch
                inputs = inputs.to(self.device)
                try:
                    targets = targets.to(self.device)
                except:
                    targets = [tt.to(self.device) for tt in targets]

                # Mixed precision forward pass for evaluation
                with autocast("cuda"):
                    outputs, temperature = self.model(inputs, targets)
                    loss = self.loss_function(outputs, temperature, targets)

                total_loss += loss.item()
                if self.args.use_temperature_adj:
                    total_temp += torch.mean(temperature).item()
                else:
                    total_temp += 1
                num_batches += 1

                # 실시간 평균 loss 업데이트
                current_avg_loss = total_loss / num_batches
                current_avg_temp = total_temp / num_batches
                if self.rank == 0:
                    pbar.set_postfix({'loss': f'{current_avg_loss:.2f}', 'temp': f'{current_avg_temp:.2f}'})

            if self.rank == 0:
                os.makedirs(
                    f'{self.args.eval_saved_path}/{self.args.eval_load_pretrained}/downstream_task_{f"{self.args.eval_dataset}_" if (dataset != 'M4')&(not zero_shot) else ""}{self.args.data}{f"_range{self.args.eval_ft_range}" if self.args.eval_ft_range <3 else ""}_{self.args.eval_finetune_lr}{f"/zeroshot_epoch{epoch}_{dataset}/detail/" if zero_shot else f"/epoch{epoch}_detail/"}',
                    exist_ok=True)
            result = self.loss_function.calc_results(
                f'{self.args.eval_saved_path}/{self.args.eval_load_pretrained}/downstream_task_{f"{self.args.eval_dataset}_" if (dataset != 'M4')&(not zero_shot) else ""}{self.args.data}{f"_range{self.args.eval_ft_range}" if self.args.eval_ft_range <3 else ""}_{self.args.eval_finetune_lr}{f"/zeroshot_epoch{epoch}_{dataset}/detail/" if zero_shot else f"/epoch{epoch}_detail/"}',
            idxs= 2 if dataset == 'eICU' else 10)

            losses_tensor = torch.tensor([train_loss, val_loss, current_avg_loss], device=f'cuda:{self.rank}')
            dist.reduce(losses_tensor, dst=0, op=dist.ReduceOp.SUM)

            if self.rank == 0:
                result['train_loss'] = (losses_tensor[0] / self.world_size).item()
                result['valid_loss'] = (losses_tensor[1] / self.world_size).item()
                result['test_loss'] = (losses_tensor[2] / self.world_size).item()
                print("    Result:", result)
                # JSON 파일로 저장
                with open(
                        f'{self.args.eval_saved_path}/{self.args.eval_load_pretrained}/downstream_task_{f"{self.args.eval_dataset}_" if (dataset != 'M4')&(not zero_shot) else ""}{self.args.data}{f"_range{self.args.eval_ft_range}" if self.args.eval_ft_range <3 else ""}_{self.args.eval_finetune_lr}/{f"zeroshot_epoch{epoch}_{dataset}/" if zero_shot else ""}epoch{epoch}_result.json',
                        'w') as f:
                    json.dump(result, f, indent=4)  # indent는 보기 좋게 들여쓰기

        avg_loss = total_loss / len(self.test_loader)
        avg_temp = total_temp / len(self.test_loader)
        return avg_loss, avg_temp

# main_ddp.py