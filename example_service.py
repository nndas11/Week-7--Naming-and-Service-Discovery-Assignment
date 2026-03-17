"""
Example Service - Demonstrates how to register with the service registry

This simulates a microservice that:
1. Registers itself on startup
2. Sends periodic heartbeats
3. Deregisters on shutdown
"""

import requests
import time
import signal
import sys
from threading import Thread, Event

class ServiceClient:
    def __init__(self, service_name, service_address, registry_url="http://localhost:5001"):
        self.service_name = service_name
        self.service_address = service_address
        self.registry_url = registry_url
        self.stop_event = Event()
        self.heartbeat_interval = 10  # seconds
        
    def register(self):
        """Register this service with the registry"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.post(
                f"{self.registry_url}/register",
                json={
                    "service": self.service_name,
                    "address": self.service_address
                },
                headers=headers,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                print(f"✓ Registered {self.service_name} at {self.service_address}")
                return True
            else:
                print(f"✗ Registration failed (status {response.status_code})")
                print(f"   Response: {response.text if response.text else 'Empty response'}")
                print(f"   URL: {self.registry_url}/register")
                return False
        except requests.exceptions.ConnectionError:
            print(f"✗ Cannot connect to registry at {self.registry_url}")
            print(f"   Make sure the registry is running: python3 service_registry_improved.py")
            return False
        except requests.exceptions.Timeout:
            print(f"✗ Connection timeout to registry at {self.registry_url}")
            return False
        except Exception as e:
            print(f"✗ Registration error: {e}")
            return False
    
    def deregister(self):
        """Deregister this service from the registry"""
        try:
            response = requests.post(
                f"{self.registry_url}/deregister",
                json={
                    "service": self.service_name,
                    "address": self.service_address
                }
            )
            
            if response.status_code == 200:
                print(f"✓ Deregistered {self.service_name}")
                return True
            else:
                print(f"✗ Deregistration failed: {response.json()}")
                return False
        except Exception as e:
            print(f"✗ Deregistration error: {e}")
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to registry"""
        try:
            response = requests.post(
                f"{self.registry_url}/heartbeat",
                json={
                    "service": self.service_name,
                    "address": self.service_address
                }
            )
            
            if response.status_code == 200:
                print(f"♥ Heartbeat sent for {self.service_name}")
                return True
            else:
                print(f"✗ Heartbeat failed: {response.json()}")
                return False
        except Exception as e:
            print(f"✗ Heartbeat error: {e}")
            return False
    
    def heartbeat_loop(self):
        """Background thread that sends periodic heartbeats"""
        while not self.stop_event.is_set():
            self.send_heartbeat()
            self.stop_event.wait(self.heartbeat_interval)
    
    def discover_service(self, service_name):
        """Discover instances of another service"""
        try:
            response = requests.get(f"{self.registry_url}/discover/{service_name}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n🔍 Discovered {service_name}:")
                print(f"   Found {data['count']} instance(s)")
                for instance in data['instances']:
                    print(f"   - {instance['address']} (uptime: {instance['uptime_seconds']:.1f}s)")
                return data['instances']
            else:
                print(f"✗ Discovery failed: {response.json()}")
                return []
        except Exception as e:
            print(f"✗ Discovery error: {e}")
            return []
    
    def start(self):
        """Start the service and register with registry"""
        # Register
        if not self.register():
            print("Failed to register. Exiting.")
            return
        
        # Start heartbeat thread
        heartbeat_thread = Thread(target=self.heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        print(f"\n{self.service_name} is running...")
        print("Press Ctrl+C to stop\n")
        
        # Setup signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print("\n\nShutting down gracefully...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Keep the main thread alive
        while not self.stop_event.is_set():
            time.sleep(1)
    
    def stop(self):
        """Stop the service and deregister"""
        self.stop_event.set()
        self.deregister()


def demo_service_discovery():
    """Demonstrate service discovery"""
    print("\n" + "="*60)
    print("SERVICE DISCOVERY DEMO")
    print("="*60)
    
    registry_url = "http://localhost:5001"
    
    # Check registry health
    try:
        response = requests.get(f"{registry_url}/health")
        if response.status_code == 200:
            print("✓ Registry is healthy\n")
        else:
            print("✗ Registry health check failed")
            return
    except Exception as e:
        print(f"✗ Cannot connect to registry: {e}")
        print("Make sure the registry is running on port 5001")
        return
    
    # List all services
    try:
        response = requests.get(f"{registry_url}/services")
        if response.status_code == 200:
            data = response.json()
            print(f"📋 Total services registered: {data['total_services']}")
            for service, info in data['services'].items():
                print(f"   - {service}: {info['active_instances']} active instance(s)")
            print()
    except Exception as e:
        print(f"✗ Error listing services: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python example_service.py <service_name> <port>")
        print("\nExample:")
        print("  python example_service.py user-service 8001")
        print("  python example_service.py payment-service 8002")
        print("\nOr run demo:")
        print("  python example_service.py demo")
        sys.exit(1)
    
    if sys.argv[1] == "demo":
        demo_service_discovery()
    else:
        service_name = sys.argv[1]
        port = sys.argv[2]
        service_address = f"http://localhost:{port}"
        
        client = ServiceClient(service_name, service_address)
        client.start()

# Made with Bob
