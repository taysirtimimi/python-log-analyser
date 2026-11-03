import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt

from ingestion import raw
from process import extract_transforme
from process import geolocation

load_dotenv()

if __name__ == "__main__":

    rows = raw.toRows('./data')

    for row in rows[:10]:
        extract_transforme.extract_from_row(row)

    invalid_user, failed_password = extract_transforme.get_statistics(rows)

    print("\nAuthentication Statistics")
    print("Invalid user:", invalid_user)
    print("Failed password:", failed_password)

    ip = os.getenv("IP_ADDRESS")

    location = geolocation.get_location(ip)

    print("\nIP Location:")
    print(location)

    labels = ["Invalid User", "Failed Password"]
    values = [invalid_user, failed_password]

    plt.bar(labels, values)

    plt.title("Authentication Failure Statistics")
    plt.xlabel("Type of Failure")
    plt.ylabel("Number of Attempts")

    plt.show()
