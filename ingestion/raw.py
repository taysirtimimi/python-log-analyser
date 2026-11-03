
import gzip
import os

def toRows(path):
    files = os.listdir(path)
    rows = []

    for file in files:
        file_path = path + '/' + file

        opener = gzip.open(
            filename=file_path,
            mode='rt',
            encoding='utf-8'
        )

        with opener as f:
            rows.extend(f.readlines())

    return rows
