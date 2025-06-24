const CACHE_NAME = 'transactionpro-2026-v1.0.0';
const STATIC_CACHE = 'static-v1.0.0';
const DYNAMIC_CACHE = 'dynamic-v1.0.0';

// Assets to cache for offline functionality
const STATIC_ASSETS = [
    '/',
    '/static/manifest.json',
    '/health',
    '/status',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
];

// API endpoints to cache dynamically
const API_ENDPOINTS = [
    '/api/transactions',
    '/api/stats',
    '/api/analytics',
    '/api/receipts'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('🚀 Service Worker installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('📦 Caching static assets...');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('✅ Static assets cached successfully');
                return self.skipWaiting();
            })
            .catch(err => {
                console.error('❌ Failed to cache static assets:', err);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('🔄 Service Worker activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('🗑️ Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('✅ Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
    const requestURL = new URL(event.request.url);
    
    // Handle API requests with network-first strategy
    if (requestURL.pathname.startsWith('/api/')) {
        event.respondWith(networkFirstStrategy(event.request));
        return;
    }
    
    // Handle static assets with cache-first strategy
    if (STATIC_ASSETS.some(asset => event.request.url.includes(asset))) {
        event.respondWith(cacheFirstStrategy(event.request));
        return;
    }
    
    // Handle navigation requests with network-first, fallback to cache
    if (event.request.mode === 'navigate') {
        event.respondWith(navigationStrategy(event.request));
        return;
    }
    
    // Default strategy for other requests
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});

// Network-first strategy (for API requests)
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('📡 Network failed, trying cache for:', request.url);
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline fallback for API requests
        return new Response(JSON.stringify({
            error: 'Offline',
            message: 'No network connection available',
            offline: true
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Cache-first strategy (for static assets)
async function cacheFirstStrategy(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        const cache = await caches.open(STATIC_CACHE);
        cache.put(request, networkResponse.clone());
        return networkResponse;
    } catch (error) {
        console.error('❌ Failed to fetch:', request.url);
        throw error;
    }
}

// Navigation strategy (for page requests)
async function navigationStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        return networkResponse;
    } catch (error) {
        console.log('📄 Network failed for navigation, using cache');
        const cachedResponse = await caches.match('/');
        return cachedResponse || new Response('Offline', { status: 503 });
    }
}

// Background sync for failed requests
self.addEventListener('sync', event => {
    console.log('🔄 Background sync triggered:', event.tag);
    
    if (event.tag === 'transaction-sync') {
        event.waitUntil(syncTransactions());
    }
    
    if (event.tag === 'analytics-sync') {
        event.waitUntil(syncAnalytics());
    }
});

// Sync transactions when back online
async function syncTransactions() {
    try {
        console.log('📊 Syncing transactions...');
        const response = await fetch('/api/sync/transactions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            console.log('✅ Transactions synced successfully');
            // Notify clients about sync completion
            self.clients.matchAll().then(clients => {
                clients.forEach(client => {
                    client.postMessage({
                        type: 'SYNC_COMPLETE',
                        data: 'Transactions synced successfully'
                    });
                });
            });
        }
    } catch (error) {
        console.error('❌ Transaction sync failed:', error);
    }
}

// Sync analytics when back online
async function syncAnalytics() {
    try {
        console.log('📈 Syncing analytics...');
        const response = await fetch('/api/sync/analytics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            console.log('✅ Analytics synced successfully');
        }
    } catch (error) {
        console.error('❌ Analytics sync failed:', error);
    }
}

// Push notification handler
self.addEventListener('push', event => {
    console.log('📨 Push notification received');
    
    let data = {};
    if (event.data) {
        data = event.data.json();
    }
    
    const options = {
        title: data.title || 'TransactionPro 2026',
        body: data.body || 'New transaction intelligence available',
        icon: '/static/manifest.json',
        badge: '/static/manifest.json',
        tag: data.tag || 'general',
        data: data.url || '/',
        actions: [
            {
                action: 'view',
                title: 'View Details',
                icon: '/static/icon-view.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/static/icon-dismiss.png'
            }
        ],
        vibrate: [200, 100, 200],
        requireInteraction: true
    };
    
    event.waitUntil(
        self.registration.showNotification(options.title, options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
    console.log('🔔 Notification clicked:', event.action);
    
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow(event.notification.data)
        );
    } else if (event.action === 'dismiss') {
        // Just close the notification
        return;
    } else {
        // Default action - open the app
        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true })
                .then(clientList => {
                    if (clientList.length > 0) {
                        return clientList[0].focus();
                    }
                    return clients.openWindow('/');
                })
        );
    }
});

// Message handler for communication with main thread
self.addEventListener('message', event => {
    console.log('📨 Service Worker received message:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'CACHE_ANALYTICS') {
        caches.open(DYNAMIC_CACHE).then(cache => {
            cache.put('/api/analytics', new Response(JSON.stringify(event.data.payload)));
        });
    }
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', event => {
    console.log('⏰ Periodic sync triggered:', event.tag);
    
    if (event.tag === 'analytics-update') {
        event.waitUntil(updateAnalytics());
    }
});

async function updateAnalytics() {
    try {
        console.log('📊 Updating analytics in background...');
        const response = await fetch('/api/analytics/refresh', {
            method: 'POST'
        });
        
        if (response.ok) {
            console.log('✅ Analytics updated successfully');
        }
    } catch (error) {
        console.error('❌ Background analytics update failed:', error);
    }
}

// Error handler
self.addEventListener('error', event => {
    console.error('❌ Service Worker error:', event.error);
});

// Unhandled rejection handler
self.addEventListener('unhandledrejection', event => {
    console.error('❌ Service Worker unhandled rejection:', event.reason);
});

console.log('🎯 TransactionPro 2026 Service Worker loaded successfully');
console.log('📱 PWA features: Offline support, background sync, push notifications');
console.log('🔄 Cache strategy: Network-first for API, Cache-first for static assets'); 