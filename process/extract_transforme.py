
import re

def extract_from_row(row):
    pattern = re.compile(
        r'(\w{3})\s+(\d{2})\s+(\d{2}:\d{2}:\d{2}).+:\s(\w+)'
    )

    match = re.search(pattern, row)

    if match:
        print(
            f'Month: {match.group(1)}\n'
            f'Day: {match.group(2)}, Time: {match.group(3)}, '
            f'Message: {match.group(4)}'
        )


def get_statistics(rows):
    invalid_user = 0
    failed_password = 0

    for row in rows:
        if "invalid user" in row.lower():
            invalid_user += 1

        if "failed password" in row.lower():
            failed_password += 1

    return invalid_user, failed_password
