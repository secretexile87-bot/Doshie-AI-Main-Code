import subprocess
import time

def check_service_status(service_name):
    try:
        result = subprocess.run(['systemctl', '--user', 'is-active', service_name], capture_output=True, text=True, check=True)
        if result.stdout.strip() == 'active':
            print(f"{service_name} is active.")
        else:
            print(f"{service_name} is not active.")
    except subprocess.CalledProcessError as e:
        print(f"Error checking {service_name}: {e.stderr}")

def monitor_service(service_name, interval=60):
    while True:
        check_service_status(service_name)
        time.sleep(interval)

if __name__ == "__main__":
    service_name = "doshie-voice-studio.service"
    monitor_service(service_name)