
##############

# Reads BLE IMU data from the ESP32C3 Devkit 1 device or Circuit PLayground Bluefruit Device.

    # FUNCTION: 
            # Input Patient Name, Circuitpy Device Name at any time, then hit "Save Inputs" 
                # Default Bluefruit device is CIRCUITPYc67c, have to change manually if using the other one

            # Click "Discover Devices" to scan for ESP32 or Bluefruit devices.
                #Select ESP or Bluefruit device 
                #Only 1 Bluefruit device can be detected at a time.

            # Click "Start" to begin collection of data from selected device

            # Click "Stop" to stop collection of data from selected device
                # Then, the Save Inputs & Device selection can be done again.



    # Uses of the GUI:
        # 1. Device address input for BLE (In case we change devices)
        # 2. Patient name input
            # 2.1. Unique file names are generated by the time stamp anyway, regardless of patient name
                # Example: Could do patient name = Andre and run 3 trials, each trial will be saved with a unique file name due to the timee marker

    # New file generation: new unique file names are produced by a time marker: day-month-year_hour-minute-second

    # Outputs: Saves text files with timestamp, x,y,z accelerometer data like for the Bluefruit
        #For each new file, timestamp starts at 0 and increments each time a notification is received (time is in seconds)
    

    

    # Future Directions: could find a way to automatically detect ESP32 Adress?

##############

import asyncio
import threading
from bleak import BleakClient, BleakScanner
import time
import struct
import os
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from datetime import datetime

# Default values
ESP32_ADDRESS = "40:4C:CA:8C:60:5A"
ESP32_NAME= "ESP32C3_IMU"
KNOWN_CIRCUITPY_NAMES = ["CIRCUITPYb48a", "CIRCUITPYc67c"]

# Globals
start_time = None
last_notification_time = time.time()
file_paths = [None, None]  # File paths for each device

stop_event = threading.Event()

data_displays = [None, None]
data_buffers = ["", ""]  # Global buffer for handling CircuitPy data

selected_devices = [None,None]
device_names = [None,None]
patient_names = ["", ""]  # Patient names for each device



def create_file_path(device_index):
    """
    Creates a file path for saving data based on the patient name and current timestamp.
    """
   # global file_path

    device_name = device_names[device_index] 
   
    patient_name = patient_names[device_index].replace(" ", "_") or f"Patient{device_index+1}"
    print(device_name)
    print(patient_name)

    time_stamp = time.strftime("%d-%b-%Y_%H-%M-%S")
    filename = f"acceleration_data_{device_name}_{patient_name}_data_{time_stamp}.txt"
    file_path = os.path.join(os.getcwd(), filename)
    return file_path

def parse_accel_data(data, device_index, device_name):
    """Parse incoming BLE data based on the selected device."""
    #global data_buffer
    print(f"Raw data received: {data}")
    try:
        if device_name == ESP32_NAME:
            accel_x, accel_y, accel_z = struct.unpack('<3f', data)
           
            return accel_x, accel_y, accel_z
        
        # Default case for other devices (e.g., Circuit Playground Bluefruit)
        elif device_name in KNOWN_CIRCUITPY_NAMES:
            buffer = data_buffers[device_index]
            data_str = data.decode("utf-8").strip().replace("(", "").replace(")", "")
            buffer += data_str

            
                # Process complete data (timestamp, x, y, z)
            if "," in buffer:
                parts = buffer.split(",", 2)  # Limit to 4 parts (timestamp, x, y, z)
                if len(parts) == 3:
                    x, y, z = map(float, parts)
                    data_buffers[device_index] = ""
                # data_buffer = ""  # Clear buffer after processing
                    return x, y, z  # Return parsed values
                return None
            data_buffers[device_index] = buffer
            #return None
            
        
    except Exception as e:
        print(f"Error parsing data for device {device_index}: {e}")
        return None, None, None


def notification_handler(sender: int, data: bytearray, device_index):
    global start_time, last_notification_time #data_display1, data_display2

    if start_time is None:
        start_time = time.time()

    current_time = time.time()
    relative_time = current_time - start_time
    utc_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Include milliseconds
    device_name = device_names[device_index]  # Get the device name

    try:
        accel_x, accel_y, accel_z = parse_accel_data(data, device_index, device_name)
        if accel_x is not None and accel_y is not None and accel_z is not None:
            output = f"Device {device_index + 1} - Relative time: {relative_time:.3f}, UTC: {utc_time}, Accel: X={accel_x:.4f}, Y={accel_y:.4f}, Z={accel_z:.4f}\n"
            print(output)

            if file_paths[device_index]:
                with open(file_paths[device_index], "a", encoding="utf-8") as file:
                    file.write(f"{utc_time},{accel_x},{accel_y},{accel_z}\n")

            if data_displays[device_index]:
                data_displays[device_index].insert(tk.END, output)
                data_displays[device_index].see(tk.END)
        else:
            print("Received invalid data, skipping notification.")

    except TypeError as e:
        print(f"Skipping invalid notification data: {e}")


