"""List Circuits/*.txt that have a matching .json in the same directory.
Output: one path per line, normalized with forward slashes (for Make on Windows).
"""
import os

for r, d, fs in os.walk('Circuits'):
    for f in fs:
        if f.endswith('.txt') and os.path.isfile(os.path.join(r, f[:-4] + '.json')):
            print(os.path.normpath(os.path.join(r, f)).replace(os.sep, '/'))
