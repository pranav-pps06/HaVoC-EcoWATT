#!/usr/bin/env python3
"""
Test script to add sample users and appliances for simulation testing
"""

import sqlite3
import random

def create_sample_data():
    """Create sample users and appliances for testing"""
    
    # Connect to database
    conn = sqlite3.connect('energy_optimizer.db')
    cursor = conn.cursor()
    
    # Sample users
    sample_users = [
        ('john_doe', 'john@example.com', 'password123'),
        ('jane_smith', 'jane@example.com', 'password123'),
        ('bob_wilson', 'bob@example.com', 'password123'),
        ('alice_brown', 'alice@example.com', 'password123'),
        ('mike_johnson', 'mike@example.com', 'password123'),
    ]
    
    print("Creating sample users...")
    for username, email, password in sample_users:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, email, password)
                VALUES (?, ?, ?)
            ''', (username, email, password))
        except Exception as e:
            print(f"Error creating user {username}: {e}")
    
    conn.commit()
    
    # Get user IDs
    cursor.execute('SELECT id, username FROM users')
    users = cursor.fetchall()
    
    # Sample appliances for each user
    appliance_types = [
        'air_conditioner', 'refrigerator', 'washing_machine', 
        'water_heater', 'television', 'microwave', 'dishwasher'
    ]
    
    appliance_names = {
        'air_conditioner': ['Living Room AC', 'Bedroom AC', 'Office AC'],
        'refrigerator': ['Kitchen Fridge', 'Mini Fridge', 'Garage Freezer'],
        'washing_machine': ['Front Load Washer', 'Top Load Washer'],
        'water_heater': ['Main Water Heater', 'Instant Water Heater'],
        'television': ['Living Room TV', 'Bedroom TV', 'Kitchen TV'],
        'microwave': ['Kitchen Microwave', 'Office Microwave'],
        'dishwasher': ['Kitchen Dishwasher']
    }
    
    power_ratings = {
        'air_conditioner': (1500, 3000),
        'refrigerator': (150, 300),
        'washing_machine': (500, 2000),
        'water_heater': (3000, 4500),
        'television': (100, 400),
        'microwave': (800, 1200),
        'dishwasher': (1200, 2400)
    }
    
    print("Creating sample appliances for each user...")
    for user_id, username in users:
        print(f"Adding appliances for user: {username}")
        
        # Each user gets 3-7 random appliances
        num_appliances = random.randint(3, 7)
        selected_types = random.sample(appliance_types, num_appliances)
        
        for appliance_type in selected_types:
            # Random name from the type's name list
            names = appliance_names[appliance_type]
            name = random.choice(names)
            
            # Random power rating within the type's range
            power_range = power_ratings[appliance_type]
            power_rating = random.randint(power_range[0], power_range[1])
            
            try:
                cursor.execute('''
                    INSERT INTO appliances (user_id, name, type, power_rating)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, name, appliance_type, power_rating))
                print(f"  - Added: {name} ({appliance_type}) - {power_rating}W")
            except Exception as e:
                print(f"  - Error adding {name}: {e}")
    
    conn.commit()
    
    # Print summary
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM appliances')
    appliance_count = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT type, COUNT(*) 
        FROM appliances 
        GROUP BY type 
        ORDER BY COUNT(*) DESC
    ''')
    type_counts = cursor.fetchall()
    
    print(f"\n=== SUMMARY ===")
    print(f"Created {user_count} users")
    print(f"Created {appliance_count} appliances")
    print(f"\nAppliances by type:")
    for appliance_type, count in type_counts:
        print(f"  {appliance_type}: {count}")
    
    conn.close()
    print(f"\nSample data created successfully!")
    print(f"Start your Flask app and the simulation will begin automatically.")

if __name__ == "__main__":
    create_sample_data()
