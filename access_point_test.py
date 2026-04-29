import network

# Create an access point interface
ap = network.WLAN(network.AP_IF)

# Configure the AP (SSID name and optional password)
# Password must be at least 8 characters
ap.config(essid='RP2350-Access-Point', password='password123')

# Activate the interface
ap.active(True)

# Print the IP address (default is usually 192.168.4.1)
print("AP IP Address:", ap.ifconfig()[0])