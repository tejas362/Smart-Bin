import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = process.env.REACT_APP_BACKEND_URL;

// Map component using OpenStreetMap
const MapView = ({ dustbins, onBinSelect }) => {
  const [map, setMap] = useState(null);
  const [markers, setMarkers] = useState({});

  useEffect(() => {
    if (!window.L) {
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = initializeMap;
      document.head.appendChild(script);

      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
    } else {
      initializeMap();
    }
  }, []);

  useEffect(() => {
    if (map && dustbins.length > 0) {
      updateMarkers();
    }
  }, [map, dustbins]);

  const initializeMap = () => {
    if (!window.L) return;

    const newMap = window.L.map('map').setView([40.7829, -73.9654], 10);
    
    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(newMap);

    setMap(newMap);
  };

  const updateMarkers = () => {
    // Clear existing markers
    Object.values(markers).forEach(marker => {
      map.removeLayer(marker);
    });

    const newMarkers = {};
    
    dustbins.forEach(bin => {
      const fillLevel = bin.fill_level;
      const isOnline = bin.status === 'online';
      
      // Choose marker color based on fill level and status
      let markerColor = '#22c55e'; // Green for low fill
      if (!isOnline) {
        markerColor = '#6b7280'; // Gray for offline
      } else if (fillLevel >= 90) {
        markerColor = '#ef4444'; // Red for full
      } else if (fillLevel >= 70) {
        markerColor = '#f59e0b'; // Orange for high fill
      } else if (fillLevel >= 50) {
        markerColor = '#eab308'; // Yellow for medium fill
      }

      const customIcon = window.L.divIcon({
        className: 'custom-marker',
        html: `
          <div style="
            background-color: ${markerColor};
            border: 3px solid white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: bold;
            color: white;
          ">
            ${Math.round(fillLevel)}
          </div>
        `,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      });

      const marker = window.L.marker([bin.location.latitude, bin.location.longitude], {
        icon: customIcon
      }).addTo(map);

      marker.bindPopup(`
        <div class="font-medium">
          <h3 class="font-bold text-lg">${bin.name}</h3>
          <p class="text-sm text-gray-600">${bin.location.address}</p>
          <div class="mt-2">
            <p><span class="font-medium">Fill Level:</span> ${fillLevel.toFixed(1)}%</p>
            <p><span class="font-medium">Status:</span> 
              <span class="px-2 py-1 rounded text-xs ${isOnline ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                ${bin.status}
              </span>
            </p>
            <p><span class="font-medium">Battery:</span> ${bin.battery_level.toFixed(1)}%</p>
            <p class="text-xs text-gray-500 mt-1">Last updated: ${new Date(bin.last_updated).toLocaleTimeString()}</p>
          </div>
        </div>
      `);

      marker.on('click', () => onBinSelect && onBinSelect(bin));
      newMarkers[bin.id] = marker;
    });

    setMarkers(newMarkers);
  };

  return <div id="map" className="w-full h-96 rounded-lg border border-gray-300"></div>;
};

