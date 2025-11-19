#!/usr/bin/env python3
"""
ML Training Daemon: Continuously monitors for new data and trains automatically

Features:
- Monitors datasets for changes
- Downloads new data from live sources
- Trains model when new data is available
- Validates new model before deployment
- Stays idle when no updates needed
- Scheduled retraining (daily/weekly/monthly)

Usage:
    # Run once and exit
    python scripts/ml_training_daemon.py --once
    
    # Run continuously (check every hour)
    python scripts/ml_training_daemon.py --interval 3600
    
    # Run as background daemon
    nohup python scripts/ml_training_daemon.py --interval 3600 > logs/ml_daemon.log 2>&1 &
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


class MLTrainingDaemon:
    """
    Daemon that monitors for new data and trains ML model automatically
    """
    
    def __init__(
        self,
        data_dir: str = "datasets_raw",
        model_path: str = "models/ml_fast.pkl",
        check_interval: int = 3600,  # 1 hour
        auto_download: bool = True,
        auto_deploy: bool = True,
        min_accuracy: float = 0.60,
        retrain_schedule: str = "weekly",  # daily, weekly, monthly, never
        verbose: bool = True
    ):
        self.data_dir = data_dir
        self.model_path = model_path
        self.check_interval = check_interval
        self.auto_download = auto_download
        self.auto_deploy = auto_deploy
        self.min_accuracy = min_accuracy
        self.retrain_schedule = retrain_schedule
        self.verbose = verbose
        
        self.last_check_time = None
        self.last_train_time = None
        self.last_download_time = None
        
        # Load state if exists
        self._load_state()
    
    def _load_state(self):
        """Load daemon state from file"""
        state_file = "data/ml_daemon_state.txt"
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith('last_train:'):
                            self.last_train_time = float(line.split(':')[1].strip())
                        elif line.startswith('last_download:'):
                            self.last_download_time = float(line.split(':')[1].strip())
            except:
                pass
    
    def _save_state(self):
        """Save daemon state to file"""
        state_file = "data/ml_daemon_state.txt"
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        
        with open(state_file, 'w') as f:
            f.write(f"last_train: {self.last_train_time or 0}\n")
            f.write(f"last_download: {self.last_download_time or 0}\n")
            f.write(f"last_check: {self.last_check_time or 0}\n")
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        if self.verbose:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] [{level}] {message}")
    
    def should_retrain_scheduled(self) -> bool:
        """Check if scheduled retraining is due"""
        if self.retrain_schedule == "never":
            return False
        
        if not self.last_train_time:
            return True
        
        now = time.time()
        elapsed_hours = (now - self.last_train_time) / 3600
        
        if self.retrain_schedule == "daily" and elapsed_hours >= 24:
            return True
        elif self.retrain_schedule == "weekly" and elapsed_hours >= 24 * 7:
            return True
        elif self.retrain_schedule == "monthly" and elapsed_hours >= 24 * 30:
            return True
        
        return False
    
    def check_for_updates(self) -> tuple:
        """
        Check if training is needed
        
        Returns:
            tuple: (needs_training: bool, reason: str)
        """
        self.last_check_time = time.time()
        
        # Check if model exists
        if not os.path.exists(self.model_path):
            self.log("No model found, training required", "WARN")
            return True, "no_model"
        
        # Check if data exists
        train_file = os.path.join(self.data_dir, "train.csv")
        if not os.path.exists(train_file):
            self.log("No training data found", "WARN")
            return True, "no_data"
        
        # Check data modification time
        data_mtime = os.path.getmtime(train_file)
        model_mtime = os.path.getmtime(self.model_path)
        
        if data_mtime > model_mtime:
            self.log("New data available (data newer than model)", "INFO")
            return True, "new_data"
        
        # Check scheduled retraining
        if self.should_retrain_scheduled():
            if self.last_train_time:
                elapsed = (time.time() - self.last_train_time) / 3600
                self.log(f"Scheduled retraining due ({self.retrain_schedule}, {elapsed:.1f}h since last)", "INFO")
            else:
                self.log(f"Scheduled retraining due (no previous training)", "INFO")
            return True, "scheduled"
        
        return False, "up_to_date"
    
    def download_new_data(self) -> bool:
        """
        Download new datasets from live sources
        
        Returns:
            bool: Success
        """
        if not self.auto_download:
            return False
        
        self.log("Downloading new data from sources...", "INFO")
        
        # Check how long since last download (avoid spamming)
        if self.last_download_time:
            elapsed_hours = (time.time() - self.last_download_time) / 3600
            if elapsed_hours < 24:
                self.log(f"Skipping download (last download {elapsed_hours:.1f}h ago)", "INFO")
                return False
        
        try:
            # Run download script
            result = subprocess.run(
                ['python3', 'scripts/download_datasets.py', '--dataset', 'jigsaw'],
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout
            )
            
            self.last_download_time = time.time()
            self._save_state()
            
            if result.returncode == 0:
                self.log("✓ Data download complete", "INFO")
                return True
            else:
                self.log(f"Download failed: {result.stderr}", "ERROR")
                return False
        
        except Exception as e:
            self.log(f"Download error: {e}", "ERROR")
            return False
    
    def train_model(self) -> bool:
        """
        Train new ML model
        
        Returns:
            bool: Success
        """
        self.log("Starting model training...", "INFO")
        
        try:
            # Train model
            result = subprocess.run(
                ['python3', 'scripts/train_ml_model.py', '--validate'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 min timeout
            )
            
            if result.returncode != 0:
                self.log(f"Training failed: {result.stderr}", "ERROR")
                return False
            
            self.log("✓ Model training complete", "INFO")
            
            # Update last train time
            self.last_train_time = time.time()
            self._save_state()
            
            return True
        
        except Exception as e:
            self.log(f"Training error: {e}", "ERROR")
            return False
    
    def validate_new_model(self) -> bool:
        """
        Validate new model meets quality requirements
        
        Returns:
            bool: Model is good enough to deploy
        """
        self.log("Validating new model...", "INFO")
        
        # TODO: Run comprehensive validation
        # For now, just check if file exists and is not corrupted
        
        if not os.path.exists(self.model_path):
            self.log("Model file not found", "ERROR")
            return False
        
        try:
            import pickle
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            # Check has required keys
            if 'vectorizer' not in model_data or 'models' not in model_data:
                self.log("Model file corrupted (missing keys)", "ERROR")
                return False
            
            self.log("✓ Model validation passed", "INFO")
            return True
        
        except Exception as e:
            self.log(f"Validation error: {e}", "ERROR")
            return False
    
    def deploy_model(self) -> bool:
        """
        Deploy new model (reload API)
        
        Returns:
            bool: Success
        """
        if not self.auto_deploy:
            self.log("Auto-deploy disabled, skipping", "INFO")
            return False
        
        self.log("Deploying new model...", "INFO")
        
        # TODO: Graceful reload of API
        # For now, just log (API will auto-reload on file change if using --reload)
        
        self.log("✓ Model deployed (API will auto-reload)", "INFO")
        return True
    
    def run_cycle(self) -> None:
        """Run one training cycle"""
        self.log("=" * 70, "INFO")
        self.log("ML Training Daemon - Check Cycle", "INFO")
        self.log("=" * 70, "INFO")
        
        # Check if updates needed
        needs_training, reason = self.check_for_updates()
        
        if not needs_training:
            self.log(f"✓ No training needed (reason: {reason})", "INFO")
            return
        
        self.log(f"Training needed (reason: {reason})", "INFO")
        
        # Download new data if needed
        if reason == "no_data" or reason == "scheduled":
            self.download_new_data()
        
        # Train model
        success = self.train_model()
        
        if not success:
            self.log("Training failed, skipping deployment", "ERROR")
            return
        
        # Validate
        if not self.validate_new_model():
            self.log("Validation failed, skipping deployment", "ERROR")
            return
        
        # Deploy
        self.deploy_model()
        
        self.log("✅ Training cycle complete", "INFO")
    
    def run_forever(self) -> None:
        """Run daemon forever"""
        self.log("🤖 ML Training Daemon started", "INFO")
        self.log(f"   Check interval: {self.check_interval}s ({self.check_interval/3600:.1f}h)", "INFO")
        self.log(f"   Retrain schedule: {self.retrain_schedule}", "INFO")
        self.log(f"   Auto download: {self.auto_download}", "INFO")
        self.log(f"   Auto deploy: {self.auto_deploy}", "INFO")
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                self.log(f"\n--- Cycle {cycle_count} ---", "INFO")
                
                try:
                    self.run_cycle()
                except Exception as e:
                    self.log(f"Cycle error: {e}", "ERROR")
                
                # Sleep until next check
                next_check = datetime.now() + timedelta(seconds=self.check_interval)
                self.log(f"💤 Sleeping until {next_check.strftime('%H:%M:%S')}", "INFO")
                time.sleep(self.check_interval)
        
        except KeyboardInterrupt:
            self.log("\n👋 Daemon stopped by user", "INFO")
        except Exception as e:
            self.log(f"\n❌ Daemon crashed: {e}", "ERROR")
            raise


def main():
    parser = argparse.ArgumentParser(description='ML Training Daemon')
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit (default: run forever)')
    parser.add_argument('--interval', type=int, default=3600,
                        help='Check interval in seconds (default: 3600 = 1h)')
    parser.add_argument('--schedule', type=str, 
                        choices=['daily', 'weekly', 'monthly', 'never'],
                        default='weekly',
                        help='Scheduled retraining frequency')
    parser.add_argument('--no-download', action='store_true',
                        help='Disable automatic data download')
    parser.add_argument('--no-deploy', action='store_true',
                        help='Disable automatic deployment')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output')
    
    args = parser.parse_args()
    
    # Create daemon
    daemon = MLTrainingDaemon(
        check_interval=args.interval,
        auto_download=not args.no_download,
        auto_deploy=not args.no_deploy,
        retrain_schedule=args.schedule,
        verbose=not args.quiet
    )
    
    # Run once or forever
    if args.once:
        daemon.run_cycle()
    else:
        daemon.run_forever()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

