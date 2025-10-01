"""
Remote Data Loader module for handling cloud/remote data sources.
Supports FTP, SFTP, HTTP/HTTPS URLs, and other remote protocols.
"""
import pandas as pd
import logging
import os
import tempfile
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
import ssl
from datetime import datetime

# Optional imports for FTP/SFTP support
try:
    import ftplib
    HAS_FTP = True
except ImportError:
    ftplib = None
    HAS_FTP = False

try:
    import paramiko
    HAS_SFTP = True
except ImportError:
    paramiko = None
    HAS_SFTP = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    requests = None
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)

class RemoteDataLoader:
    """
    Handles loading data from remote sources including FTP, SFTP, HTTP/HTTPS URLs.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.temp_dir = tempfile.mkdtemp(prefix="tender_remote_")
        self.downloaded_files = []
        
    def __del__(self):
        """Cleanup temporary files on destruction."""
        self.cleanup_temp_files()
    
    def cleanup_temp_files(self):
        """Remove all temporary downloaded files."""
        for file_path in self.downloaded_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                self.logger.warning(f"Could not remove temp file {file_path}: {e}")
        
        try:
            if os.path.exists(self.temp_dir):
                os.rmdir(self.temp_dir)
        except Exception as e:
            self.logger.warning(f"Could not remove temp directory {self.temp_dir}: {e}")
    
    def is_remote_url(self, path: str) -> bool:
        """Check if the given path is a remote URL."""
        if not path:
            return False
        
        path_lower = path.lower()
        remote_protocols = ['http://', 'https://', 'ftp://', 'sftp://', 'ftps://']
        
        # Check for standard protocols
        if any(path_lower.startswith(protocol) for protocol in remote_protocols):
            return True
        
        # Check for IP address patterns
        if self._is_ip_address_url(path):
            return True
        
        return False
    
    def _is_ip_address_url(self, path: str) -> bool:
        """Check if path contains an IP address pattern."""
        import re
        # Simple IP address pattern check
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        return bool(re.search(ip_pattern, path))
    
    def load_from_remote_source(self, url: str, username: Optional[str] = None, password: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Load data from a remote source.
        
        Returns:
            Tuple of (success, message, local_file_path)
        """
        try:
            self.logger.info(f"Attempting to load data from remote source: {url}")
            
            if url.lower().startswith(('http://', 'https://')):
                return self._download_http(url, username, password)
            elif url.lower().startswith('ftp://'):
                return self._download_ftp(url, username, password)
            elif url.lower().startswith(('sftp://', 'ftps://')):
                return self._download_sftp(url, username, password)
            else:
                # Try to detect protocol and add default if needed
                if self._is_ip_address_url(url) and not any(url.lower().startswith(p) for p in ['http', 'ftp']):
                    # Default to HTTP for IP addresses
                    return self._download_http(f"http://{url}", username, password)
                else:
                    return False, f"Unsupported protocol in URL: {url}", None
                    
        except Exception as e:
            self.logger.error(f"Error loading from remote source {url}: {e}")
            return False, f"Error: {str(e)}", None
    
    def _download_http(self, url: str, username: Optional[str] = None, password: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Download file from HTTP/HTTPS URL."""
        try:
            # Determine file extension from URL
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            if not filename or '.' not in filename:
                # If no filename in URL, try to detect from Content-Type header
                filename = f"remote_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            local_path = os.path.join(self.temp_dir, filename)
            
            if HAS_REQUESTS and requests is not None:
                # Use requests library if available (better for authentication)
                auth = None
                if username and password:
                    auth = (username, password)
                
                headers = {
                    'User-Agent': 'Tender Management Utility v3.0'
                }
                
                response = requests.get(url, auth=auth, headers=headers, timeout=30, stream=True)
                response.raise_for_status()
                
                # Try to get filename from Content-Disposition header
                if 'content-disposition' in response.headers:
                    import re
                    cd = response.headers['content-disposition']
                    filename_match = re.findall('filename=(.+)', cd)
                    if filename_match:
                        filename = filename_match[0].strip('"\'')
                        local_path = os.path.join(self.temp_dir, filename)
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
            else:
                # Fallback to urllib
                if username and password:
                    # Create password manager
                    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                    password_mgr.add_password(None, url, username, password)
                    
                    auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
                    opener = urllib.request.build_opener(auth_handler)
                    urllib.request.install_opener(opener)
                
                # Create SSL context that doesn't verify certificates for flexibility
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                request = urllib.request.Request(url, headers={
                    'User-Agent': 'Tender Management Utility v3.0'
                })
                
                with urllib.request.urlopen(request, context=ssl_context, timeout=30) as response:
                    with open(local_path, 'wb') as f:
                        f.write(response.read())
            
            self.downloaded_files.append(local_path)
            file_size = os.path.getsize(local_path) / 1024  # KB
            
            self.logger.info(f"Successfully downloaded {filename} ({file_size:.1f} KB)")
            return True, f"Downloaded {filename} ({file_size:.1f} KB)", local_path
            
        except Exception as e:
            self.logger.error(f"HTTP download failed for {url}: {e}")
            return False, f"HTTP download failed: {str(e)}", None
    
    def _download_ftp(self, url: str, username: Optional[str] = None, password: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Download file from FTP URL."""
        if not HAS_FTP or ftplib is None:
            return False, "FTP support not available. Please install required dependencies.", None
        
        try:
            parsed_url = urllib.parse.urlparse(url)
            host = parsed_url.hostname
            if not host:
                return False, "Invalid FTP URL: missing hostname", None
            
            port = parsed_url.port or 21
            path = parsed_url.path
            
            filename = os.path.basename(path)
            if not filename:
                filename = f"ftp_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            local_path = os.path.join(self.temp_dir, filename)
            
            # Use provided credentials or try anonymous
            ftp_user = username or parsed_url.username or 'anonymous'
            ftp_pass = password or parsed_url.password or 'anonymous@'
            
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=30)
            ftp.login(ftp_user, ftp_pass)
            
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {path}', f.write)
            
            ftp.quit()
            
            self.downloaded_files.append(local_path)
            file_size = os.path.getsize(local_path) / 1024  # KB
            
            self.logger.info(f"Successfully downloaded via FTP: {filename} ({file_size:.1f} KB)")
            return True, f"Downloaded via FTP: {filename} ({file_size:.1f} KB)", local_path
            
        except Exception as e:
            self.logger.error(f"FTP download failed for {url}: {e}")
            return False, f"FTP download failed: {str(e)}", None
    
    def _download_sftp(self, url: str, username: Optional[str] = None, password: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Download file from SFTP URL."""
        if not HAS_SFTP or paramiko is None:
            return False, "SFTP support not available. Please install paramiko: pip install paramiko", None
        
        try:
            parsed_url = urllib.parse.urlparse(url)
            host = parsed_url.hostname
            if not host:
                return False, "Invalid SFTP URL: missing hostname", None
            port = parsed_url.port or 22
            path = parsed_url.path
            
            filename = os.path.basename(path)
            if not filename:
                filename = f"sftp_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            local_path = os.path.join(self.temp_dir, filename)
            
            # Use provided credentials
            sftp_user = username or parsed_url.username
            sftp_pass = password or parsed_url.password
            
            if not sftp_user:
                return False, "SFTP requires username", None
            
            # Create SSH client - paramiko is guaranteed to not be None here
            ssh = paramiko.SSHClient()  # type: ignore
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # type: ignore
            
            # Try password authentication first, then key-based
            try:
                ssh.connect(host, port=port, username=sftp_user, password=sftp_pass, timeout=30)
            except paramiko.AuthenticationException:  # type: ignore
                # Try with default SSH key
                ssh.connect(host, port=port, username=sftp_user, timeout=30)
            
            sftp = ssh.open_sftp()
            sftp.get(path, local_path)
            sftp.close()
            ssh.close()
            
            self.downloaded_files.append(local_path)
            file_size = os.path.getsize(local_path) / 1024  # KB
            
            self.logger.info(f"Successfully downloaded via SFTP: {filename} ({file_size:.1f} KB)")
            return True, f"Downloaded via SFTP: {filename} ({file_size:.1f} KB)", local_path
            
        except Exception as e:
            self.logger.error(f"SFTP download failed for {url}: {e}")
            return False, f"SFTP download failed: {str(e)}", None
    
    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate if URL is properly formatted and potentially accessible."""
        if not url or not url.strip():
            return False, "URL cannot be empty"
        
        url = url.strip()
        
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Check for valid scheme
            valid_schemes = ['http', 'https', 'ftp', 'sftp', 'ftps']
            if parsed.scheme.lower() not in valid_schemes and not self._is_ip_address_url(url):
                return False, f"Unsupported protocol. Supported: {', '.join(valid_schemes)}"
            
            # Check for hostname/IP
            if not parsed.hostname and not self._is_ip_address_url(url):
                return False, "Invalid URL: missing hostname or IP address"
            
            # Check for file extension in path (optional but recommended)
            if parsed.path:
                valid_extensions = ['.xlsx', '.xls', '.csv', '.json', '.xml']
                path_lower = parsed.path.lower()
                if not any(path_lower.endswith(ext) for ext in valid_extensions):
                    return True, "Warning: URL doesn't point to a recognized file format (.xlsx, .xls, .csv)"
            
            return True, "URL format is valid"
            
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
    
    def get_supported_protocols(self) -> Dict[str, bool]:
        """Get list of supported protocols and their availability."""
        return {
            'HTTP/HTTPS': True,
            'FTP': HAS_FTP,
            'SFTP': HAS_SFTP,
            'Advanced HTTP (requests)': HAS_REQUESTS
        }