// Dashboard Stats Component
const DashboardStats = ({ stats }) => {
  if (!stats) return null;

  const statCards = [
    { label: 'Total Bins', value: stats.total_bins, color: 'blue', icon: '🗑️' },
    { label: 'Full Bins', value: stats.full_bins, color: 'red', icon: '⚠️' },
    { label: 'Offline Bins', value: stats.offline_bins, color: 'gray', icon: '📴' },
    { label: 'Low Battery', value: stats.low_battery_bins, color: 'yellow', icon: '🔋' },
    { label: 'Avg Fill Level', value: `${stats.avg_fill_level}%`, color: 'green', icon: '📊' },
    { label: 'Notifications', value: stats.unread_notifications, color: 'purple', icon: '🔔' }
  ];

  const getColorClasses = (color) => {
    const colors = {
      blue: 'bg-blue-50 border-blue-200 text-blue-800',
      red: 'bg-red-50 border-red-200 text-red-800',
      gray: 'bg-gray-50 border-gray-200 text-gray-800',
      yellow: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      green: 'bg-green-50 border-green-200 text-green-800',
      purple: 'bg-purple-50 border-purple-200 text-purple-800'
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
      {statCards.map((stat, index) => (
        <div key={index} className={`p-4 rounded-lg border-2 ${getColorClasses(stat.color)}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium opacity-75">{stat.label}</p>
              <p className="text-2xl font-bold">{stat.value}</p>
            </div>
            <div className="text-2xl opacity-75">{stat.icon}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Dustbin Card Component
const DustbinCard = ({ bin, onClick }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'bg-green-100 text-green-800';
      case 'offline': return 'bg-red-100 text-red-800';
      case 'maintenance': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getFillLevelColor = (level) => {
    if (level >= 90) return 'bg-red-500';
    if (level >= 70) return 'bg-orange-500';
    if (level >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div 
      className="bg-white rounded-lg shadow-md border border-gray-200 p-4 hover:shadow-lg transition-shadow cursor-pointer"
      onClick={() => onClick && onClick(bin)}
    >
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-semibold text-gray-800 text-sm">{bin.name}</h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(bin.status)}`}>
          {bin.status}
        </span>
      </div>
      
      <div className="space-y-2">
        <div>
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>Fill Level</span>
            <span>{bin.fill_level.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all ${getFillLevelColor(bin.fill_level)}`}
              style={{ width: `${Math.min(100, Math.max(0, bin.fill_level))}%` }}
            ></div>
          </div>
        </div>
        
        <div>
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>Battery</span>
            <span>{bin.battery_level.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1">
            <div 
              className={`h-1 rounded-full transition-all ${bin.battery_level <= 20 ? 'bg-red-500' : 'bg-blue-500'}`}
              style={{ width: `${Math.min(100, Math.max(0, bin.battery_level))}%` }}
            ></div>
          </div>
        </div>
      </div>
      
      <div className="mt-3 text-xs text-gray-500">
        <p>📍 {bin.location.address}</p>
        <p>🌡️ {bin.temperature?.toFixed(1)}°C | 💧 {bin.humidity?.toFixed(1)}%</p>
        <p>Updated: {new Date(bin.last_updated).toLocaleTimeString()}</p>
      </div>
    </div>
  );
};

// Notifications Component
const NotificationPanel = ({ notifications, onMarkRead }) => {
  const getNotificationIcon = (type) => {
    switch (type) {
      case 'full': return '🗑️';
      case 'battery_low': return '🔋';
      case 'offline': return '📴';
      case 'maintenance': return '🔧';
      default: return '📢';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical': return 'border-l-red-500 bg-red-50';
      case 'high': return 'border-l-orange-500 bg-orange-50';
      case 'medium': return 'border-l-yellow-500 bg-yellow-50';
      case 'low': return 'border-l-blue-500 bg-blue-50';
      default: return 'border-l-gray-500 bg-gray-50';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4">
      <h3 className="font-semibold text-gray-800 mb-4 flex items-center">
        🔔 Recent Notifications
        {notifications.length > 0 && (
          <span className="ml-2 bg-red-500 text-white text-xs rounded-full px-2 py-1">
            {notifications.filter(n => !n.is_read).length}
          </span>
        )}
      </h3>
      
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {notifications.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-4">No notifications</p>
        ) : (
          notifications.slice(0, 10).map((notification) => (
            <div 
              key={notification.id}
              className={`border-l-4 p-3 rounded-r ${getPriorityColor(notification.priority)} ${notification.is_read ? 'opacity-60' : ''}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center text-sm">
                    <span className="mr-2">{getNotificationIcon(notification.type)}</span>
                    <span className="font-medium">{notification.dustbin_name}</span>
                    <span className={`ml-2 px-2 py-1 rounded text-xs ${notification.is_read ? 'bg-gray-200 text-gray-600' : 'bg-blue-100 text-blue-800'}`}>
                      {notification.priority}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mt-1">{notification.message}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(notification.timestamp).toLocaleString()}
                  </p>
                </div>
                {!notification.is_read && (
                  <button
                    onClick={() => onMarkRead(notification.id)}
                    className="ml-2 text-blue-600 hover:text-blue-800 text-xs"
                  >
                    Mark Read
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [activeView, setActiveView] = useState('dashboard');
  const [dustbins, setDustbins] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedBin, setSelectedBin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);

  // Fetch data functions
  const fetchDustbins = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/dustbins`);
      setDustbins(response.data);
    } catch (error) {
      console.error('Error fetching dustbins:', error);
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/notifications?limit=20`);
      setNotifications(response.data);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, []);

  const initializeDemoData = async () => {
    try {
      setLoading(true);
      await axios.post(`${API_BASE}/api/initialize-demo-data`);
      await fetchAllData();
    } catch (error) {
      console.error('Error initializing demo data:', error);
    } finally {
      setLoading(false);
    }
  };

  const simulateIoTData = async () => {
    try {
      setIsSimulating(true);
      await axios.post(`${API_BASE}/api/simulate/iot-data`);
      await fetchAllData();
    } catch (error) {
      console.error('Error simulating IoT data:', error);
    } finally {
      setIsSimulating(false);
    }
  };

  const markNotificationRead = async (notificationId) => {
    try {
      await axios.put(`${API_BASE}/api/notifications/${notificationId}/read`);
      await fetchNotifications();
      await fetchStats();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const fetchAllData = useCallback(async () => {
    await Promise.all([fetchDustbins(), fetchNotifications(), fetchStats()]);
  }, [fetchDustbins, fetchNotifications, fetchStats]);

  // Initialize app
  useEffect(() => {
    const initialize = async () => {
      await fetchAllData();
      setLoading(false);
    };
    initialize();
  }, [fetchAllData]);

  // Auto-refresh data every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, [fetchAllData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading Smart Dustbin System...</p>
          <button
            onClick={initializeDemoData}
            className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Initialize Demo Data
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">🗑️ Smart Dustbin IoT</h1>
              <span className="ml-3 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                {dustbins.filter(bin => bin.status === 'online').length}/{dustbins.length} Online
              </span>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={simulateIoTData}
                disabled={isSimulating}
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 text-sm"
              >
                {isSimulating ? '⚡ Simulating...' : '⚡ Simulate IoT Data'}
              </button>
              
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setActiveView('dashboard')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeView === 'dashboard' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  📊 Dashboard
                </button>
                <button
                  onClick={() => setActiveView('map')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeView === 'map' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  🗺️ Map View
                </button>
                <button
                  onClick={() => setActiveView('settings')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeView === 'settings' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  ⚙️ Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Dashboard */}
        <DashboardStats stats={stats} />

        {/* Content based on active view */}
        {activeView === 'dashboard' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Dustbin Cards */}
            <div className="lg:col-span-2">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Dustbin Status</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {dustbins.map((bin) => (
                  <DustbinCard 
                    key={bin.id} 
                    bin={bin} 
                    onClick={setSelectedBin}
                  />
                ))}
              </div>
            </div>

            {/* Notifications Panel */}
            <div>
              <NotificationPanel 
                notifications={notifications} 
                onMarkRead={markNotificationRead}
              />
            </div>
          </div>
        )}

        {activeView === 'map' && (
          <div>
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Dustbin Locations Map</h2>
            <MapView dustbins={dustbins} onBinSelect={setSelectedBin} />
            
            {selectedBin && (
              <div className="mt-6 bg-white rounded-lg shadow-md border border-gray-200 p-6">
                <h3 className="text-lg font-semibold mb-4">Selected Dustbin Details</h3>
                <DustbinCard bin={selectedBin} />
              </div>
            )}
          </div>
        )}

        {activeView === 'settings' && (
          <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-6">System Settings</h2>
            
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-700 mb-3">Demo Controls</h3>
                <div className="flex space-x-4">
                  <button
                    onClick={initializeDemoData}
                    className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Reset Demo Data
                  </button>
                  <button
                    onClick={simulateIoTData}
                    disabled={isSimulating}
                    className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                  >
                    {isSimulating ? 'Simulating...' : 'Simulate IoT Update'}
                  </button>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-700 mb-3">System Information</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <dt className="font-medium text-gray-600">Total Dustbins</dt>
                      <dd className="text-gray-900">{stats?.total_bins || 0}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-gray-600">System Status</dt>
                      <dd className="text-green-600">🟢 Online</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-gray-600">Last Update</dt>
                      <dd className="text-gray-900">{stats?.last_updated ? new Date(stats.last_updated).toLocaleString() : 'N/A'}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-gray-600">API Endpoint</dt>
                      <dd className="text-gray-900 text-sm">{API_BASE}/api</dd>
                    </div>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;