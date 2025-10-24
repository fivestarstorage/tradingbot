"""
Auto-Deploy Webhook Server
Listens for GitHub push events and automatically deploys
"""
from flask import Flask, request, jsonify
import subprocess
import hmac
import hashlib
import os
import logging
from datetime import datetime

app = Flask(__name__)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GITHUB_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', 'your-secret-here')
REPO_PATH = '/root/tradingbot'

def verify_signature(payload, signature):
    """Verify GitHub webhook signature"""
    if not signature:
        return False
    
    try:
        sha_name, signature_value = signature.split('=')
        if sha_name != 'sha256':
            return False
        
        mac = hmac.new(
            GITHUB_SECRET.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        
        return hmac.compare_digest(mac.hexdigest(), signature_value)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False

def deploy():
    """Execute deployment steps"""
    try:
        logger.info("=" * 70)
        logger.info("🚀 STARTING AUTO-DEPLOYMENT")
        logger.info("=" * 70)
        
        # Change to repo directory
        os.chdir(REPO_PATH)
        
        # 1. Git pull
        logger.info("📥 Pulling latest code from GitHub...")
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            capture_output=True,
            text=True
        )
        logger.info(result.stdout)
        if result.returncode != 0:
            logger.error(f"Git pull failed: {result.stderr}")
            return False, result.stderr
        
        # Check if there were actual changes
        if "Already up to date" in result.stdout:
            logger.info("✅ No changes detected, skipping restart")
            return True, "No changes"
        
        # 2. Restart dashboard (always safe to restart)
        logger.info("🔄 Restarting dashboard...")
        subprocess.run(['screen', '-S', 'dashboard', '-X', 'quit'], 
                      capture_output=True)
        subprocess.run([
            'screen', '-dmS', 'dashboard',
            'python3', f'{REPO_PATH}/advanced_dashboard.py'
        ])
        logger.info("✅ Dashboard restarted")
        
        # 3. Log deployment
        logger.info("=" * 70)
        logger.info("✅ DEPLOYMENT COMPLETE")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        return True, "Deployment successful"
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        return False, str(e)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook"""
    try:
        # Verify signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not verify_signature(request.data, signature):
            logger.warning("⚠️ Invalid signature!")
            return jsonify({'error': 'Invalid signature'}), 403
        
        # Parse payload
        payload = request.json
        
        # Check if it's a push event
        if request.headers.get('X-GitHub-Event') != 'push':
            logger.info(f"Ignoring non-push event: {request.headers.get('X-GitHub-Event')}")
            return jsonify({'message': 'Not a push event'}), 200
        
        # Get commit info
        commits = payload.get('commits', [])
        branch = payload.get('ref', '').split('/')[-1]
        
        logger.info(f"📨 Received push to {branch} branch")
        logger.info(f"📝 {len(commits)} commit(s) pushed")
        
        if commits:
            latest_commit = commits[-1]
            logger.info(f"Latest commit: {latest_commit.get('message', 'N/A')}")
            logger.info(f"Author: {latest_commit.get('author', {}).get('name', 'N/A')}")
        
        # Deploy
        success, message = deploy()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'commits': len(commits)
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 500
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/deploy', methods=['POST'])
def manual_deploy():
    """Manual deploy endpoint (no signature check)"""
    try:
        auth_key = request.headers.get('Authorization')
        if auth_key != f"Bearer {os.getenv('DEPLOY_KEY', 'secret')}":
            return jsonify({'error': 'Unauthorized'}), 401
        
        logger.info("🔧 Manual deployment triggered")
        success, message = deploy()
        
        if success:
            return jsonify({'status': 'success', 'message': message}), 200
        else:
            return jsonify({'status': 'error', 'message': message}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'deploy-webhook',
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🚀 AUTO-DEPLOY WEBHOOK SERVER")
    logger.info("=" * 70)
    logger.info(f"Repository: {REPO_PATH}")
    logger.info(f"Listening on: 0.0.0.0:5002")
    logger.info(f"Webhook URL: http://YOUR_SERVER_IP:5002/webhook")
    logger.info("=" * 70)
    
    app.run(host='0.0.0.0', port=5002, debug=False)
