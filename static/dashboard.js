// Dashboard JavaScript
class EnergyDashboard {
    constructor() {
        // Get user ID from session data passed from backend
        this.currentUserId = window.sessionData ? window.sessionData.userId : 1;
        this.updateInterval = 10000; // 10 seconds
        this.charts = {};
        this.isUpdating = false;
        
        console.log('Dashboard initialized for user ID:', this.currentUserId);
        this.init();
    }
    
    init() {
        this.initCharts();
        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.loadInitialData();
    }
    
    // Initialize Chart.js charts
    initCharts() {
        this.initUsageChart();
        this.initDistributionChart();
    }
    
    initUsageChart() {
        const ctx = document.getElementById('usageChart');
        if (!ctx) return;
        
        this.charts.usage = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.generateTimeLabels(24),
                datasets: [{
                    label: 'Power Usage (W)',
                    data: this.generateSampleData(24),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f5f9'
                        }
                    },
                    x: {
                        grid: {
                            color: '#f1f5f9'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 0,
                        hoverRadius: 5
                    }
                }
            }
        });
    }
    
    initDistributionChart() {
        const ctx = document.getElementById('distributionChart');
        if (!ctx) return;
        
        this.charts.distribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Air Conditioning', 'Water Heater', 'Refrigerator', 'TV', 'Others'],
                datasets: [{
                    data: [45, 25, 15, 10, 5],
                    backgroundColor: [
                        '#667eea',
                        '#764ba2',
                        '#10b981',
                        '#f59e0b',
                        '#ef4444'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                },
                cutout: '60%'
            }
        });
    }
    
    // Setup event listeners
    setupEventListeners() {
        // Chart period buttons
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.handleChartPeriodChange(e.target.dataset.period);
            });
        });
        
        // Add appliance form
        const form = document.getElementById('addApplianceForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleAddAppliance(e);
            });
        }
        
        // Sidebar navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleNavigation(e.target.closest('.nav-link').getAttribute('href'));
            });
        });
        
        // Recommendation apply buttons
        document.querySelectorAll('.apply-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.handleRecommendationApply(e.target);
            });
        });
        
        // Distribution period selector
        const selector = document.getElementById('distributionPeriod');
        if (selector) {
            selector.addEventListener('change', (e) => {
                this.updateDistributionChart(e.target.value);
            });
        }
    }
    
    // Real-time data updates
    startRealTimeUpdates() {
        this.updateDashboard();
        this.updateInterval = setInterval(() => {
            this.updateDashboard();
        }, this.updateInterval);
        
        // Pause updates when page is hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                clearInterval(this.updateInterval);
            } else {
                this.startRealTimeUpdates();
            }
        });
    }
    
    async updateDashboard() {
        if (this.isUpdating) return;
        this.isUpdating = true;
        
        try {
            // Update overview metrics
            await this.updateOverviewMetrics();
            
            // Update appliances list
            await this.updateAppliancesList();
            
            // Update charts
            this.updateUsageChart();
            
            // Update real-time indicator
            this.updateRealTimeIndicator();
            
        } catch (error) {
            console.error('Failed to update dashboard:', error);
        } finally {
            this.isUpdating = false;
        }
    }
    
    async updateOverviewMetrics() {
        try {
            const response = await fetch(`/api/dashboard-data/${this.currentUserId}`);
            const data = await response.json();
            
            // Update current power
            const currentPower = data.total_power || 0;
            document.getElementById('currentPower').textContent = `${currentPower.toLocaleString()} W`;
            
            // Update active devices
            const activeDevices = `${data.active_count || 0}/${data.total_count || 0}`;
            document.getElementById('activeDevices').textContent = activeDevices;
            
            // Calculate daily usage (simplified)
            const dailyUsage = (currentPower * 24 / 1000).toFixed(1);
            document.getElementById('dailyUsage').textContent = `${dailyUsage} kWh`;
            
            // Calculate monthly cost (simplified)
            const monthlyCost = (dailyUsage * 30 * 5.8).toFixed(0);
            document.getElementById('monthlyCost').textContent = `₹${monthlyCost}`;
            
        } catch (error) {
            console.error('Failed to update overview metrics:', error);
        }
    }
    
    async updateAppliancesList() {
        try {
            const response = await fetch(`/api/appliances/${this.currentUserId}`);
            const appliances = await response.json();
            
            const container = document.getElementById('appliancesList');
            if (!container) return;
            
            // Clear existing items except static examples
            const staticItems = container.querySelectorAll('.appliance-item:nth-child(-n+3)');
            container.innerHTML = '';
            staticItems.forEach(item => container.appendChild(item));
            
            // Add real appliances
            appliances.forEach(appliance => {
                const item = this.createApplianceItem(appliance);
                container.appendChild(item);
            });
            
        } catch (error) {
            console.error('Failed to update appliances list:', error);
        }
    }
    
    createApplianceItem(appliance) {
        const item = document.createElement('div');
        item.className = 'appliance-item';
        item.dataset.applianceId = appliance.id;
        
        const iconMap = {
            'air_conditioner': 'fas fa-snowflake',
            'refrigerator': 'fas fa-temperature-low',
            'washing_machine': 'fas fa-tshirt',
            'water_heater': 'fas fa-tint',
            'television': 'fas fa-tv',
            'microwave': 'fas fa-microchip',
            'dishwasher': 'fas fa-utensils'
        };
        
        const icon = iconMap[appliance.type] || 'fas fa-plug';
        const statusClass = appliance.is_on ? 'on' : 'off';
        const statusText = appliance.is_on ? 'Running' : 'Off';
        const temperature = appliance.temperature ? ` • ${appliance.temperature}°C` : '';
        
        item.innerHTML = `
            <div class="appliance-info">
                <div class="appliance-icon">
                    <i class="${icon}"></i>
                </div>
                <div class="appliance-details">
                    <span class="appliance-name">${appliance.name}</span>
                    <span class="appliance-status">${statusText}${temperature}</span>
                </div>
            </div>
            <div class="appliance-metrics">
                <span class="power-usage">${appliance.power_consumption || 0}W</span>
                <div class="status-indicator ${statusClass}"></div>
            </div>
        `;
        
        return item;
    }
    
    updateUsageChart() {
        if (!this.charts.usage) return;
        
        // Generate new data point
        const now = new Date();
        const timeLabel = now.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
        
        const newDataPoint = Math.floor(Math.random() * 1000) + 1500; // Random power value
        
        // Update chart data
        const chart = this.charts.usage;
        chart.data.labels.push(timeLabel);
        chart.data.datasets[0].data.push(newDataPoint);
        
        // Keep only last 20 points
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        chart.update('none'); // Update without animation for performance
    }
    
    updateDistributionChart(period) {
        if (!this.charts.distribution) return;
        
        // Different data for different periods
        const data = {
            'today': [45, 25, 15, 10, 5],
            'week': [40, 20, 20, 12, 8],
            'month': [35, 30, 18, 10, 7]
        };
        
        this.charts.distribution.data.datasets[0].data = data[period] || data['today'];
        this.charts.distribution.update();
    }
    
    updateRealTimeIndicator() {
        const indicator = document.querySelector('.realtime-indicator');
        if (indicator) {
            indicator.style.animation = 'none';
            indicator.offsetHeight; // Trigger reflow
            indicator.style.animation = 'pulse 2s infinite';
        }
    }
    
    // Event handlers
    handleChartPeriodChange(period) {
        // Update active button
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-period="${period}"]`).classList.add('active');
        
        // Update chart data based on period
        let labels, data;
        switch(period) {
            case '24h':
                labels = this.generateTimeLabels(24);
                data = this.generateSampleData(24);
                break;
            case '7d':
                labels = this.generateDayLabels(7);
                data = this.generateSampleData(7);
                break;
            case '30d':
                labels = this.generateDayLabels(30);
                data = this.generateSampleData(30);
                break;
        }
        
        if (this.charts.usage) {
            this.charts.usage.data.labels = labels;
            this.charts.usage.data.datasets[0].data = data;
            this.charts.usage.update();
        }
    }
    
    async handleAddAppliance(event) {
        const formData = new FormData(event.target);
        const data = {
            user_id: this.currentUserId,
            name: formData.get('name'),
            type: formData.get('type'),
            power_rating: parseInt(formData.get('power_rating'))
        };
        
        try {
            const response = await fetch('/api/add-appliance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.closeAddApplianceModal();
                this.showNotification('Appliance added successfully!', 'success');
                this.updateAppliancesList();
                event.target.reset();
            } else {
                this.showNotification(result.error || 'Failed to add appliance', 'error');
            }
        } catch (error) {
            console.error('Error adding appliance:', error);
            this.showNotification('Failed to add appliance', 'error');
        }
    }
    
    handleNavigation(section) {
        // Update active nav item
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const targetNav = document.querySelector(`[href="${section}"]`).closest('.nav-item');
        if (targetNav) {
            targetNav.classList.add('active');
        }
        
        // Show notification for now (in a real app, this would switch views)
        const sectionName = section.replace('#', '').replace(/([A-Z])/g, ' $1').trim();
        this.showNotification(`Navigating to ${sectionName}...`, 'info');
    }
    
    handleRecommendationApply(button) {
        const item = button.closest('.recommendation-item');
        const title = item.querySelector('h4').textContent;
        
        // Simulate applying recommendation
        button.textContent = 'Applied!';
        button.style.background = '#10b981';
        
        setTimeout(() => {
            button.textContent = 'Applied';
            button.disabled = true;
        }, 1000);
        
        this.showNotification(`Applied: ${title}`, 'success');
    }
    
    // Utility functions
    generateTimeLabels(hours) {
        const labels = [];
        const now = new Date();
        
        for (let i = hours - 1; i >= 0; i--) {
            const time = new Date(now.getTime() - (i * 60 * 60 * 1000));
            labels.push(time.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: false 
            }));
        }
        
        return labels;
    }
    
    generateDayLabels(days) {
        const labels = [];
        const now = new Date();
        
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(now.getTime() - (i * 24 * 60 * 60 * 1000));
            labels.push(date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric' 
            }));
        }
        
        return labels;
    }
    
    generateSampleData(count) {
        const data = [];
        for (let i = 0; i < count; i++) {
            data.push(Math.floor(Math.random() * 2000) + 1000);
        }
        return data;
    }
    
    loadInitialData() {
        // Load any initial data that doesn't require real-time updates
        this.updateOverviewMetrics();
        this.updateAppliancesList();
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#667eea'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            animation: slideInRight 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
}

// Modal functions
function showAddApplianceModal() {
    const modal = document.getElementById('addApplianceModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeAddApplianceModal() {
    const modal = document.getElementById('addApplianceModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(100px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideOutRight {
            from {
                opacity: 1;
                transform: translateX(0);
            }
            to {
                opacity: 0;
                transform: translateX(100px);
            }
        }
    `;
    document.head.appendChild(style);
    
    // Initialize dashboard
    window.dashboard = new EnergyDashboard();
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('addApplianceModal');
        if (event.target === modal) {
            closeAddApplianceModal();
        }
    });
});
