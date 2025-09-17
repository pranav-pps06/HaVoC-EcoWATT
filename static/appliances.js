// Appliances Management JavaScript

class ApplianceManager {
    constructor() {
        this.appliances = [];
        this.selectedAppliance = null;
        // Get user ID from session data passed from backend
        this.userId = window.sessionData ? window.sessionData.userId : 1;
        console.log('Appliances manager initialized for user ID:', this.userId);
        this.init();
    }

    init() {
        this.loadAppliances();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Search functionality
        document.getElementById('searchAppliances').addEventListener('input', (e) => {
            this.filterAppliances();
        });

        // Filter functionality
        document.getElementById('typeFilter').addEventListener('change', () => {
            this.filterAppliances();
        });

        document.getElementById('statusFilter').addEventListener('change', () => {
            this.filterAppliances();
        });

        // Add appliance form
        document.getElementById('addApplianceForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addAppliance();
        });

        // Edit appliance form
        document.getElementById('editApplianceForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateAppliance();
        });
    }

    async loadAppliances() {
        try {
            this.showLoading();
            const response = await fetch(`/api/appliances/${this.userId}`);
            if (response.ok) {
                this.appliances = await response.json();
                this.renderAppliances();
            } else {
                this.showError('Failed to load appliances');
            }
        } catch (error) {
            console.error('Error loading appliances:', error);
            this.showError('Failed to load appliances');
        }
    }

    renderAppliances() {
        const grid = document.getElementById('appliancesGrid');
        
        if (this.appliances.length === 0) {
            grid.innerHTML = this.getEmptyState();
            return;
        }

        const filtered = this.getFilteredAppliances();
        
        if (filtered.length === 0) {
            grid.innerHTML = this.getNoResultsState();
            return;
        }

        grid.innerHTML = filtered.map(appliance => this.createApplianceCard(appliance)).join('');
    }

    createApplianceCard(appliance) {
        const isOn = appliance.is_on;
        const powerConsumption = appliance.power_consumption || 0;
        const icon = this.getApplianceIcon(appliance.type);
        
        return `
            <div class="appliance-card" data-id="${appliance.id}" onclick="applianceManager.selectAppliance(${appliance.id})">
                <div class="card-header">
                    <div class="appliance-info">
                        <div class="appliance-name">${appliance.name}</div>
                        <div class="appliance-type">${this.formatType(appliance.type)}</div>
                    </div>
                    <i class="${icon} appliance-icon"></i>
                </div>
                <div class="card-body">
                    <div class="status-row">
                        <div class="status-indicator ${isOn ? 'on' : 'off'}">
                            <div class="status-dot ${isOn ? 'on' : 'off'}"></div>
                            ${isOn ? 'Active' : 'Inactive'}
                        </div>
                        <div class="power-switch ${isOn ? 'on' : 'off'}" onclick="applianceManager.toggleAppliance(event, ${appliance.id})"></div>
                    </div>
                    <div class="metrics-row">
                        <div class="metric">
                            <div class="metric-value">${powerConsumption}W</div>
                            <div class="metric-label">Current Power</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${appliance.power_rating}W</div>
                            <div class="metric-label">Max Power</div>
                        </div>
                    </div>
                    <div class="card-actions">
                        <button class="action-btn edit-btn" onclick="applianceManager.editAppliance(event, ${appliance.id})">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="action-btn delete-btn" onclick="applianceManager.deleteAppliance(event, ${appliance.id})">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                        <button class="action-btn details-btn" onclick="applianceManager.showDetails(event, ${appliance.id})">
                            <i class="fas fa-info"></i> Details
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    getApplianceIcon(type) {
        const icons = {
            'air_conditioner': 'fas fa-snowflake',
            'refrigerator': 'fas fa-box',
            'washing_machine': 'fas fa-tshirt',
            'water_heater': 'fas fa-fire',
            'television': 'fas fa-tv',
            'microwave': 'fas fa-microchip'
        };
        return icons[type] || 'fas fa-plug';
    }

    formatType(type) {
        return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    getFilteredAppliances() {
        const searchTerm = document.getElementById('searchAppliances').value.toLowerCase();
        const typeFilter = document.getElementById('typeFilter').value;
        const statusFilter = document.getElementById('statusFilter').value;

        return this.appliances.filter(appliance => {
            const matchesSearch = appliance.name.toLowerCase().includes(searchTerm) ||
                                this.formatType(appliance.type).toLowerCase().includes(searchTerm);
            const matchesType = !typeFilter || appliance.type === typeFilter;
            const matchesStatus = !statusFilter || 
                                (statusFilter === 'on' && appliance.is_on) ||
                                (statusFilter === 'off' && !appliance.is_on);
            
            return matchesSearch && matchesType && matchesStatus;
        });
    }

    filterAppliances() {
        this.renderAppliances();
    }

    selectAppliance(id) {
        // Remove previous selection
        document.querySelectorAll('.appliance-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // Add selection to clicked card
        const card = document.querySelector(`[data-id="${id}"]`);
        if (card) {
            card.classList.add('selected');
        }
        
        this.selectedAppliance = this.appliances.find(a => a.id === id);
        this.showApplianceDetails(this.selectedAppliance);
    }

    showApplianceDetails(appliance) {
        const panel = document.getElementById('detailsPanel');
        const content = document.getElementById('panelContent');
        
        content.innerHTML = `
            <div class="detail-section">
                <div class="section-title">Basic Information</div>
                <div class="detail-item">
                    <span class="detail-label">Name</span>
                    <span class="detail-value">${appliance.name}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Type</span>
                    <span class="detail-value">${this.formatType(appliance.type)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Power Rating</span>
                    <span class="detail-value">${appliance.power_rating}W</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Status</span>
                    <span class="detail-value ${appliance.is_on ? 'on' : 'off'}">${appliance.is_on ? 'Active' : 'Inactive'}</span>
                </div>
            </div>
            
            <div class="detail-section">
                <div class="section-title">Current Metrics</div>
                <div class="detail-item">
                    <span class="detail-label">Power Consumption</span>
                    <span class="detail-value">${appliance.power_consumption || 0}W</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Temperature</span>
                    <span class="detail-value">${appliance.temperature || 'N/A'}°C</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Last Updated</span>
                    <span class="detail-value">${this.formatTime(appliance.last_updated)}</span>
                </div>
            </div>
            
            <div class="detail-section">
                <div class="section-title">Usage Chart</div>
                <canvas id="usageChart" class="usage-chart"></canvas>
            </div>
        `;
        
        panel.classList.add('open');
        this.renderUsageChart(appliance);
    }

    renderUsageChart(appliance) {
        const ctx = document.getElementById('usageChart').getContext('2d');
        
        // Generate sample data for the last 24 hours
        const hours = [];
        const data = [];
        for (let i = 23; i >= 0; i--) {
            const hour = new Date();
            hour.setHours(hour.getHours() - i);
            hours.push(hour.getHours() + ':00');
            data.push(Math.random() * appliance.power_rating);
        }
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [{
                    label: 'Power Consumption (W)',
                    data: data,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Power (W)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    closeDetailsPanel() {
        document.getElementById('detailsPanel').classList.remove('open');
        document.querySelectorAll('.appliance-card').forEach(card => {
            card.classList.remove('selected');
        });
        this.selectedAppliance = null;
    }

    async toggleAppliance(event, id) {
        event.stopPropagation();
        
        const appliance = this.appliances.find(a => a.id === id);
        if (!appliance) return;
        
        try {
            const response = await fetch(`/api/appliance/${id}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                appliance.is_on = !appliance.is_on;
                this.renderAppliances();
                if (this.selectedAppliance && this.selectedAppliance.id === id) {
                    this.showApplianceDetails(appliance);
                }
            } else {
                this.showError('Failed to toggle appliance');
            }
        } catch (error) {
            console.error('Error toggling appliance:', error);
            this.showError('Failed to toggle appliance');
        }
    }

    editAppliance(event, id) {
        event.stopPropagation();
        
        const appliance = this.appliances.find(a => a.id === id);
        if (!appliance) return;
        
        document.getElementById('editApplianceId').value = id;
        document.getElementById('editApplianceName').value = appliance.name;
        document.getElementById('editPowerRating').value = appliance.power_rating;
        document.getElementById('editLocation').value = appliance.location || '';
        document.getElementById('editBrand').value = appliance.brand || '';
        
        document.getElementById('editApplianceModal').style.display = 'block';
    }

    async updateAppliance() {
        const id = document.getElementById('editApplianceId').value;
        const formData = new FormData(document.getElementById('editApplianceForm'));
        
        try {
            const response = await fetch(`/api/appliance/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(Object.fromEntries(formData))
            });
            
            if (response.ok) {
                this.closeEditApplianceModal();
                this.loadAppliances();
                this.showSuccess('Appliance updated successfully');
            } else {
                this.showError('Failed to update appliance');
            }
        } catch (error) {
            console.error('Error updating appliance:', error);
            this.showError('Failed to update appliance');
        }
    }

    async deleteAppliance(event, id) {
        event.stopPropagation();
        
        if (!confirm('Are you sure you want to delete this appliance?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/appliance/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.loadAppliances();
                this.closeDetailsPanel();
                this.showSuccess('Appliance deleted successfully');
            } else {
                this.showError('Failed to delete appliance');
            }
        } catch (error) {
            console.error('Error deleting appliance:', error);
            this.showError('Failed to delete appliance');
        }
    }

    showDetails(event, id) {
        event.stopPropagation();
        this.selectAppliance(id);
    }

    async addAppliance() {
        const formData = new FormData(document.getElementById('addApplianceForm'));
        
        try {
            const response = await fetch('/api/add-appliance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(Object.fromEntries(formData))
            });
            
            if (response.ok) {
                this.closeAddApplianceModal();
                this.loadAppliances();
                this.showSuccess('Appliance added successfully');
            } else {
                this.showError('Failed to add appliance');
            }
        } catch (error) {
            console.error('Error adding appliance:', error);
            this.showError('Failed to add appliance');
        }
    }

    formatTime(timestamp) {
        if (!timestamp) return 'N/A';
        return new Date(timestamp).toLocaleString();
    }

    showLoading() {
        document.getElementById('appliancesGrid').innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
            </div>
        `;
    }

    showError(message) {
        // You can implement a toast notification system here
        alert(message);
    }

    showSuccess(message) {
        // You can implement a toast notification system here
        alert(message);
    }

    getEmptyState() {
        return `
            <div class="empty-state">
                <i class="fas fa-plug"></i>
                <h3>No Appliances Found</h3>
                <p>Get started by adding your first appliance to monitor its energy consumption.</p>
                <button class="add-appliance-btn" onclick="openAddApplianceModal()">
                    <i class="fas fa-plus"></i> Add Your First Appliance
                </button>
            </div>
        `;
    }

    getNoResultsState() {
        return `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <h3>No Results Found</h3>
                <p>Try adjusting your search criteria or filters.</p>
            </div>
        `;
    }
}

// Modal functions
function openAddApplianceModal() {
    document.getElementById('addApplianceModal').style.display = 'block';
    document.getElementById('addApplianceForm').reset();
}

function closeAddApplianceModal() {
    document.getElementById('addApplianceModal').style.display = 'none';
}

function closeEditApplianceModal() {
    document.getElementById('editApplianceModal').style.display = 'none';
}

function closeDetailsPanel() {
    applianceManager.closeDetailsPanel();
}

function logout() {
    window.location.href = '/login';
}

// Close modals when clicking outside
window.onclick = function(event) {
    const addModal = document.getElementById('addApplianceModal');
    const editModal = document.getElementById('editApplianceModal');
    
    if (event.target === addModal) {
        closeAddApplianceModal();
    }
    if (event.target === editModal) {
        closeEditApplianceModal();
    }
}

// Initialize the appliance manager when the page loads
let applianceManager;
document.addEventListener('DOMContentLoaded', function() {
    applianceManager = new ApplianceManager();
});
