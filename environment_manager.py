#!/usr/bin/env python3
"""
Environment Manager for Receipt Processor
Manages Teller environment switching and Render deployment automation
"""

import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """Manages environment configurations for Teller and Render deployment"""
    
    def __init__(self):
        self.render_yaml_path = Path('render.yaml')
        self.env_path = Path('.env')
        self.environments = {
            'sandbox': {
                'teller_environment': 'sandbox',
                'webhook_url': 'https://receipt-processor.onrender.com/teller/webhook',
                'flask_env': 'production',
                'debug': False,
                'description': 'Sandbox environment for testing with fake data'
            },
            'development': {
                'teller_environment': 'development',
                'webhook_url': 'http://localhost:5000/teller/webhook',  # Default, can be overridden
                'flask_env': 'development',
                'debug': True,
                'description': 'Local development environment with ngrok tunneling'
            },
            'production': {
                'teller_environment': 'production',
                'webhook_url': 'https://receipt-processor.onrender.com/teller/webhook',
                'flask_env': 'production',
                'debug': False,
                'description': 'Production environment with live bank data'
            }
        }
    
    def get_current_environment(self) -> Dict:
        """Get current environment configuration"""
        return {
            'teller_environment': os.getenv('TELLER_ENVIRONMENT', 'sandbox'),
            'teller_webhook_url': os.getenv('TELLER_WEBHOOK_URL', ''),
            'flask_env': os.getenv('FLASK_ENV', 'development'),
            'debug': os.getenv('DEBUG', 'false').lower() == 'true',
            'render_service_url': 'https://receipt-processor.onrender.com'
        }
    
    def update_render_yaml(self, environment: str, webhook_url: Optional[str] = None) -> bool:
        """Update render.yaml with new environment configuration"""
        try:
            if environment not in self.environments:
                logger.error(f"Invalid environment: {environment}")
                return False
            
            config = self.environments[environment].copy()
            if webhook_url:
                config['webhook_url'] = webhook_url
            
            # Read current render.yaml
            if not self.render_yaml_path.exists():
                logger.error("render.yaml not found")
                return False
            
            with open(self.render_yaml_path, 'r') as f:
                content = f.read()
            
            # Update environment variables
            content = self._update_yaml_env_var(content, 'TELLER_ENVIRONMENT', config['teller_environment'])
            content = self._update_yaml_env_var(content, 'TELLER_WEBHOOK_URL', config['webhook_url'])
            content = self._update_yaml_env_var(content, 'FLASK_ENV', config['flask_env'])
            content = self._update_yaml_env_var(content, 'FLASK_DEBUG', str(config['debug']).lower())
            content = self._update_yaml_env_var(content, 'DEBUG', str(config['debug']).lower())
            
            # Write updated render.yaml
            with open(self.render_yaml_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Updated render.yaml for {environment} environment")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update render.yaml: {str(e)}")
            return False
    
    def update_local_env(self, environment: str, webhook_url: Optional[str] = None) -> bool:
        """Update local .env file with new configuration"""
        try:
            if environment not in self.environments:
                logger.error(f"Invalid environment: {environment}")
                return False
            
            config = self.environments[environment].copy()
            if webhook_url:
                config['webhook_url'] = webhook_url
            
            if not self.env_path.exists():
                logger.warning("No .env file found, skipping local update")
                return True
            
            with open(self.env_path, 'r') as f:
                content = f.read()
            
            # Update environment variables
            content = self._update_env_var(content, 'TELLER_ENVIRONMENT', config['teller_environment'])
            content = self._update_env_var(content, 'TELLER_WEBHOOK_URL', config['webhook_url'])
            content = self._update_env_var(content, 'FLASK_ENV', config['flask_env'])
            content = self._update_env_var(content, 'FLASK_DEBUG', str(config['debug']).lower())
            content = self._update_env_var(content, 'DEBUG', str(config['debug']).lower())
            
            with open(self.env_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Updated .env for {environment} environment")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update .env: {str(e)}")
            return False
    
    def _update_yaml_env_var(self, content: str, key: str, value: str) -> str:
        """Update environment variable in YAML content"""
        pattern = rf'(\s+- key: {re.escape(key)}\s+value: ).*'
        replacement = f'\\1{value}'
        return re.sub(pattern, replacement, content)
    
    def _update_env_var(self, content: str, key: str, value: str) -> str:
        """Update environment variable in .env content"""
        pattern = rf'^{re.escape(key)}=.*$'
        replacement = f'{key}={value}'
        
        if re.search(pattern, content, re.MULTILINE):
            return re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            # Add new variable if not found
            return content + f'\n{key}={value}'
    
    def deploy_to_render(self, commit_message: Optional[str] = None) -> bool:
        """Deploy changes to Render via git push"""
        try:
            # Check if we're in a git repository
            if not Path('.git').exists():
                logger.error("Not in a git repository")
                return False
            
            # Stage changes
            subprocess.run(['git', 'add', 'render.yaml'], check=True)
            
            # Commit changes
            commit_msg = commit_message or f"Update environment configuration - {self.get_current_environment()['teller_environment']}"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            # Push to trigger Render deployment
            result = subprocess.run(['git', 'push'], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Successfully pushed to GitHub - Render deployment triggered")
                return True
            else:
                logger.error(f"❌ Git push failed: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Git command failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Deploy failed: {str(e)}")
            return False
    
    def switch_environment(self, environment: str, webhook_url: Optional[str] = None, 
                          deploy: bool = False, commit_message: Optional[str] = None) -> Dict:
        """Switch to a new environment configuration"""
        try:
            if environment not in self.environments:
                return {'success': False, 'error': f'Invalid environment: {environment}'}
            
            config = self.environments[environment]
            
            # Update render.yaml
            if not self.update_render_yaml(environment, webhook_url):
                return {'success': False, 'error': 'Failed to update render.yaml'}
            
            # Update local .env if it exists
            self.update_local_env(environment, webhook_url)
            
            result = {
                'success': True,
                'environment': environment,
                'webhook_url': webhook_url or config['webhook_url'],
                'description': config['description']
            }
            
            # Auto-deploy if requested
            if deploy:
                if self.deploy_to_render(commit_message):
                    result['deployed'] = True
                    result['message'] = f'Successfully switched to {environment} and deployed to Render'
                else:
                    result['deployed'] = False
                    result['message'] = f'Switched to {environment} but deployment failed'
            else:
                result['message'] = f'Successfully switched to {environment}. Use git push to deploy.'
            
            return result
            
        except Exception as e:
            logger.error(f"Environment switch failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_environment_info(self) -> Dict:
        """Get information about all available environments"""
        return {
            'current': self.get_current_environment(),
            'available': self.environments,
            'render_service_url': 'https://receipt-processor.onrender.com'
        }

def main():
    """CLI interface for environment management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Receipt Processor environments')
    parser.add_argument('action', choices=['switch', 'info', 'deploy'], 
                       help='Action to perform')
    parser.add_argument('--environment', '-e', choices=['sandbox', 'development', 'production'],
                       help='Environment to switch to')
    parser.add_argument('--webhook-url', '-w', help='Custom webhook URL (for development)')
    parser.add_argument('--deploy', '-d', action='store_true', 
                       help='Auto-deploy to Render after switching')
    parser.add_argument('--message', '-m', help='Commit message for deployment')
    
    args = parser.parse_args()
    
    manager = EnvironmentManager()
    
    if args.action == 'info':
        info = manager.get_environment_info()
        print(json.dumps(info, indent=2))
    
    elif args.action == 'switch':
        if not args.environment:
            print("❌ Environment required for switch action")
            return
        
        result = manager.switch_environment(
            args.environment, 
            args.webhook_url, 
            args.deploy, 
            args.message
        )
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")
    
    elif args.action == 'deploy':
        if manager.deploy_to_render(args.message):
            print("✅ Successfully deployed to Render")
        else:
            print("❌ Deployment failed")

if __name__ == '__main__':
    main() 