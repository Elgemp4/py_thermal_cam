import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv("data.csv")

# Convert the Date column to a datetime format (it includes both date and time)
df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y.%H:%M:%S')

# Plot for each zone
zones = df['Name'].unique()
count = 0
for zone in zones:
    zone_data = df[df['Name'] == zone]

    plt.figure(count, figsize=(10, 6))
    plt.plot(zone_data['Date'], zone_data['Avg'], label='Average Temperature', color='blue')
    plt.plot(zone_data['Date'], zone_data['Min'], label='Minimum Temperature', color='green', linestyle='--')
    plt.plot(zone_data['Date'], zone_data['Max'], label='Maximum Temperature', color='red', linestyle='--')

    plt.title(f"Temperature Trends for {zone}")
    plt.xlabel("Date and Time")
    plt.ylabel("Temperature (°C)")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)

    plt.tight_layout()
    count+=1
    plt.show()

