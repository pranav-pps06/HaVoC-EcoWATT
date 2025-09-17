import random
import time
import threading
from datetime import datetime, timedelta
import sqlite3
import json
import os
from contextlib import contextmanager

class IoTSimulator:
    def __init__(self, db_path='havoc_ecowatt.db'):
        self.db_path = db_path
        self.running = False
        self.thread = None
        self.lock_file = 'simulation.lock'
        
        # Appliance behavior patterns
        self.appliance_patterns = {
            'air_conditioner': {
                'temp_range': (16, 30),
                'power_range': (1500, 3000),
                'base_probability': 0.4,
                'peak_hours': [14, 15, 16, 21, 22, 23],
                'off_hours': [2, 3, 4, 5, 6],
                'temp_change_rate': 0.5
            },
            'refrigerator': {
                'temp_range': (2, 8),
                'power_range': (150, 300),
                'base_probability': 0.9,  # Always on, compressor cycles
                'peak_hours': [],
                'off_hours': [],
                'temp_change_rate': 0.2
            },
            'washing_machine': {
                'temp_range': (20, 60),
                'power_range': (500, 2000),
                'base_probability': 0.05,  # Rarely on
                'peak_hours': [9, 10, 11, 19, 20],
                'off_hours': [0, 1, 2, 3, 4, 5, 6],
                'temp_change_rate': 1.0
            },
            'water_heater': {
                'temp_range': (40, 80),
                'power_range': (3000, 4500),
                'base_probability': 0.25,
                'peak_hours': [6, 7, 8, 18, 19, 20],
                'off_hours': [1, 2, 3, 4],
                'temp_change_rate': 0.8
            },
            'television': {
                'temp_range': (25, 45),
                'power_range': (100, 400),
                'base_probability': 0.3,
                'peak_hours': [19, 20, 21, 22],
                'off_hours': [1, 2, 3, 4, 5, 6, 7, 8],
                'temp_change_rate': 0.3
            },
            'microwave': {
                'temp_range': (30, 80),
                'power_range': (800, 1200),
                'base_probability': 0.08,  # Used briefly
                'peak_hours': [7, 8, 12, 13, 18, 19],
                'off_hours': [0, 1, 2, 3, 4, 5, 6],
                'temp_change_rate': 2.0
            },
            'dishwasher': {
                'temp_range': (40, 70),
                'power_range': (1200, 2400),
                'base_probability': 0.1,
                'peak_hours': [20, 21, 22],
                'off_hours': [0, 1, 2, 3, 4, 5, 6, 7],
                'temp_change_rate': 1.5
            }
        }
        
        # Initialize database
        self.init_database()
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables if they don't exist"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create appliances table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appliances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    power_rating DECIMAL(8,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create appliance_data table for real-time data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appliance_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appliance_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    is_on BOOLEAN NOT NULL,
                    temperature DECIMAL(5,2),
                    power_consumption DECIMAL(8,2) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (appliance_id) REFERENCES appliances (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_appliance_data_timestamp 
                ON appliance_data (appliance_id, timestamp)
            ''')
            
            # Create hourly aggregated data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hourly_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    appliance_id INTEGER NOT NULL,
                    hour_start DATETIME NOT NULL,
                    avg_power DECIMAL(8,2),
                    total_energy DECIMAL(10,4),
                    on_duration_minutes INTEGER,
                    min_temperature DECIMAL(5,2),
                    max_temperature DECIMAL(5,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(appliance_id, hour_start),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (appliance_id) REFERENCES appliances (id)
                )
            ''')
            
            conn.commit()
            print("Database tables initialized successfully")
    
    def get_all_appliances(self):
        """Get all active appliances from all users"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.id, a.user_id, a.name, a.type, a.power_rating
                FROM appliances a
                WHERE a.is_active = 1
                ORDER BY a.user_id, a.id
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_latest_data(self, appliance_id):
        """Get the most recent data for an appliance"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM appliance_data 
                WHERE appliance_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (appliance_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_time_based_probability(self, appliance_type, current_hour):
        """Adjust on/off probability based on time of day"""
        pattern = self.appliance_patterns.get(appliance_type, {})
        base_prob = pattern.get('base_probability', 0.5)
        peak_hours = pattern.get('peak_hours', [])
        off_hours = pattern.get('off_hours', [])
        
        if current_hour in peak_hours:
            return min(0.95, base_prob * 2.0)
        elif current_hour in off_hours:
            return max(0.05, base_prob * 0.1)
        else:
            return base_prob
    
    def simulate_appliance_data(self, appliance):
        """Generate realistic data for a single appliance"""
        appliance_type = appliance['type']
        pattern = self.appliance_patterns.get(appliance_type, 
                                            self.appliance_patterns['television'])
        
        current_hour = datetime.now().hour
        
        # Get previous state from database
        prev_data = self.get_latest_data(appliance['id'])
        
        # Determine if appliance is on/off based on time and patterns
        on_probability = self.get_time_based_probability(appliance_type, current_hour)
        is_on = random.random() < on_probability
        
        # Generate temperature based on appliance type and previous value
        temp_range = pattern.get('temp_range', (20, 30))
        if prev_data:
            # Gradual temperature change
            prev_temp = prev_data['temperature'] or random.uniform(*temp_range)
            temp_change = random.uniform(-pattern['temp_change_rate'], 
                                       pattern['temp_change_rate'])
            temperature = max(temp_range[0], 
                            min(temp_range[1], prev_temp + temp_change))
        else:
            temperature = random.uniform(*temp_range)
        
        # Generate power consumption
        if is_on:
            power_range = pattern.get('power_range', (100, 1000))
            base_power = random.uniform(*power_range)
            
            # Add variance based on appliance behavior
            if appliance_type in ['air_conditioner', 'water_heater']:
                # Temperature-dependent power consumption
                if appliance_type == 'air_conditioner':
                    # More power when it's hotter (cooling more)
                    temp_factor = max(0, (temperature - 20) / 10)
                else:  # water_heater
                    # More power when water is cooler (heating more)
                    temp_factor = max(0, (60 - temperature) / 20)
                
                power_consumption = base_power * (1 + temp_factor * 0.4)
            else:
                # Random variance for other appliances
                variance = random.uniform(0.8, 1.2)
                power_consumption = base_power * variance
        else:
            # Standby power (small amount)
            standby_power = {
                'air_conditioner': random.uniform(5, 15),
                'refrigerator': random.uniform(2, 8),
                'television': random.uniform(1, 5),
                'washing_machine': random.uniform(1, 3),
                'dishwasher': random.uniform(1, 3),
                'microwave': random.uniform(2, 8),
                'water_heater': random.uniform(3, 10)
            }
            power_consumption = standby_power.get(appliance_type, random.uniform(1, 5))
        
        return {
            'appliance_id': appliance['id'],
            'user_id': appliance['user_id'],
            'is_on': is_on,
            'temperature': round(temperature, 2),
            'power_consumption': round(power_consumption, 2),
            'timestamp': datetime.now()
        }
    
    def update_database(self, data_list):
        """Insert new data for multiple appliances into the database"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Insert all appliance data
            cursor.executemany('''
                INSERT INTO appliance_data 
                (appliance_id, user_id, is_on, temperature, power_consumption, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', [
                (data['appliance_id'], data['user_id'], data['is_on'], 
                 data['temperature'], data['power_consumption'], data['timestamp'])
                for data in data_list
            ])
            
            conn.commit()
    
    def cleanup_old_data(self):
        """Remove data older than 30 days to prevent database bloat"""
        cutoff_date = datetime.now() - timedelta(days=30)
        
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM appliance_data 
                WHERE timestamp < ?
            ''', (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                print(f"Cleaned up {deleted_count} old records")
    
    def get_user_stats(self):
        """Get statistics about active users and appliances"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count active users
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as user_count
                FROM appliances
                WHERE is_active = 1
            ''')
            user_count = cursor.fetchone()[0]
            
            # Count total appliances
            cursor.execute('''
                SELECT COUNT(*) as appliance_count
                FROM appliances
                WHERE is_active = 1
            ''')
            appliance_count = cursor.fetchone()[0]
            
            # Count by appliance type
            cursor.execute('''
                SELECT type, COUNT(*) as count
                FROM appliances
                WHERE is_active = 1
                GROUP BY type
            ''')
            type_counts = dict(cursor.fetchall())
            
            return {
                'users': user_count,
                'appliances': appliance_count,
                'by_type': type_counts
            }
    
    def run_simulation(self):
        """Main simulation loop for all users"""
        cleanup_counter = 0
        
        while self.running:
            try:
                # Get all active appliances from ALL users
                appliances = self.get_all_appliances()
                
                if not appliances:
                    print("No appliances found, waiting...")
                    time.sleep(10)
                    continue
                
                # Generate data for ALL appliances
                all_data = []
                for appliance in appliances:
                    data = self.simulate_appliance_data(appliance)
                    all_data.append(data)
                
                # Bulk update database
                self.update_database(all_data)
                
                # Get statistics
                stats = self.get_user_stats()
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated {len(appliances)} appliances "
                      f"for {stats['users']} users - Types: {stats['by_type']}")
                
                # Cleanup old data every hour (360 iterations * 10 seconds)
                cleanup_counter += 1
                if cleanup_counter >= 360:
                    self.cleanup_old_data()
                    cleanup_counter = 0
                
                # Wait 10 seconds before next update
                time.sleep(10)
                
            except Exception as e:
                print(f"Simulation error: {e}")
                time.sleep(10)
    
    def is_simulation_running(self):
        """Check if simulation is already running via lock file"""
        if os.path.exists(self.lock_file):
            try:
                with open(self.lock_file, 'r') as f:
                    pid = int(f.read().strip())
                # Check if process is still running (simplified check)
                try:
                    os.kill(pid, 0)  # Send signal 0 to check if process exists
                    return True
                except OSError:
                    # Process doesn't exist, remove stale lock file
                    os.remove(self.lock_file)
                    return False
            except (ValueError, IOError):
                # Invalid lock file, remove it
                try:
                    os.remove(self.lock_file)
                except OSError:
                    pass
                return False
        return False
    
    def create_lock_file(self):
        """Create lock file with current process ID"""
        try:
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except IOError:
            return False
    
    def remove_lock_file(self):
        """Remove lock file"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except OSError:
            pass
    
    def start(self):
        """Start the simulation service"""
        if self.running:
            print("Simulation is already running in this instance")
            return
            
        # Check if another instance is already running
        if self.is_simulation_running():
            print("IoT Simulation is already running in another process")
            return
        
        # Create lock file
        if not self.create_lock_file():
            print("Could not create lock file, simulation may already be running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run_simulation, daemon=True)
        self.thread.start()
        
        stats = self.get_user_stats()
        print(f"IoT Simulation started for {stats['users']} users with {stats['appliances']} appliances")
    
    def stop(self):
        """Stop the simulation service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.remove_lock_file()
        print("IoT Simulation stopped")

# Global simulator instance
simulator = IoTSimulator()

if __name__ == "__main__":
    # For testing the simulator independently
    simulator.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        simulator.stop()
