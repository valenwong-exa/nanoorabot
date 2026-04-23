# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('oracle_ai_blogs_20260421.txt', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('标题:'):
            print(line.strip())
