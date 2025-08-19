# config/environment.py
import os
import socket
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Environment types
ENV_LOCAL = "local"
ENV_DOCKER = "docker"
ENV_JENKINS = "jenkins"
ENV_STAGING = "staging"
ENV_PRODUCTION = "production"

def detect_environment():
    """Detect the current running environment."""
    # Check for explicit environment setting
    env_setting = os.environ.get("ENV", "").lower()
    
    # Staging/Production check based on explicit setting
    if env_setting in ["staging", "production"]:
        return env_setting
    
    # Jenkins check
    jenkins_indicators = ['JENKINS_URL', 'JENKINS_HOME', 'BUILD_ID', 'BUILD_URL', 'JOB_NAME']
    if any(indicator in os.environ for indicator in jenkins_indicators):
        return ENV_JENKINS
    
    # Docker check
    if os.path.exists('/.dockerenv') or os.path.exists('/.docker'):
        return ENV_DOCKER
        
    # Default to local
    return ENV_LOCAL

def is_remote_environment():
    """Check if we're running in a remote environment (Jenkins, staging, production)."""
    env = detect_environment()
    return env in [ENV_JENKINS, ENV_STAGING, ENV_PRODUCTION]

def validate_remote_host(host: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a host is suitable for remote connections from Jenkins/staging/production.
    
    Args:
        host: The hostname or IP to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Don't allow empty host
    if not host:
        return False, "Host cannot be empty"
    
    # Don't allow localhost variants in remote environments
    if is_remote_environment() and host.lower() in ['localhost', '127.0.0.1', 'host.docker.internal', '::1']:
        return False, f"Host '{host}' cannot be used in remote environments. Please use a public IP address or hostname."
    
    # Check if host is an IP address
    try:
        socket.inet_aton(host)
        # It's an IP address, check if it's a private IP
        if is_remote_environment():
            octets = host.split('.')
            if len(octets) == 4:
                # Check for private IP ranges
                if octets[0] == '10' or \
                   (octets[0] == '172' and 16 <= int(octets[1]) <= 31) or \
                   (octets[0] == '192' and octets[1] == '168'):
                    return False, f"Private IP address '{host}' may not be reachable from remote environments. Use a public IP or hostname."
        return True, None
    except socket.error:
        # Not an IP address, try to resolve it
        try:
            resolved_ip = socket.gethostbyname(host)
            return True, None
        except socket.gaierror:
            return False, f"Could not resolve hostname '{host}'. Please use a valid hostname or IP address."

def test_ssh_connectivity(host: str, port: int, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """
    Test if SSH port is open on the target host.
    
    Args:
        host: Target hostname or IP
        port: SSH port (usually 22)
        timeout: Connection timeout in seconds
        
    Returns:
        tuple: (is_reachable, error_message)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, None
        else:
            return False, f"SSH port {port} is not open on host {host} (error code: {result})"
    except Exception as e:
        return False, f"Error testing SSH connectivity to {host}:{port} - {str(e)}"
