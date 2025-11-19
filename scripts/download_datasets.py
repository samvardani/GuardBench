#!/usr/bin/env python3
"""
Download datasets from live sources

Supports:
- Kaggle (Jigsaw, Civil Comments, etc.)
- GitHub repositories
- Hugging Face datasets
- Custom URLs

Usage:
    python scripts/download_datasets.py
    python scripts/download_datasets.py --source kaggle --dataset jigsaw
    python scripts/download_datasets.py --all
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd


def download_jigsaw_kaggle(output_dir: str = "datasets_raw", verbose: bool = True):
    """
    Download Jigsaw Toxic Comments from Kaggle
    
    Requires: kaggle API credentials (~/.kaggle/kaggle.json)
    """
    if verbose:
        print("\n📥 Downloading Jigsaw Toxic Comments (Kaggle)...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if kaggle is installed
    try:
        subprocess.run(['kaggle', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Kaggle CLI not found. Install: pip install kaggle")
        print("   Also set up credentials: https://github.com/Kaggle/kaggle-api")
        return False
    
    # Download dataset
    dataset_name = "julian3833/jigsaw-toxic-comment-classification-challenge"
    
    if verbose:
        print(f"   Downloading {dataset_name}...")
    
    try:
        # Download to temp directory
        subprocess.run([
            'kaggle', 'datasets', 'download',
            '-d', dataset_name,
            '-p', output_dir,
            '--unzip'
        ], check=True, capture_output=not verbose)
        
        if verbose:
            print(f"   ✓ Downloaded to {output_dir}/")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading: {e}")
        return False


def download_davidson_github(output_dir: str = "datasets_raw", verbose: bool = True):
    """
    Download Davidson Hate Speech dataset from GitHub
    """
    if verbose:
        print("\n📥 Downloading Davidson Hate Speech (GitHub)...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    url = "https://raw.githubusercontent.com/t-davidson/hate-speech-and-offensive-language/master/data/labeled_data.csv"
    output_file = os.path.join(output_dir, "hate_speech_davidson.csv")
    
    if os.path.exists(output_file):
        if verbose:
            print(f"   ⚠ File already exists: {output_file}")
        return True
    
    try:
        import urllib.request
        urllib.request.urlretrieve(url, output_file)
        
        if verbose:
            print(f"   ✓ Downloaded to {output_file}")
        
        return True
    except Exception as e:
        print(f"❌ Error downloading: {e}")
        return False


def download_toxigen_github(output_dir: str = "datasets_raw", verbose: bool = True):
    """
    Download ToxiGen dataset from GitHub
    """
    if verbose:
        print("\n📥 Downloading ToxiGen (GitHub)...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Clone repo if needed
    repo_dir = os.path.join(output_dir, "ToxiGen")
    
    if os.path.exists(repo_dir):
        if verbose:
            print(f"   ⚠ Repository already exists: {repo_dir}")
        return True
    
    try:
        subprocess.run([
            'git', 'clone',
            'https://github.com/microsoft/ToxiGen.git',
            repo_dir
        ], check=True, capture_output=not verbose)
        
        if verbose:
            print(f"   ✓ Cloned to {repo_dir}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error cloning: {e}")
        return False


def check_for_new_data(data_dir: str = "datasets_raw", verbose: bool = True):
    """
    Check if new data is available compared to last training
    
    Returns:
        tuple: (has_new_data: bool, info: dict)
    """
    if verbose:
        print("\n🔍 Checking for new data...")
    
    # Check if training file exists
    train_file = os.path.join(data_dir, "train.csv")
    
    if not os.path.exists(train_file):
        if verbose:
            print("   ⚠ No training data found")
        return False, {'reason': 'no_data'}
    
    # Check modification time
    train_mtime = os.path.getmtime(train_file)
    train_age_hours = (time.time() - train_mtime) / 3600
    
    # Check if model exists and is newer than data
    model_file = "models/ml_fast.pkl"
    
    if os.path.exists(model_file):
        model_mtime = os.path.getmtime(model_file)
        
        if model_mtime > train_mtime:
            if verbose:
                print(f"   ✓ Model is up to date (data age: {train_age_hours:.1f}h)")
            return False, {'reason': 'model_newer', 'data_age_hours': train_age_hours}
        else:
            if verbose:
                print(f"   🆕 New data available! (data age: {train_age_hours:.1f}h)")
            return True, {'reason': 'new_data', 'data_age_hours': train_age_hours}
    else:
        if verbose:
            print("   🆕 No model found, training needed")
        return True, {'reason': 'no_model'}


def main():
    parser = argparse.ArgumentParser(description='Download datasets for ML training')
    parser.add_argument('--source', type=str, choices=['kaggle', 'github', 'all'],
                        default='kaggle', help='Data source')
    parser.add_argument('--dataset', type=str, choices=['jigsaw', 'davidson', 'toxigen', 'all'],
                        default='jigsaw', help='Dataset to download')
    parser.add_argument('--output', type=str, default='datasets_raw',
                        help='Output directory')
    parser.add_argument('--check-only', action='store_true',
                        help='Only check if new data is needed')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output')
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    # Check only mode
    if args.check_only:
        has_new, info = check_for_new_data(args.output, verbose=verbose)
        return 0 if has_new else 1
    
    # Download datasets
    success = True
    
    if args.dataset == 'jigsaw' or args.dataset == 'all':
        success &= download_jigsaw_kaggle(args.output, verbose=verbose)
    
    if args.dataset == 'davidson' or args.dataset == 'all':
        success &= download_davidson_github(args.output, verbose=verbose)
    
    if args.dataset == 'toxigen' or args.dataset == 'all':
        success &= download_toxigen_github(args.output, verbose=verbose)
    
    if verbose:
        if success:
            print("\n✅ All downloads complete!")
        else:
            print("\n⚠ Some downloads failed")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())