## UPDATES FRO CIRCUITPY
async def discover_devices():
    """Scan for BLE devices, returning a list of discovered devices."""
    print("Scanning for devices...")
    devices = await BleakScanner.discover()
    found_devices = []

    # Add devices that match ESP32 or CircuitPy criteria
    for device in devices:
        if device.name and (device.name  in KNOWN_CIRCUITPY_NAMES or device.address == ESP32_ADDRESS):  
            found_devices.append(device)

    if not found_devices:
        print("No suitable devices found.")
        return None

    print("Discovered devices:")
    for idx, device in enumerate(found_devices, start=1):
        print(f"{idx}: {device.name} ({device.address})")

    return found_devices

def update_device_list(device_dropdowns, status_label):
    """Discover BLE devices and update the dropdown menu."""
    async def discover_and_update():
        devices = await discover_devices()
        if not devices:
            status_label.config(text="No devices found.", fg="red")
            return

        # Clear current dropdown options and add devices
        for dropdown in device_dropdowns:
            menu = dropdown["menu"]
            menu.delete(0, "end")  # Clear old options

        for device in devices:
            for i, dropdown in enumerate(device_dropdowns):
                menu = dropdown["menu"]
             
                menu.add_command(
                        label=f"{device.name} ({device.address})",
                        command=lambda d=device, idx=i: select_device(d, idx),
                    )
        status_label.config(text="Devices discovered. Select from dropdown.", fg="green")

    # Run discovery in an asyncio loop
    loop = asyncio.new_event_loop()
    threading.Thread(target=run_asyncio_task, args=(loop, discover_and_update())).start()

def select_device(device, index):
    """Update the selected device at a given index."""
    selected_devices[index] = device.address
    device_names[index]= device.name
    print(f"Device {index + 1} selected: {device.name} ({device.address})")



def select_device_gui(found_devices):
    """GUI to let users select a BLE device from discovered options."""
    def set_device_selection():
        selected_index = device_listbox.curselection()
        if selected_index:
            selected_device[0] = found_devices[selected_index[0]]
            root.destroy()

    root = tk.Tk()
    root.title("Select BLE Device")
    tk.Label(root, text="Select a device to connect to:").pack(padx=0, pady=10)

    # Listbox for device selection
    device_listbox = tk.Listbox(root, height=len(found_devices), width=50)
    for idx, device in enumerate(found_devices):
        device_listbox.insert(tk.END, f"{device.name} ({device.address})")
    device_listbox.pack(padx=0, pady=10)

    # Connect button
    tk.Button(root, text="Connect", command=set_device_selection).pack(pady=10)

    # Selected device reference
    selected_device = [None]
    root.mainloop()

    return selected_device[0]

## END UPDATE FOR CIRCUITPY
async def discover_services_and_characteristics(address):
    async with BleakClient(address) as client:
        print(f"Connected to {address}")
        if not client.is_connected:
            print("Failed to connect to the device.")
            return

        if client.services is None:  # Services are not populated until connection
            await client.get_services()

        for service in client.services:
            print(f"Found service: {service.uuid}")
            for char in service.characteristics:
                if "notify" in char.properties:
                    print(f"Characteristic with notify: {char.uuid}")


async def connect_and_subscribe(device_address, device_index):
    global stop_event
    create_file_path(device_index)
    #print(device_address)
    

    
    try: 
        # Step 3: Connect to the selected device
        async with BleakClient(device_address) as client: ##ESP32_ADDRESS
            ##print(f"Connected to {selected_device}")
            print(f"Connected to device {device_index + 1}: {device_address}")
            if not client.is_connected:
                print("Failed to connect to the device.")
                return

            stop_event.clear()

            services = client.services  # Use the services property
            if services is None:  # Services are not populated until connection
                await client.get_services()

            for service in client.services:
                for char in service.characteristics:
                    if "notify" in char.properties:
                        await client.start_notify(char.uuid, lambda s, d: notification_handler(s, d, device_index))
            print("Started receiving notifications. Press 'Stop' to end.")

            while not stop_event.is_set():
                await asyncio.sleep(1)

            if client.services is None:
                await client.get_services()

            for service in client.services:
                for char in service.characteristics:
                    try: 
                        if "notify" in char.properties:
                            await client.stop_notify(char.uuid)
                    except Exception as e:
                        print(f"Error stopping notification: {e}")

            print("Stopped receiving notifications.")

    except Exception as e:
        print(f"Error in BLE connection: {e}")

    finally:
        await client.disconnect()
        print(f"Disconnected from device {device_index + 1}. Resources freed.")

