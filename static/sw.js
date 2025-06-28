const CACHE_NAME = 'receipt-scanner-v1.0.0';
const STATIC_CACHE = 'receipt-scanner-static-v1.0.0';
const DYNAMIC_CACHE = 'receipt-scanner-dynamic-v1.0.0';

// Files to cache immediately
const STATIC_FILES = [
  '/',
  '/receipt-scanner',
  '/static/style.css',
  '/static/script.js',
  '/static/receipt_scanner.js',
  '/static/enhanced_notifications.js',
  '/static/manifest.json',
  '/static/icon-192x192.png',
  '/static/icon-512x512.png',
  '/static/favicon-32x32.png',
  '/static/favicon-16x16.png',
  '/static/apple-touch-icon.png'
];

// API endpoints to cache
const API_CACHE = [
  '/api/process-receipt',
  '/api/save-processed-receipt',
  '/api/analytics/summary',
  '/api/chat/general'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('Caching static files');
        return cache.addAll(STATIC_FILES);
      })
      .then(() => {
        console.log('Static files cached successfully');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('Failed to cache static files:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('Service Worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - handle network requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }
  
  // Handle static file requests
  if (url.pathname.startsWith('/static/') || url.pathname === '/' || url.pathname === '/receipt-scanner') {
    event.respondWith(handleStaticRequest(request));
    return;
  }
  
  // Handle other requests with network-first strategy
  event.respondWith(handleOtherRequest(request));
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
  try {
    // Try network first
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('Network failed for API request, trying cache:', request.url);
    
    // Fallback to cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline response for API requests
    return new Response(
      JSON.stringify({ 
        error: 'You are offline. Please check your connection and try again.',
        offline: true 
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle static file requests with cache-first strategy
async function handleStaticRequest(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('Failed to fetch static file:', request.url);
    
    // Return a basic offline page for HTML requests
    if (request.headers.get('accept').includes('text/html')) {
      return new Response(
        `
        <!DOCTYPE html>
        <html>
        <head>
          <title>Offline - Receipt Scanner</title>
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            body { 
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              display: flex; 
              align-items: center; 
              justify-content: center; 
              height: 100vh; 
              margin: 0; 
              background: #000; 
              color: #fff; 
            }
            .offline-container { 
              text-align: center; 
              padding: 20px; 
            }
            .offline-icon { 
              font-size: 64px; 
              margin-bottom: 20px; 
            }
            .retry-btn { 
              background: #00ff88; 
              color: #000; 
              border: none; 
              padding: 12px 24px; 
              border-radius: 25px; 
              font-size: 16px; 
              cursor: pointer; 
              margin-top: 20px; 
            }
          </style>
        </head>
        <body>
          <div class="offline-container">
            <div class="offline-icon">📶</div>
            <h1>You're Offline</h1>
            <p>Please check your internet connection and try again.</p>
            <button class="retry-btn" onclick="window.location.reload()">Retry</button>
          </div>
        </body>
        </html>
        `,
        {
          status: 200,
          headers: { 'Content-Type': 'text/html' }
        }
      );
    }
    
    throw error;
  }
}

// Handle other requests with network-first strategy
async function handleOtherRequest(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    return cachedResponse || new Response('Not found', { status: 404 });
  }
}

// Background sync for offline receipt processing
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync-receipts') {
    console.log('Background sync triggered for receipts');
    event.waitUntil(syncReceipts());
  }
});

// Sync pending receipts when back online
async function syncReceipts() {
  try {
    // Get pending receipts from IndexedDB
    const pendingReceipts = await getPendingReceipts();
    
    for (const receipt of pendingReceipts) {
      try {
        const response = await fetch('/api/save-processed-receipt', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(receipt)
        });
        
        if (response.ok) {
          // Remove from pending receipts
          await removePendingReceipt(receipt.id);
          console.log('Synced receipt:', receipt.id);
        }
      } catch (error) {
        console.error('Failed to sync receipt:', receipt.id, error);
      }
    }
  } catch (error) {
    console.error('Background sync failed:', error);
  }
}

// IndexedDB operations for offline storage
async function getPendingReceipts() {
  // This would be implemented with actual IndexedDB operations
  // For now, return empty array
  return [];
}

async function removePendingReceipt(id) {
  // This would be implemented with actual IndexedDB operations
  console.log('Removing pending receipt:', id);
}

// Push notification handling
self.addEventListener('push', (event) => {
  console.log('Push notification received');
  
  const options = {
    body: event.data ? event.data.text() : 'New receipt processed!',
    icon: '/static/icon-192x192.png',
    badge: '/static/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Receipt',
        icon: '/static/icon-96x96.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/icon-96x96.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Receipt Scanner', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/receipt-scanner')
    );
  }
});

// Message handling from main thread
self.addEventListener('message', (event) => {
  console.log('Service Worker received message:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_RECEIPT') {
    // Cache receipt data for offline processing
    event.waitUntil(cacheReceiptData(event.data.receipt));
  }
});

// Cache receipt data for offline processing
async function cacheReceiptData(receipt) {
  try {
    const cache = await caches.open(DYNAMIC_CACHE);
    const response = new Response(JSON.stringify(receipt), {
      headers: { 'Content-Type': 'application/json' }
    });
    
    await cache.put(`/api/receipts/${receipt.id}`, response);
    console.log('Cached receipt data for offline processing');
  } catch (error) {
    console.error('Failed to cache receipt data:', error);
  }
}

console.log('Service Worker script loaded'); 