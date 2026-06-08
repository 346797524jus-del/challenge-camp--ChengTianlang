import os
import sys
import json
import csv

def process_d4_pipeline():
    ra_dir = r"./student-camp-data/raw/d4"
    output_dir = r"./phase2-consolidata"
    os.makedirs(output_dir, exist_ok=True)