def run_asyncio_task(loop, task):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(task)

def start_collection():
    global ESP32_ADDRESS, patient_name, stop_event, start_time
    #stop_event = threading.Event()
    stop_event.clear()
    # Ensure patient names are set with defaults if not provided
    if not patient_names[0]:
        patient_names[0] = "Position 1"
    if not patient_names[1]:
        patient_names[1] = "Position 2"

    start_time = None  # Reset start_time to ensure it starts fresh for each run    
    def run_tasks():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [connect_and_subscribe(address, i) for i, address in enumerate(selected_devices) if address]
        loop.run_until_complete(asyncio.gather(*tasks))
        loop.close()
    
   
    threading.Thread(target=run_tasks).start()

def stop_collection():
    global stop_event
    stop_event.set()
    print("Stop event triggered.")
    
def save_inputs(patient_entry1,patient_entry2, status_label):
    global patient_names, file_paths 
    patient_names[0] = patient_entry1.get()
    patient_names[1] = patient_entry2.get()
    
     #Validate device selection
    for i in range(2):
        if selected_devices[i]:
            file_paths[i] = create_file_path(i)
            
    print(f"Patient names saved: {patient_names}")
    status_label.config(text="Inputs saved successfully!", fg="green")


# GUI Setup
def create_gui():
    global data_displays 

    root = tk.Tk()
    root.title("BLE Data Logger")

    tk.Button(root, text="Discover Devices", command=lambda: update_device_list(device_dropdowns, status_label)).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky ='w')
   
    # Device 1
    tk.Label(root, text="Device 1").grid(row=0, column=1, padx=5, pady=5, sticky="e")
    device_dropdown1 = tk.OptionMenu(root, tk.StringVar(), "Select a device")  # Initial placeholder
    device_dropdown1.grid(row=0, column=2, padx=5, pady=5)

    #Device 2
    tk.Label(root, text="Device 2:").grid(row=1, column=1, padx=5, pady=5, sticky="e")
    device_dropdown2 = tk.OptionMenu(root, tk.StringVar(), "Select a device")
    device_dropdown2.grid(row=1, column=2, padx=5, pady=5)

    device_dropdowns = [device_dropdown1, device_dropdown2]

    tk.Button(root, text="Save Inputs", command=lambda: save_inputs(patient_entry1, patient_entry2,status_label)).grid(row=2, column=0, columnspan=3, padx=10,pady=10, sticky ='w')
    
    # Patient Name Inputs
    tk.Label(root, text="Position 1:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
    patient_entry1 = tk.Entry(root, width=30)
    patient_entry1.grid(row=4, column=1, columnspan=2, padx=5, pady=5)
    patient_entry1.insert(0,  "Position 1")  # Default value

    tk.Label(root, text="Position 2:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
    patient_entry2 = tk.Entry(root, width=30)
    patient_entry2.grid(row=5, column=1, columnspan=2, padx=5, pady=5)
    patient_entry2.insert(0, "Position 2")  # Default value
    
    # Status label to show messages within the GUI
    status_label = tk.Label(root, text="", fg="red")
    status_label.grid(row=6, column=0, columnspan=2, pady=5)

    
    tk.Button(root, text="Start", command=start_collection, bg="green", fg="white").grid(row=7, column=0, padx=5, pady=5, sticky="e")
    tk.Button(root, text="Stop", command=stop_collection, bg="red", fg="white").grid(row=7, column=1, padx=5, pady=5, sticky="w")

    
    tk.Label(root, text="Device 1 Data:").grid(row=8, column=0, padx=5, pady=5, sticky="w")
    data_displays[0] = tk.Text(root, height=10, width=50)
    data_displays[0].grid(row=9, column=0, columnspan=2, padx=5, pady=5)

    tk.Label(root, text="Device 2 Data:").grid(row=10, column=0, padx=5, pady=5, sticky="w")
    data_displays[1] = tk.Text(root, height=10, width=50)
    data_displays[1].grid(row=11, column=0, columnspan=2, padx=5, pady=5)
    root.mainloop()

if __name__ == "__main__":
    create_gui()
