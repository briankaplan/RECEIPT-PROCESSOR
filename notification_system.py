#!/usr/bin/env python3
"""
Notification System - Handles notifications for the receipt processor
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

class NotificationSystem:
    def __init__(self, config: Dict):
        self.config = config
        self.notifications = []
        
    async def initialize(self):
        """Initialize the notification system"""
        logging.info("🔔 Notification system initialized")
        
    async def send_notification(self, message: str, level: str = "info", data: Optional[Dict] = None):
        """Send a notification"""
        notification = {
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        self.notifications.append(notification)
        
        # Log the notification
        if level == "error":
            logging.error(message)
        elif level == "warning":
            logging.warning(message)
        else:
            logging.info(message)
            
        return notification
    
    async def get_notifications(self, level: Optional[str] = None) -> List[Dict]:
        """Get notifications, optionally filtered by level"""
        if level:
            return [n for n in self.notifications if n["level"] == level]
        return self.notifications
    
    async def clear_notifications(self):
        """Clear all notifications"""
        self.notifications = [] 